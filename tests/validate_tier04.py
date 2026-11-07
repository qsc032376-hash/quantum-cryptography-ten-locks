"""Run the real Tier 4 pipeline under a renamed team; report aggregates only."""

import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from validate_tier02_tier03 import record_runs, require

from common import is_correct
from tools.check_submission import load_solution


ROOT = Path(__file__).resolve().parents[1]
TEAM = ROOT / "submissions/team3"


def validate(solution):
    original_build = solution.build_circuit
    original_recover = solution.recover_period_with_diagnostics
    original_decrypt = solution._load_decrypt()
    runs, aer = record_runs()
    oracle_blocks, reported = [], []
    recovered = None
    decrypt_calls = 0

    def build():
        circuit = original_build()
        oracle_blocks.append(solution.count_oracle_calls(circuit))
        return circuit

    def recover(**kwargs):
        nonlocal recovered
        recovered, stats = original_recover(**kwargs)
        reported.append(stats)
        return recovered, stats

    def decrypt(period, ciphertext_hex):
        nonlocal decrypt_calls
        decrypt_calls += 1
        require(type(period) is int and 0 < period < 2**10 and period == recovered,
                "Decryption did not receive the measured nonzero 10-bit integer")
        return original_decrypt(period, ciphertext_hex)

    start = time.perf_counter()
    with (patch.object(solution, "build_circuit", new=build),
          patch.object(solution, "recover_period_with_diagnostics", new=recover),
          patch.object(solution, "_load_decrypt", return_value=decrypt),
          aer):
        hash_ok = is_correct(4, solution.solve())
    require(hash_ok, "Tier 4 SHA-256 mismatch")
    require(oracle_blocks == [1], "Expected one opaque Oracle block per sampling circuit")
    require(len(reported) == 1 and decrypt_calls == 1, "Expected one recovery and decryption")
    stats = reported[0]
    require(stats["rank"] == 9 and stats["nullity"] == 1
            and stats["unique_nonzero_candidate"] and stats["all_observed_equations_satisfied"],
            "Simon GF(2) uniqueness was not established")
    require(runs["aer_batches"] == runs["circuits"] == stats["aer_run_calls"],
            "Aer batch or circuit count mismatch")
    require(runs["shots"] == stats["shots"] == stats["oracle_queries_including_shots"]
            and runs["shots"] <= stats["max_shots"], "Oracle query or shot count mismatch")
    return {"hash_ok": hash_ok, "renamed_team_import_ok": True,
            "seconds": round(time.perf_counter() - start, 3),
            "circuits_executed": runs["circuits"], **stats}


def main():
    # Preserve the official submissions/<team>/tier04 layout, but change the
    # name. The checker loads the file as team_solution, without a package.
    with TemporaryDirectory(prefix="renamed-tier04-", dir=ROOT / "submissions") as folder:
        renamed = Path(folder)
        tier = renamed / "tier04"
        tier.mkdir()
        for name in ("solution.py", "gf2.py"):
            shutil.copy2(TEAM / "tier04" / name, tier / name)
        shutil.copy2(TEAM / "classical_keystream.py", renamed)
        sys.path.insert(0, str(tier))
        try:
            result = validate(load_solution(tier / "solution.py"))
        finally:
            sys.path.pop(0)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
