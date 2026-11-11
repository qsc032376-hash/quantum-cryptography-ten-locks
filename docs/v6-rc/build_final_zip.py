"""Build the final Team 3 submission ZIP deterministically from a Git tree.

The runtime builder (build_zip.py) packages only .py files. The final package
also includes the approved README.md and WRITEUP.md, so this variant keeps the
same deterministic metadata (sorted entries, ZIP_STORED, fixed mode 0644) and
adds an explicit 32-file inventory check.
"""
import argparse
from pathlib import Path
import subprocess
from zipfile import ZIP_STORED, ZipFile, ZipInfo

PREFIX = "submissions/team3/"
OMITTED = {"tier01/test_solution.py", "tier01/validate_quantum.py"}
REQUIRED = {f"tier{tier:02}/solution.py" for tier in range(1, 11)} | {
    "README.md",
    "WRITEUP.md",
}
EXPECTED_COUNT = 32


def git(*args):
    return subprocess.check_output(["git", *args])


def build(ref, output):
    paths = git("ls-tree", "-r", "--name-only", ref, PREFIX).decode().splitlines()
    files = [p for p in paths if p.removeprefix(PREFIX) not in OMITTED]
    relative = {p.removeprefix(PREFIX) for p in files}

    missing = sorted(REQUIRED - relative)
    if missing:
        raise ValueError(f"Missing required entries: {missing}")
    unexpected = sorted(
        name
        for name in relative
        if not (name.endswith(".py") or name in {"README.md", "WRITEUP.md"})
    )
    if unexpected:
        raise ValueError(f"Unexpected entries: {unexpected}")
    if len(files) != EXPECTED_COUNT:
        raise ValueError(f"Expected {EXPECTED_COUNT} files, found {len(files)}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for path in sorted(files):
            info = ZipInfo(path.removeprefix("submissions/"))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, git("show", f"{ref}:{path}"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", help="commit or tree containing submissions/team3")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.ref, args.output)
