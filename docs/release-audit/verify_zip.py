"""Rebuild the pinned draft with the original packager and compare exact bytes."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PACKAGER = "2ebf7a1f64bf5450ca862d2e6dba2eaf7718e1d0"
V3 = "04feb70e52f5522aa2976ca9c7df2e48f27f3cce"
DIGEST = "ac21a9ebc6c804f558395680b86b3b49b88c14e92a5396d1ce7ef2e9cab289b0"


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args])


def main():
    source = git("show", f"{PACKAGER}:tools/package_release_draft.py").decode()
    # The frozen v1 tool has no ref/count switches. Adapt only these settings
    # and normalize the ZIP creator OS to the Unix value used by the v3 draft.
    for old, new in [
        ('BASE = "868fb65e20c73a27bffc118f3617080df9cf2f8b"', f'BASE = "{V3}"'),
        ("len(paths) != 25", "len(paths) != 26"),
        ("info.external_attr =", "info.create_system = 3\n            info.external_attr ="),
        ("ROOT = Path(__file__).resolve().parents[1]", f"ROOT = Path({str(ROOT)!r})"),
    ]:
        if source.count(old) != 1:
            raise RuntimeError("Unexpected pinned packager")
        source = source.replace(old, new)
    paths = git("ls-tree", "-r", "--name-only", V3, "--", "submissions/team3").decode().splitlines()
    expected = {p.removeprefix("submissions/"): p for p in paths
                if not Path(p).name.startswith(("test_", "validate_"))}
    with tempfile.TemporaryDirectory() as tmp:
        script, draft = Path(tmp)/"packager.py", Path(tmp)/"rebuilt.zip"
        script.write_text(source, encoding="utf-8")
        subprocess.run([sys.executable, script, draft], check=True)
        data = draft.read_bytes()
        original = git("show", f"{V3}:drafts/ten-locks-v3-team3-draft.zip")
        if data != original or hashlib.sha256(data).hexdigest() != DIGEST:
            raise RuntimeError("Draft digest or bytes differ")
        with zipfile.ZipFile(draft) as archive:
            if sorted(archive.namelist()) != sorted(expected) or archive.testzip() is not None:
                raise RuntimeError("Unexpected ZIP layout or invalid CRC")
            for name, path in expected.items():
                if not name.endswith(".py") or archive.read(name) != git("show", f"{V3}:{path}"):
                    raise RuntimeError(f"Unexpected content: {name}")
    print("PASS: 26 exact source files; one team3/ root; draft byte-identical.")


if __name__ == "__main__":
    main()
