"""Rebuild frozen v5 in memory and verify the archived run without executing a solver."""
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
V5 = "41c7c6775b8fc499c2acdd878b4829bd17e1210d"
DRAFT = "drafts/ten-locks-v5-team3-draft.zip"
DIGEST = "48e5023081ea14d6b26315895daa7c9e36ff88d4c29c2b09ccf697fba0f319bc"


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args])


def blob(path):
    return git("show", V5 + ":" + path)


def verify():
    saved = json.loads(blob("docs/evidence/v5/resources.json"))
    diff = git("diff", "--name-only", saved["source_tree"], V5).decode().splitlines()
    assert all(p.startswith("docs/") or p == DRAFT for p in diff)
    report = json.loads(blob("docs/evidence/v5/report.json"))
    assert set(report["tiers"]) == set(map(str, range(1, 11)))
    for row in report["tiers"].values():
        assert row["status"] == "full" and row["hash_ok"] and row["circuit_executed"]
        assert row["metrics_status"] == "ok" and not row["flags"]
        assert all(isinstance(row["metrics"][k], int) and row["metrics"][k] >= 0
                   for k in ("two_qubit_gates", "depth", "total_gates", "active_qubits"))
    assert [sum(row["metrics"][k] for row in report["tiers"].values())
            for k in ("two_qubit_gates", "depth", "total_gates")] == [241211, 621301, 711705]
    for label in ("baseline", "candidate"):
        trials = json.loads(blob(f"docs/evidence/v5/tier08-{label}-seeds.json"))["runs"]
        assert [x["seed"] for x in trials] == list(range(800, 810))
        for x in trials:
            assert x["status"] == "PASS" and x["hash_ok"] and x["shots_total"] == 64
            assert x["seed_metadata"]["actual_forwarded_simulator_seeds"] == [x["seed"]]

    paths = git("ls-tree", "-r", "--name-only", V5, "--", "submissions/team3").decode().splitlines()
    paths = [p for p in paths if not Path(p).name.startswith(("test_", "validate_"))]
    assert len(paths) == 27 and all(p.endswith(".py") for p in paths)
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for p in paths:
            item = zipfile.ZipInfo(p.removeprefix("submissions/"), (2026, 1, 1, 0, 0, 0))
            item.create_system, item.compress_type, item.external_attr = 3, zipfile.ZIP_DEFLATED, 0o100644 << 16
            archive.writestr(item, blob(p))
    raw = data.getvalue()
    assert raw == blob(DRAFT) == (ROOT / DRAFT).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == DIGEST == saved["zip_sha256"]
    hashes = set(re.findall(r"[a-fA-F0-9]{64}", blob("hashes.txt").decode()))
    assert len(hashes) == 10

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        official = git("archive", "--format=tar", V5, "tools", "common", "hashes.txt",
                       *(f"tier{i:02}" for i in range(1, 11)))
        with tarfile.open(fileobj=io.BytesIO(official)) as tar:
            tar.extractall(root, filter="data")
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            assert z.testzip() is None and z.namelist() == [p.removeprefix("submissions/") for p in paths]
            for p in paths:
                code = z.read(p.removeprefix("submissions/"))
                assert code == blob(p)
                assert not re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|AKIA[A-Z0-9]{16}", code)
                for node in ast.walk(ast.parse(code)):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        assert hashlib.sha256(node.value.rstrip("\r\n").encode()).hexdigest() not in hashes
            z.extractall(root / "submissions")
        (root / "submissions/team3").rename(root / "submissions/release_review")
        probe = """import sys
from pathlib import Path
root = Path.cwd()
tier = root / 'submissions/release_review' / f'tier{int(sys.argv[1]):02}'
sys.path[:0] = [str(tier), str(root)]
from tools.check_submission import load_solution
module = load_solution(tier/'solution.py')
assert callable(module.solve) and callable(module.build_circuit)
"""
        for i in range(1, 11):
            subprocess.run([sys.executable, "-I", "-B", "-c", probe, str(i)], cwd=root, check=True, timeout=30)
    print("PASS: identical source, 10 archived full/hash/metrics, 10 seed pairs, exact ZIP, CRC/content checks, 10 isolated imports.")
    print("Draft SHA-256:", DIGEST)


if __name__ == "__main__":
    verify()
