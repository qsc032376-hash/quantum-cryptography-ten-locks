"""One real Tier 7 QPE session, after the separate synthetic tests pass.

Only aggregate evidence is saved: never keys, measurement strings, matrices,
gate parameters, statevectors or plaintext. No classical module is copied.
"""

import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import signal
import subprocess
import time
from unittest.mock import patch

from qiskit import transpile
from qiskit_aer import AerSimulator

from submissions.team3.tier07 import solution

REPORT_PATH = Path(__file__).with_name("quantum_validation.json")


def gate_metrics(circuit):
    def is_gate(instruction):
        return instruction.operation.name not in {"measure", "barrier", "reset"}
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
    classical_path = Path(__file__).resolve().parents[1] / "tier07_classical.py"
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
        "aer_memory_limit_mb": 512,
        "aer_max_parallel_threads": 2,
        "solve_timeout_seconds": 120,
        "scoring_transpile_timeout_seconds": 120,
        "real_aer_run_calls": 0,
        "real_total_shots": 0,
        "executions": [],
        "aer_success": False,
        "phase_recovered_from_measurements": False,
        "quantum_phase_consistency_verified": False,
        "plaintext_hash_verified": False,
        "solve_status": "NOT_VALIDATED" if classical_path.is_file() else "PENDING_CLASSICAL_INTEGRATION",
        "secret_values_recorded": False,
    }
    if (report["python"].split(".")[:2] != ["3", "12"]
            or (report["qiskit"], report["qiskit_aer"]) != ("2.6.1", "0.18.2")):
        raise RuntimeError("Use Python 3.12 and official Qiskit/Aer versions")
    if report["branch"] != "feature/quantum-circuits":
        raise RuntimeError("Run only on feature/quantum-circuits")
    original_run = AerSimulator.run
    executed = []

    def aer_run(simulator, circuit, *args, **kwargs):
        report["real_aer_run_calls"] += 1
        report["real_total_shots"] += kwargs["shots"]
        report["executions"].append({
            "name": circuit.name, "shots": kwargs["shots"],
            "seed_simulator": kwargs["seed_simulator"],
            "basis_circuit_metrics": gate_metrics(circuit),
            "executed_measurement_q_to_c": [
                [circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index]
                for item in circuit.data if item.operation.name == "measure"
            ],
        })
        executed.append(circuit)  # In-memory only, for official scoring transform.
        return original_run(simulator, circuit, *args, **kwargs)

    def timed_out(_signum, _frame):
        raise TimeoutError("Tier 7 exceeded the resource budget; no retry")

    previous_handler = signal.signal(signal.SIGALRM, timed_out)
    started = time.perf_counter()
    signal.alarm(120)
    report["stage"] = "phase_recovery_and_quantum_check"
    try:
        with patch.object(AerSimulator, "run", new=aer_run):
            phase, diagnostics = solution.recover_phase_with_diagnostics()
        report["quantum_recovery_seconds"] = round(time.perf_counter() - started, 6)
        signal.alarm(0)
        if type(phase) is not int or not 0 <= phase < (1 << 14):
            raise RuntimeError("Expected a measured 14-bit integer phase")
        del phase
        report["recovery_diagnostics"] = diagnostics
        if report["real_aer_run_calls"] != 2 or report["real_total_shots"] != 96:
            raise RuntimeError("Expected one QPE and one phase-check batch, without retries")
        measurement = diagnostics["qpe_measurement"]
        if measurement["distinct_outcomes"] != 1 or measurement["dominant_count"] != 64:
            raise RuntimeError("Exact phase did not produce a single consistent measurement")
        if not diagnostics["phase_check_passed"] or diagnostics["phase_check_all_zero_shots"] != 32:
            raise RuntimeError("Quantum phase verification failed")
        report["stage"] = "scoring_transpile"
        started = time.perf_counter()
        signal.alarm(120)
        metrics = []
        for index, circuit in enumerate(executed):
            scored = transpile(
                circuit, basis_gates=solution.BASIS_GATES, coupling_map=None,
                initial_layout=None, optimization_level=1, seed_transpiler=12345,
                num_processes=1,
            )
            record = gate_metrics(scored)
            report["executions"][index]["scored_circuit_metrics"] = record
            metrics.append(record)
        selected = max(range(len(metrics)), key=lambda i: (
            metrics[i]["two_qubit_gate_count"], metrics[i]["gate_depth"],
        ))
        report["single_scoring_circuit_execution_index"] = selected
        report["single_scoring_circuit_metrics"] = metrics[selected]
        report["scoring_transpile_seconds"] = round(time.perf_counter() - started, 6)
        report["aer_success"] = True
        report["phase_recovered_from_measurements"] = True
        report["quantum_phase_consistency_verified"] = True
        report["status"] = "PASS_QPE_AND_QUANTUM_PHASE_CHECK"
        report["stage"] = "complete"
    except Exception as error:
        # Native error messages could include circuit matrices or private values.
        report["error_type"] = type(error).__name__
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
    report["process_peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS_QPE_AND_QUANTUM_PHASE_CHECK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
