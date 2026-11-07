"""ONE bounded Tier 6 calibration/search session; run synthetic tests first.

Commit aggregates only. Raw measurements and candidates are retained in a
separate mode-0600 local artifact, outside the repository, never printed.
Linux SIGALRM mirrors the separate official 120s execution/transpile budgets.
"""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import time
from unittest.mock import patch

from qiskit import transpile
from qiskit_aer import AerSimulator

from submissions.team3.tier06 import solution


REPORT_PATH = Path(__file__).with_name("quantum_validation.json")
REPO_ROOT = Path(__file__).resolve().parents[3]


def gate_metrics(circuit):
    def is_gate(instruction):
        return instruction.operation.name not in {"measure", "barrier"}
    gates = [item for item in circuit.data if is_gate(item)]
    return {
        "qubits": circuit.num_qubits,
        "classical_bits": circuit.num_clbits,
        "gate_count": len(gates),
        "gate_depth": circuit.depth(filter_function=is_gate),
        "two_qubit_gate_count": sum(len(item.qubits) == 2 for item in gates),
        "active_gate_qubits": len({qubit for item in gates for qubit in item.qubits}),
        "operation_count_including_measurements": circuit.size(),
        "depth_including_measurements": circuit.depth(),
    }


def _private_directory(path):
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(REPO_ROOT):
        raise ValueError("Store private measurements outside the repository")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    if resolved.stat().st_mode & 0o077:
        raise ValueError("Private output directory must have mode 0700")
    return resolved


def _save_private(directory, recovery):
    path = directory / f"measurements_{time.time_ns()}.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump({
            "tier": 6, "candidates": recovery.candidates,
            "measurement_counts": recovery.counts,
            "diagnostics": recovery.diagnostics,
        }, handle, indent=2)
        handle.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-output-directory", type=Path, required=True)
    args = parser.parse_args()
    private_directory = _private_directory(args.private_output_directory)
    classical_path = REPO_ROOT / "submissions/team3/toy_cipher_classical.py"
    report = {
        "status": "FAIL",
        "python": platform.python_version(),
        "qiskit": importlib.metadata.version("qiskit"),
        "qiskit_aer": importlib.metadata.version("qiskit-aer"),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
        "tested_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "basis_gates": solution.BASIS_GATES,
        "optimization_level": 1,
        "seed_transpiler": solution.SEED_TRANSPILER,
        "solve_timeout_seconds": 120,
        "scoring_transpile_timeout_seconds": 120,
        "aer_memory_limit_mb": 512,
        "aer_max_parallel_threads": 2,
        "real_aer_run_calls": 0,
        "real_total_shots": 0,
        "executions": [],
        "classical_candidates_checked": 0,
        "checksum_verified": False,
        "plaintext_hash_verified": False,
        "solve_status": "NOT_VALIDATED" if classical_path.is_file() else "PENDING_CLASSICAL_INTEGRATION",
        "secret_values_in_repository_report": False,
        "private_measurements_retained_outside_repository": False,
    }
    if (report["python"].split(".")[:2] != ["3", "12"]
            or (report["qiskit"], report["qiskit_aer"]) != ("2.6.1", "0.18.2")):
        raise RuntimeError("Use Python 3.12 and official Qiskit/Aer versions")
    if report["branch"] != "feature/quantum-circuits":
        raise RuntimeError("Run only on feature/quantum-circuits")
    original_run = AerSimulator.run
    original_cipher = solution.ToyCipher
    executed = []

    def aer_run(simulator, circuit, *run_args, **kwargs):
        report["real_aer_run_calls"] += 1
        report["real_total_shots"] += kwargs["shots"]
        report["executions"].append({
            "name": circuit.name, "shots": kwargs["shots"],
            "seed_simulator": kwargs["seed_simulator"],
            "basis_circuit_metrics": gate_metrics(circuit),
        })
        executed.append(circuit)
        return original_run(simulator, circuit, *run_args, **kwargs)

    def cipher(*args, **kwargs):
        report["classical_candidates_checked"] += 1
        return original_cipher(*args, **kwargs)

    def timed_out(_signum, _frame):
        raise TimeoutError("Tier 6 exceeded its resource budget; no automatic retry")

    previous_handler = signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(120)
    report["stage"] = "quantum_search"
    started = time.perf_counter()
    try:
        with patch.object(AerSimulator, "run", new=aer_run), patch.object(solution, "ToyCipher", new=cipher):
            recovery = solution.recover_candidates_with_diagnostics()
        report["quantum_recovery_seconds"] = round(time.perf_counter() - started, 6)
        signal.alarm(0)
        diagnostics = recovery.diagnostics
        report["recovery_diagnostics"] = diagnostics
        if (not recovery.candidates or len(set(recovery.candidates)) != len(recovery.candidates)
                or any(type(key) is not int or not 0 <= key < 2**14 for key in recovery.candidates)):
            raise RuntimeError("Expected unique measured 14-bit integer candidates")
        if report["classical_candidates_checked"] != diagnostics["distinct_measured_candidates"]:
            raise RuntimeError("Classical checks must cover only measured unique candidates")
        if report["real_aer_run_calls"] != diagnostics["aer_run_calls"] or not 2 <= report["real_aer_run_calls"] <= 3:
            raise RuntimeError("Unexpected number of Aer executions")
        if report["real_total_shots"] != solution.PILOT_SHOTS + diagnostics["search_shots"]:
            raise RuntimeError("Shot accounting mismatch")
        if diagnostics["public_prefix_hit_rate"] < 0.9:
            raise RuntimeError("Observed amplification below local validation threshold")
        _save_private(private_directory, recovery)
        report["private_measurements_retained_outside_repository"] = True
        del recovery
        # Score every circuit actually run; pick the official largest CX,
        # then largest depth. This performs no further quantum shots.
        report["stage"] = "scoring_transpile"
        started = time.perf_counter()
        signal.alarm(120)
        scored_metrics = []
        for index, circuit in enumerate(executed):
            scored = transpile(
                circuit, basis_gates=solution.BASIS_GATES, coupling_map=None,
                initial_layout=None, optimization_level=1, seed_transpiler=12345,
                num_processes=1,
            )
            metrics = gate_metrics(scored)
            report["executions"][index]["scored_circuit_metrics"] = metrics
            scored_metrics.append(metrics)
        selected = max(range(len(scored_metrics)), key=lambda i: (
            scored_metrics[i]["two_qubit_gate_count"], scored_metrics[i]["gate_depth"],
        ))
        report["single_scoring_circuit_execution_index"] = selected
        report["single_scoring_circuit_metrics"] = scored_metrics[selected]
        report["scoring_transpile_seconds"] = round(time.perf_counter() - started, 6)
        report["aer_success"] = True
        report["candidates_recovered_from_measurements"] = True
        report["status"] = "PASS_QUANTUM_AND_PUBLIC_PREFIX_ONLY"
        report["stage"] = "complete"
    except Exception as error:
        # Exception messages may contain private counts or candidate values.
        report["error_type"] = type(error).__name__
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
    report["process_peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS_QUANTUM_AND_PUBLIC_PREFIX_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
