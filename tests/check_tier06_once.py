"""Run the unmodified Checker once under a renamed team; save aggregates only."""

import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEAM = ROOT / "submissions/team3"
sys.path.insert(0, str(ROOT))

from qiskit import transpile
from qiskit_aer import AerSimulator
from tools.check_submission import (
    compute_metrics, load_config, load_solution, strip_simulator_instructions,
)


def observe(solution_path, output):
    """Called inside the official solve worker; do not alter its Aer recorder."""
    solution = load_solution(solution_path)
    original_solve = solution._solve_with_diagnostics
    original_run = AerSimulator.run
    observed_circuits = []
    aggregates = {}

    def capture():
        plaintext, diag = original_solve()
        for key in (
            "aer_run_calls", "calibration_shots", "calibration_flag_hits", "search_shots",
            "distinct_measured_candidates", "public_prefix_candidates", "checksum_utf8_passes",
            "full_prefix_passes", "hash_passes", "plaintext_hash_verified",
            "calibration_queries_per_shot", "search_queries_per_shot",
            "phase_queries_shot_weighted", "bit_predicate_queries_shot_weighted",
            "coverage_target_draws_reached", "hash_supplement_requested",
            "supplemental_batch_skipped_for_time", "elapsed_seconds",
        ):
            aggregates[key] = diag[key]
        aggregates["iterations"] = diag["estimate"]["iterations"]
        return plaintext, diag

    def capture_run(simulator, circuit, *args, **kwargs):
        # Only the public circuits and requested shot counts, never the result.
        observed_circuits.append((circuit, kwargs["shots"]))
        return original_run(simulator, circuit, *args, **kwargs)

    with (patch.object(solution, "_solve_with_diagnostics", new=capture),
          patch.object(AerSimulator, "run", new=capture_run)):
        plaintext = solution.solve()

    config = load_config()
    rows = []
    for index, (circuit, shots) in enumerate(observed_circuits):
        scored = strip_simulator_instructions(circuit)
        scored.metadata = {}
        scored.name = "scored"
        compiled = transpile(
            scored, basis_gates=config["basis_gates"], coupling_map=config["coupling_map"],
            initial_layout=config["initial_layout"], optimization_level=config["optimization_level"],
            seed_transpiler=config["seed_transpiler"], num_processes=1,
        )
        rows.append({"stage": "calibration" if index == 0 else "search",
                     "shots": shots, "metrics": compute_metrics(compiled)})
    if (len(rows) != aggregates["aer_run_calls"]
            or rows[0]["shots"] != aggregates["calibration_shots"]
            or sum(row["shots"] for row in rows[1:]) != aggregates["search_shots"]):
        raise RuntimeError("Tier 6 aggregate shot accounting mismatch")
    aggregates["executed_circuits"] = rows
    divisor = 2**20 if sys.platform == "darwin" else 1024
    aggregates["solve_worker_peak_rss_mib"] = round(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / divisor, 1
    )
    output.write_text(json.dumps(aggregates, indent=2) + "\n", encoding="utf-8")
    return plaintext


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / ".venv/checker-tier06")
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    aggregates_path = output / "aggregate_run.json"
    aggregates_path.unlink(missing_ok=True)

    with TemporaryDirectory(prefix="renamed-tier06-", dir=ROOT / "submissions") as temp:
        renamed = Path(temp)
        tier = renamed / "tier06"
        tier.mkdir()
        shutil.copy2(TEAM / "tier06/solution.py", tier / "integrated_solution.py")
        shutil.copy2(TEAM / "tier06/oracle.py", tier)
        shutil.copy2(TEAM / "toy_cipher_classical.py", renamed)
        (tier / "solution.py").write_text(
            "from pathlib import Path\n"
            "from runpy import run_path\n\n"
            "def solve():\n"
            f"    observe = run_path({str(Path(__file__).resolve())!r})['observe']\n"
            "    return observe(Path(__file__).with_name('integrated_solution.py'), "
            f"Path({str(aggregates_path)!r}))\n",
            encoding="utf-8",
        )
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="2")
        subprocess.run(
            [sys.executable, "-B", "tools/check_submission.py", str(renamed), "--out", str(output)],
            cwd=ROOT, env=env, check=True, timeout=420,
        )

    official = json.loads((output / "report.json").read_text())["tiers"]["6"]
    if official["status"] != "full" or not official["hash_ok"]:
        raise SystemExit(f"Checker result {official['status']}; see private report for diagnosis")
    aggregates = json.loads(aggregates_path.read_text())
    rows = aggregates["executed_circuits"]
    winner = max(rows, key=lambda row: (
        row["metrics"]["two_qubit_gates"], row["metrics"]["depth"]
    ))
    if (official["circuits_executed"] != len(rows) or official["metrics"] != winner["metrics"]
            or official["metrics_status"] != "ok" or official["flags"]):
        raise SystemExit("Checker score does not match observed circuits, or has review flags")
    print(json.dumps({"scored_stage": winner["stage"], **aggregates}, indent=2))


if __name__ == "__main__":
    main()
