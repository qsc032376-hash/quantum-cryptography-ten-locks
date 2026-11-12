#!/usr/bin/env python3
"""Read-only v6.3.1 archive audit; publish hashes, never runtime file contents.

No ZIP rebuilding, extraction, JSON reserialization, production writes or
Oracle/secret inspection. All comparisons use original uncompressed bytes.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

CANDIDATE = '2fe40b2d096d87875244d5ccbb8a76ef979ac499'
# Full pinned approved baseline, deliberately not a moving branch reference.
BASELINE = 'ce75c0721622d363e77912191a52a02c34f92472'
NEW_ZIP = 'drafts/ten-locks-team3-v6.3.1-docs.zip'
OLD_ZIP = 'drafts/ten-locks-team3-v6.3-rc.zip'
NEW_SHA = '4f1b2de8c7b554bed75319ab7f965937bad85906aa11a26172f5573dc24dfb52'
OLD_SHA = '64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94'
CACHE_SHAS = {
    'team3/tier09/public_operations.json': '06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b',
    'team3/tier10/public_operations.json': 'b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6',
}
CHANGED = ['team3/README.md', 'team3/WRITEUP.md']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments])


def audit(root):
    raw = (root / NEW_ZIP).read_bytes()
    committed_raw = git(root, 'show', f'{CANDIDATE}:{NEW_ZIP}')
    old_raw = git(root, 'show', f'{BASELINE}:{OLD_ZIP}')
    assert sha(raw) == NEW_SHA, 'RELEASE_BLOCKED: new archive raw SHA mismatch'
    assert raw == committed_raw, 'RELEASE_BLOCKED: working ZIP differs from pinned source blob'
    assert sha(old_raw) == OLD_SHA, 'RELEASE_BLOCKED: fallback archive raw SHA mismatch'
    manifest_raw = git(root, 'show', f'{CANDIDATE}:docs/V631_PACKAGE_MANIFEST.md')
    declared = {
        name: (old, new)
        for name, old, new in re.findall(
            r'^\| (team3/[^| ]+) \| ([0-9a-f]{64}) \| ([0-9a-f]{64}) \|$',
            manifest_raw.decode('utf-8'), re.MULTILINE)
    }
    records = []
    with zipfile.ZipFile(io.BytesIO(raw)) as current, zipfile.ZipFile(io.BytesIO(old_raw)) as old:
        names, old_names = current.namelist(), old.namelist()
        assert current.testzip() is None and old.testzip() is None, 'CRC/decompression failure'
        assert len(names) == 37 == len(set(names)), 'Expected 37 unique members'
        assert len(set(n.casefold() for n in names)) == 37, 'Case-insensitive filename collision'
        assert names == old_names, 'Unexpected member names or order'
        assert set(declared) == set(names), 'Manifest expected-member list mismatch'
        for info in current.infolist():
            name = info.filename
            path = PurePosixPath(name)
            assert str(path) == name and not path.is_absolute(), 'Noncanonical or absolute path'
            assert path.parts[0] == 'team3' and len(path.parts) > 1, 'Wrong archive root'
            assert all(part not in ('', '.', '..') and not part.endswith((' ', '.')) for part in path.parts), 'Unsafe path component'
            assert not any(c in name for c in ('\\', ':', '\x00')), 'Unsafe cross-platform path'
            assert not info.is_dir(), 'Unexpected directory entry'
            mode = info.external_attr >> 16
            assert not stat.S_ISLNK(mode), 'Symlink member forbidden'
            assert stat.S_IFMT(mode) in (0, stat.S_IFREG), 'Unexpected special-file member'
            assert not (info.flag_bits & 1), 'Encrypted member forbidden'
            data, old_data = current.read(info), old.read(name)
            source_path = f'submissions/{name}'
            source = git(root, 'show', f'{CANDIDATE}:{source_path}')
            old_source = git(root, 'show', f'{BASELINE}:{source_path}')
            assert data == source, f'Candidate source blob mismatch: {name}'
            assert old_data == old_source, f'Fallback source blob mismatch: {name}'
            assert declared[name] == (sha(old_data), sha(data)), f'Manifest hash mismatch: {name}'
            records.append({
                'member': name, 'bytes': len(data), 'crc32': f'{info.CRC:08x}',
                'compressed_bytes': info.compress_size, 'compression_method': info.compress_type,
                'safe_relative_regular_path': True,
                'candidate_sha256': sha(data), 'baseline_sha256': sha(old_data),
                'unchanged_raw_bytes_from_baseline': data == old_data,
                'source_path': source_path,
                'candidate_source_blob_oid': git(root, 'rev-parse', f'{CANDIDATE}:{source_path}').decode().strip(),
                'baseline_source_blob_oid': git(root, 'rev-parse', f'{BASELINE}:{source_path}').decode().strip(),
                'candidate_source_blob_matches_raw_member': data == source,
                'baseline_source_blob_matches_raw_member': old_data == old_source,
                'package_manifest_row_matches': True,
            })
        changes = [row['member'] for row in records if not row['unchanged_raw_bytes_from_baseline']]
        assert changes == CHANGED, 'Changes exceed the two approved documentation files'
        required = {f'team3/tier{i:02d}/solution.py' for i in range(1, 11)} | set(CACHE_SHAS)
        assert required <= set(names), 'Required solution/cache member missing'
        caches = []
        for name, expected in CACHE_SHAS.items():
            data = current.read(name)
            assert sha(data) == expected, f'Cache SHA mismatch: {name}'
            caches.append({'member': name, 'bytes': len(data), 'expected_sha256': expected,
                           'actual_sha256': sha(data), 'matches_baseline_raw_bytes': data == old.read(name),
                           'carriage_return_byte_count': data.count(b'\r'), 'line_feed_byte_count': data.count(b'\n'),
                           'parsed_or_reserialized': False})
        assert next(x for x in caches if 'tier10/' in x['member'])['carriage_return_byte_count'] == 0, 'Tier10 is not canonical LF'
    return {
        'status': 'ARCHIVE_AND_SOURCE_COMPARISON_PASS',
        'completed_at': datetime.now(ZoneInfo('America/New_York')).isoformat(),
        'candidate_commit': CANDIDATE, 'baseline_commit': BASELINE,
        'candidate_zip_path': NEW_ZIP, 'candidate_zip_bytes': len(raw), 'candidate_zip_sha256': sha(raw),
        'candidate_zip_git_blob_oid': git(root, 'rev-parse', f'{CANDIDATE}:{NEW_ZIP}').decode().strip(),
        'candidate_zip_matches_pinned_commit_raw_bytes': True,
        'baseline_zip_path': OLD_ZIP, 'baseline_zip_sha256': sha(old_raw),
        'expected_member_count': 37, 'actual_member_count': len(records),
        'testzip_result': None, 'testzip_executed': True, 'baseline_testzip_result': None,
        'unique_member_count': len(records), 'ordered_names_equal_baseline': True,
        'unsafe_or_duplicate_entries': [], 'all_source_blobs_match': True,
        'changed_members': changes, 'unchanged_member_count': len(records)-len(changes),
        'unchanged_python_members': sum(x['member'].endswith('.py') and x['unchanged_raw_bytes_from_baseline'] for x in records),
        'unchanged_json_members': sum(x['member'].endswith('.json') and x['unchanged_raw_bytes_from_baseline'] for x in records),
        'package_manifest_sha256': sha(manifest_raw), 'all_manifest_rows_verified': True,
        'correct_extraction_destination': 'official_repository/submissions/ (archive root is team3/)',
        'cache_checks': caches, 'members': records,
        'zip_or_production_modified': False, 'archive_extracted_by_this_script': False,
        'runtime_file_contents_or_private_data_published': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('archive-comparison.json'))
    args = parser.parse_args()
    result = audit(args.repository.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:result[k] for k in ('status','candidate_zip_sha256','actual_member_count','changed_members','unchanged_member_count','all_source_blobs_match')}))


if __name__ == '__main__':
    main()
