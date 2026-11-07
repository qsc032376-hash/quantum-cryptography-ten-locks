"""Validate Tier 4 only; retain ranks/metrics, never measured equations or s.

Run from the repository root in the official Python/Qiskit/Aer environment.
Artificial tests precede the bounded real quantum recovery. This Linux runner
uses a 120-second deadline and records peak RSS without saving raw circuit data.
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

from qiskit_aer import AerSimulator

from submissions.team3.tier04 import solution


REPORT_PATH = Path(__file__).with_name("quantum_validation.json")


def gate_metrics(circuit):
    """Aggregate outer operations; never traverse Oracle definitions."""
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
    classical_path = Path(__file__).resolve().parents[1] / "classical_keystream.py"
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
        "batch_shots": solution.BATCH_SHOTS,
        "max_shots": solution.MAX_SHOTS,
        "aer_memory_limit_mb": 512,
        "aer_max_parallel_threads": 2,
        "timeout_seconds": 120,
        "aer_run_calls": 0,
        "shots_per_run": [],
        "plaintext_hash_verified": False,
        "solve_status": "NOT_VALIDATED" if classical_path.is_file() else "PENDING_CLASSICAL_INTEGRATION",
        "secret_values_recorded": False,
    }
    if sys.version_info[:2] != (3, 12) or (report["qiskit"], report["qiskit_aer"]) != ("2.6.1", "0.18.2"):
        raise RuntimeError("Use Python 3.12 and the official Qiskit/Aer versions")
    if report["branch"] != "feature/quantum-circuits":
        raise RuntimeError("Run on feature/quantum-circuits")

    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "submissions.team3.tier04.test_gf2", "submissions.team3.tier04.test_solution"
    ])
    tests = unittest.TextTestRunner(verbosity=1).run(suite)
    report["unit_tests_run"] = tests.testsRun
    report["unit_tests_passed"] = tests.wasSuccessful()
    original_build = solution.build_circuit
    original_run = AerSimulator.run

    def build():
        circuit = original_build()
        report["oracle_calls_before_transpilation"] = solution.count_oracle_calls(circuit)
        report["logical_opaque_oracle_metrics"] = gate_metrics(circuit)
        return circuit

    def aer_run(simulator, circuit, *args, **kwargs):
        report["aer_run_calls"] += 1
        report["shots_per_run"].append(kwargs["shots"])
        report["executed_basis_circuit_metrics"] = gate_metrics(circuit)
        return original_run(simulator, circuit, *args, **kwargs)

    def timed_out(_signum, _frame):
        raise TimeoutError("Tier 4 runtime exceeded the budget; no automatic retry")

    if tests.wasSuccessful():
        previous_handler = signal.signal(signal.SIGALRM, timed_out)
        started = time.perf_counter()
        signal.alarm(120)
        try:
            with patch.object(solution, "build_circuit", new=build), patch.object(
                AerSimulator, "run", new=aer_run
            ):
                period, diagnostics = solution.recover_period_with_diagnostics()
            if type(period) is not int or not 0 < period < 2**10:
                raise RuntimeError("Expected a nonzero 10-bit period")
            del period
            if diagnostics["rank"] != 9 or diagnostics["nullity"] != 1:
                raise RuntimeError("The measured system is not uniquely determined")
            if not diagnostics["unique_nonzero_candidate"] or not diagnostics["all_observed_equations_satisfied"]:
                raise RuntimeError("Measured equation verification failed")
            if report["oracle_calls_before_transpilation"] != 1:
                raise RuntimeError("Expected one opaque Oracle block")
            if sum(report["shots_per_run"]) != diagnostics["shots"]:
                raise RuntimeError("Actual shots differ from recovery diagnostics")
            if report["aer_run_calls"] != diagnostics["aer_run_calls"]:
                raise RuntimeError("Actual Aer executions differ from diagnostics")
            report["recovery_diagnostics"] = diagnostics
            report["aer_success"] = True
            report["period_recovered_from_measurements"] = True
            report["status"] = "PASS_QUANTUM_AND_GF2_ONLY"
        except solution.SamplingLimitError as error:
            report.update(error_type=type(error).__name__, rank_at_limit=error.rank, shots_at_limit=error.shots)
        except Exception as error:
            # Do not serialize exception text, which might contain simulator data.
            report["error_type"] = type(error).__name__
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)
            report["quantum_validation_seconds"] = round(time.perf_counter() - started, 6)

    report["process_peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS_QUANTUM_AND_GF2_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
