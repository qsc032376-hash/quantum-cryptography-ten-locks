"""Validate only Tier 1; persist aggregate results, never keys or plaintext.

Run from the repo root with:
    python -m submissions.team3.tier01.validate_quantum

Artificial bit-ordering tests must pass before the single real Aer run.
No circuits, statevectors, counts, key hashes, or plaintext are serialized.
"""

import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from qiskit_aer import AerSimulator

from submissions.team3.tier01 import solution
from tier01 import helper


REPORT_PATH = Path(__file__).with_name("quantum_validation.json")


def aggregate_metrics(circuit):
    """Count only top-level operations, with no oracle-definition traversal.

    For the executed circuit, transpilation has already lowered operations
    into the scoring basis. Gate depth/count exclude measurements/barriers,
    matching the scoring convention for this straight-line circuit.
    """
    def is_gate(instruction):
        return instruction.operation.name not in {"measure", "barrier"}

    gates = [instruction for instruction in circuit.data if is_gate(instruction)]
    return {
        "qubits": circuit.num_qubits,
        "classical_bits": circuit.num_clbits,
        "gate_count": len(gates),
        "gate_depth": circuit.depth(filter_function=is_gate),
        "two_qubit_gate_count": sum(len(item.qubits) == 2 for item in gates),
        "operation_count_including_measurements": circuit.size(),
        "depth_including_measurements": circuit.depth(),
    }


def main():
    report = {
        "status": "FAIL",
        "python": platform.python_version(),
        "qiskit": importlib.metadata.version("qiskit"),
        "qiskit_aer": importlib.metadata.version("qiskit-aer"),
        "branch": subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip(),
        "tested_base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "shots": solution.SHOTS,
        "basis_gates": solution.BASIS_GATES,
        "optimization_level": 1,
        "seed_transpiler": solution.SEED_TRANSPILER,
        "aer_memory_limit_mb": 2048,
        "aer_max_parallel_threads": 2,
        "real_aer_runs": 0,
        "key_recovered_from_measurement": False,
        "plaintext_hash_verified": False,
        "solve_status": (
            "NOT_VALIDATED"
            if Path(solution.__file__).with_name("classical.py").is_file()
            else "PENDING_CLASSICAL_INTEGRATION"
        ),
        "secret_values_recorded": False,
    }
    try:
        if sys.version_info[:2] != (3, 12):
            raise RuntimeError("Python 3.12 is required for this validation")
        if (report["qiskit"], report["qiskit_aer"]) != ("2.6.1", "0.18.2"):
            raise RuntimeError("Validation requires the pinned Qiskit/Aer versions")
        if report["branch"] != "feature/quantum-circuits":
            raise RuntimeError("Run validation on feature/quantum-circuits")

        suite = unittest.defaultTestLoader.loadTestsFromName(
            "submissions.team3.tier01.test_solution"
        )
        tests = unittest.TextTestRunner(verbosity=2).run(suite)
        report["unit_tests_run"] = tests.testsRun
        report["unit_tests_passed"] = tests.wasSuccessful()
        if not tests.wasSuccessful():
            raise RuntimeError("Artificial-data tests failed; real Oracle not run")

        original_build = solution.build_circuit
        original_run = AerSimulator.run
        jobs = []

        def record_build():
            circuit = original_build()
            report["oracle_calls_before_transpilation"] = helper.count_oracle_calls(circuit)
            report["logical_opaque_oracle_metrics"] = aggregate_metrics(circuit)
            return circuit

        def record_run(simulator, circuit, *args, **kwargs):
            report["real_aer_runs"] += 1
            report["executed_basis_circuit_metrics"] = aggregate_metrics(circuit)
            job = original_run(simulator, circuit, *args, **kwargs)
            jobs.append(job)
            return job

        started = time.perf_counter()
        with patch.object(solution, "build_circuit", side_effect=record_build), patch.object(
            AerSimulator, "run", new=record_run
        ):
            measured_key = solution.recover_key()
        report["quantum_recovery_seconds"] = round(time.perf_counter() - started, 6)

        if report["oracle_calls_before_transpilation"] != 1 or report["real_aer_runs"] != 1:
            raise RuntimeError("Expected one oracle block and one actual Aer run")
        if type(measured_key) is not int or not 0 <= measured_key < 2**24:
            raise RuntimeError("The quantum recovery did not produce a 24-bit integer")
        del measured_key
        result = jobs[0].result()  # Reads the completed job; does not run it again.
        report["aer_success"] = bool(result.success)
        report["aer_method"] = result.results[0].metadata["method"]
        report["key_recovered_from_measurement"] = True
        report["status"] = "PASS_QUANTUM_ONLY"
    except Exception as error:
        # Exception text could include simulator data; record only its type.
        report["error_type"] = type(error).__name__
    report["process_peak_rss_mib"] = round(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3
    )
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS_QUANTUM_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
