"""Rehearse the exact equivalence tests and renamed Tier 9 Checker in a clean tree."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from verify_zip import DIGEST, V3, git
import hashlib

TEST_REF = "17df36d1c31cd441cd3bd840157caadd3062cada"


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONHASHSEED="0", QISKIT_PARALLEL="FALSE", OMP_NUM_THREADS="2")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = git("archive", "--format=tar", V3, "common", "tools", "hashes.txt", "tier09")
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            archive.extractall(root, filter="data")
        raw = git("show", f"{V3}:drafts/ten-locks-v3-team3-draft.zip")
        if hashlib.sha256(raw).hexdigest() != DIGEST:
            raise RuntimeError("Unexpected ZIP")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            archive.extractall(root/"submissions")
        tests = root/"test_tier09_shared_controls.py"
        tests.write_bytes(git("show", f"{TEST_REF}:tests/test_tier09_shared_controls.py"))
        subprocess.run([sys.executable, "-I", "-c",
                        "import sys,unittest; sys.path.insert(0,'.'); "
                        "unittest.main(module='test_tier09_shared_controls', verbosity=2)"],
                       cwd=root, check=True, env=env, timeout=60)
        team = root/"submissions/independent_review"
        (root/"submissions/team3").rename(team)
        # Keep all helpers; only the Tier 9 entry is discoverable by the CLI.
        for entry in team.glob("tier*/solution.py"):
            if entry.parent.name != "tier09":
                entry.unlink()
        subprocess.run([sys.executable, "-I", "tools/check_submission.py", team,
                        "--sha", V3, "--out", output], cwd=root, env=env, check=True, timeout=300)
    report = json.loads((output/"report.json").read_text())
    expected = dict(two_qubit_gates=89075, depth=235048, total_gates=263601, active_qubits=21)
    row = report["tiers"]["9"]
    if not (set(report["tiers"]) == {"9"} and row["status"] == "full" and row["hash_ok"]
            and row["circuit_executed"] and row["metrics_status"] == "ok"
            and not row["flags"] and row["metrics"] == expected):
        raise RuntimeError("Tier 9 did not reproduce the accepted result; retain the report.")
    print("PASS: Tier 9 full, matching hash and expected metrics, zero flags.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python review_tier09.py NEW_OUTPUT_DIRECTORY")
    main()
