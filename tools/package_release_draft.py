#!/usr/bin/env python3
"""Create a local team-only draft ZIP from the frozen Git tree."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

BASE = "868fb65e20c73a27bffc118f3617080df9cf2f8b"
ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new local ZIP path")
    args = parser.parse_args()
    paths = git("ls-tree", "-r", "--name-only", BASE, "--", "submissions/team3/").decode().splitlines()
    paths = [p for p in paths if not PurePosixPath(p).name.startswith(("test_", "validate_"))]
    if len(paths) != 25 or not all(p.endswith(".py") for p in paths):
        raise RuntimeError("Unexpected frozen submission tree")
    with zipfile.ZipFile(args.output, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            info = zipfile.ZipInfo(path.removeprefix("submissions/"), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, git("show", f"{BASE}:{path}"))
    print(f"Wrote {args.output} ({len(paths)} files)")
    print(f"SHA-256: {hashlib.sha256(args.output.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
