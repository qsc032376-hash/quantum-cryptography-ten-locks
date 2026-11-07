"""Artificial Oracle tests followed by one bounded real Tier 5 search.

Keep only aggregate success/resource statistics. Never save measured keys,
counts, amplitudes, plaintext, or candidate-specific validation results.
This Linux runner mirrors the separate 120s solve/transpile budgets.
"""

import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from qiskit import transpile
from qiskit_aer import AerSimulator

from submissions.team3.tier05 import solution


REPORT_PATH = Path(__file__).with_name("quantum_validation.json")


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
        "active_gate_qubits": len({q for item in gates for q in item.qubits}),
        "operation_count_including_measurements": circuit.size(),
        "depth_including_measurements": circuit.depth(),
    }


def main():
    classical_path = Path(__file__).resolve().parents[1] / "toy_cipher_classical.py"
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
        "real_shots": 0,
        "classical_candidates_checked": 0,
        "plaintext_hash_verified": False,
        "solve_status": "NOT_VALIDATED" if classical_path.is_file() else "PENDING_CLASSICAL_INTEGRATION",
        "secret_values_recorded": False,
    }
    if sys.version_info[:2] != (3, 12) or (report["qiskit"], report["qiskit_aer"]) != ("2.6.1", "0.18.2"):
        raise RuntimeError("Use Python 3.12 and the official Qiskit/Aer versions")
    if report["branch"] != "feature/quantum-circuits":
        raise RuntimeError("Run on feature/quantum-circuits")

    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "submissions.team3.tier05.test_oracle", "submissions.team3.tier05.test_solution"
    ])
    unit_started = time.perf_counter()
    tests = unittest.TextTestRunner(verbosity=1).run(suite)
    report["unit_tests_run"] = tests.testsRun
    report["unit_tests_passed"] = tests.wasSuccessful()
    report["unit_test_seconds"] = round(time.perf_counter() - unit_started, 6)
    report["unit_tests_use_synthetic_data_only"] = True

    original_build = solution.build_circuit
    original_run = AerSimulator.run
    original_check = solution.validate_candidate
    executed = []

    def build(*args, **kwargs):
        circuit = original_build(*args, **kwargs)
        report["oracle_calls_before_transpilation"] = solution.count_oracle_calls(circuit)
        report["logical_opaque_block_metrics"] = gate_metrics(circuit)
        return circuit

    def aer_run(simulator, circuit, *args, **kwargs):
        report["real_aer_run_calls"] += 1
        report["real_shots"] += kwargs["shots"]
        report["executed_basis_circuit_metrics"] = gate_metrics(circuit)
        executed.append(circuit)  # In-memory only, for the official scoring transform.
        return original_run(simulator, circuit, *args, **kwargs)

    def check(*args, **kwargs):
        report["classical_candidates_checked"] += 1
        return original_check(*args, **kwargs)

    def timed_out(_signum, _frame):
        raise TimeoutError("Tier 5 exceeded the resource budget; no automatic retry")

    if tests.wasSuccessful():
        previous_handler = signal.signal(signal.SIGALRM, timed_out)
        started = time.perf_counter()
        signal.alarm(120)
        report["stage"] = "quantum_recovery"
        try:
            with (
                patch.object(solution, "build_circuit", new=build),
                patch.object(AerSimulator, "run", new=aer_run),
                patch.object(solution, "validate_candidate", new=check),
            ):
                key, diagnostics = solution.recover_key_with_diagnostics()
            report["quantum_recovery_seconds"] = round(time.perf_counter() - started, 6)
            signal.alarm(0)
            if type(key) is not int or not 0 <= key < 1024:
                raise RuntimeError("Expected a measured 10-bit integer candidate")
            del key
            report["recovery_diagnostics"] = diagnostics
            if report["real_aer_run_calls"] != 1 or report["real_shots"] != diagnostics["shots"]:
                raise RuntimeError("Expected one real quantum execution without retry")
            if report["oracle_calls_before_transpilation"] != 25:
                raise RuntimeError("Unexpected Grover query budget")
            if report["classical_candidates_checked"] != diagnostics["distinct_measured_candidates"]:
                raise RuntimeError("Candidate checking exceeded the measured set")
            if not diagnostics["public_prefix_verified"] or diagnostics["measured_success_rate"] < 0.9:
                raise RuntimeError("Observed amplification did not pass the validation threshold")

            # Mirror the checker's transformation of the circuit actually run.
            # This is only a resource calculation; it executes no extra shots.
            report["stage"] = "scoring_transpile"
            started = time.perf_counter()
            signal.alarm(120)
            scored = transpile(
                executed[0], basis_gates=solution.BASIS_GATES, coupling_map=None,
                initial_layout=None, optimization_level=1, seed_transpiler=12345,
                num_processes=1,
            )
            report["single_scoring_circuit_metrics"] = gate_metrics(scored)
            report["scoring_transpile_seconds"] = round(time.perf_counter() - started, 6)
            report["aer_success"] = True
            report["key_recovered_from_measurements"] = True
            report["status"] = "PASS_QUANTUM_AND_PUBLIC_PREFIX_ONLY"
            report["stage"] = "complete"
        except Exception as error:
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
