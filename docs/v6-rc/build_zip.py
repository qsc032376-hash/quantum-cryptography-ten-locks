"""Build the v6 runtime draft from Git blobs, independent of checkout EOLs."""
import argparse
from pathlib import Path
import subprocess
from zipfile import ZIP_STORED, ZipFile, ZipInfo


def git(*args):
    return subprocess.check_output(["git", *args])


def build(ref, output):
    prefix = "submissions/team3/"
    omitted = {"tier01/test_solution.py", "tier01/validate_quantum.py"}
    paths = git("ls-tree", "-r", "--name-only", ref, prefix).decode().splitlines()
    files = [p for p in paths if p.removeprefix(prefix) not in omitted]
    entries = {f"{prefix}tier{tier:02}/solution.py" for tier in range(1, 11)}
    if not entries.issubset(files) or not all(p.endswith(".py") for p in files):
        raise ValueError("Unexpected runtime inventory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for path in sorted(files):
            info = ZipInfo(path.removeprefix("submissions/"))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, git("show", f"{ref}:{path}"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.ref, args.output)
