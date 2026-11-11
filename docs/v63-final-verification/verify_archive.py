"""Read-only raw archive audit; optional safe extraction into a clean official tree."""
import argparse
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import zipfile

APPROVED = 'ce75c0721622d363e77912191a52a02c34f92472'
EXPECTED = '64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94'
MANIFEST = 'docs/v63-evidence/zip-manifest.json'
ZIP_PATH = 'drafts/ten-locks-team3-v6.3-rc.zip'
UPSTREAM = '340e1ce18cafa69f4cea906f88f93741738dc0fa'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--official-root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.repository.resolve()
    def git(*parts):
        return subprocess.check_output(['git', '-C', str(root), *parts])
    path = root / ZIP_PATH
    data = path.read_bytes()
    report = {'approved_commit': APPROVED, 'archive_path': str(path),
              'verification_time': datetime.now(ZoneInfo('America/New_York')).isoformat(),
              'zip_bytes': len(data), 'actual_sha256': sha(data), 'expected_sha256': EXPECTED}
    def save():
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    if sha(data) != EXPECTED:
        report['status'] = 'RELEASE_BLOCKED'; save()
        raise SystemExit('RELEASE_BLOCKED: raw archive digest differs; no extraction/execution')
    assert data == git('show', f'{APPROVED}:{ZIP_PATH}')
    manifest = json.loads(git('show', f'{APPROVED}:{MANIFEST}'))
    assert manifest['zip_sha256'] == EXPECTED
    assert git('rev-parse', f'{APPROVED}:submissions/team3').decode().strip() == manifest['team_tree']
    report['approved_zip_blob'] = git('rev-parse', f'{APPROVED}:{ZIP_PATH}').decode().strip()
    report['team_tree'] = manifest['team_tree']
    with zipfile.ZipFile(path) as z:
        entries = z.infolist(); names = [x.filename for x in entries]
        assert len(entries) == 37 and set(names) == set(manifest['contents'])
        assert all(n == 1 for n in Counter(names).values())
        assert len({n.casefold() for n in names}) == len(names)
        report['member_count'] = len(entries)
        report['testzip_result'] = z.testzip()
        assert report['testzip_result'] is None
        members = []
        for entry in entries:
            name = entry.filename
            p = PurePosixPath(name)
            mode = entry.external_attr >> 16
            assert not p.is_absolute() and name == p.as_posix()
            assert p.parts[0] == 'team3' and len(p.parts) >= 2
            assert not any(part in ('', '.', '..') or ':' in part for part in p.parts)
            assert '\\' not in name and '\x00' not in name
            assert not entry.is_dir() and not stat.S_ISLNK(mode)
            assert not stat.S_IFMT(mode) or stat.S_ISREG(mode)
            assert not entry.flag_bits & 1
            source_path = 'submissions/' + name
            actual = z.read(entry)
            approved_bytes = git('show', f'{APPROVED}:{source_path}')
            assert actual == approved_bytes
            assert sha(actual) == manifest['contents'][name]
            members.append({'member': name, 'bytes': len(actual), 'sha256': sha(actual),
                            'approved_source': source_path,
                            'approved_git_blob': git('rev-parse', f'{APPROVED}:{source_path}').decode().strip(),
                            'source_bytes_equal': True, 'manifest_hash_matches': True})
        for tier in range(1, 11):
            assert f'team3/tier{tier:02d}/solution.py' in names
        caches = {}
        for tier, expected in ((9, '06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b'),
                               (10, 'b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6')):
            cache = z.read(f'team3/tier{tier:02d}/public_operations.json')
            assert sha(cache) == expected
            caches[str(tier)] = {'sha256': sha(cache), 'expected_sha256': expected,
                                 'bytes': len(cache), 'crlf_sequences': cache.count(b'\r\n'),
                                 'raw_bytes_match': True, 'reserialized_or_normalized': False}
        report.update({'members': members, 'caches': caches, 'duplicates': [], 'unsafe_paths': [],
                       'required_tier_entrypoints_present': True,
                       'all_expected_runtime_modules_and_assets_present': True,
                       'archive_root': 'team3/', 'extraction_target_relative_to_official_root': 'submissions/'})
        if args.official_root:
            fresh = args.official_root.resolve()
            assert subprocess.check_output(['git','-C',str(fresh),'rev-parse','HEAD']).decode().strip() == UPSTREAM
            assert not subprocess.check_output(['git','-C',str(fresh),'status','--porcelain']).strip()
            assert not (fresh/'submissions/team3').exists()
            protected = []
            for name in subprocess.check_output(['git','-C',str(fresh),'ls-files']).decode().splitlines():
                if name.startswith(('tools/', 'common/', 'tier')) or name in ('requirements.txt','hashes.txt'):
                    actual = (fresh/name).read_bytes()
                    assert actual == git('show', f'{APPROVED}:{name}')
                    protected.append({'path':name, 'sha256':sha(actual)})
            z.extractall(fresh/'submissions')
            for entry in members:
                assert sha((fresh/'submissions'/entry['member']).read_bytes()) == entry['sha256']
            report['extraction'] = {'official_repository':'https://github.com/QuantumClub-OSU/Quantum-Cryptography-Challenge',
                                    'official_commit':UPSTREAM, 'fresh_root':str(fresh),
                                    'team_path':str(fresh/'submissions/team3'),
                                    'clean_before_extraction':True, 'all_extracted_bytes_equal':True,
                                    'protected_official_files':protected}
    assert sha(path.read_bytes()) == EXPECTED
    report['status'] = 'ARCHIVE_PREFLIGHT_PASS'; save()
    print(json.dumps({'status':report['status'],'sha256':report['actual_sha256'],
                      'members':report['member_count'],'source_matches':len(report['members'])}))

if __name__ == '__main__':
    main()
