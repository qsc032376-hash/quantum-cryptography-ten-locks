"""Run one bounded real Tier 8 session after synthetic tests pass.

Persist measurement-derived order and aggregate resource statistics, never
factor values, RSA private exponents, unwrapped keys, or plaintext. This does
not run the shared RSA module or claim complete solve() integration.
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

from submissions.team3.tier08 import solution

REPORT_PATH = Path(__file__).with_name("quantum_validation.json")


def gate_metrics(circuit):
    def is_gate(instruction):
        return instruction.operation.name not in {"measure", "reset", "barrier"}
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
    classical = Path(__file__).resolve().parents[1] / "rsa_classical.py"
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
        "factors_recovered_from_measurements": False,
        "plaintext_hash_verified": False,
        "solve_status": "NOT_VALIDATED" if classical.is_file() else "PENDING_CLASSICAL_INTEGRATION",
        "secret_values_recorded": False,
    }
    if (report["python"].split(".")[:2] != ["3", "12"]
            or (report["qiskit"], report["qiskit_aer"]) != ("2.6.1", "0.18.2")):
        raise RuntimeError("Use Python 3.12 and official Qiskit/Aer versions")
    if report["branch"] != "feature/quantum-circuits":
        raise RuntimeError("Run only on feature/quantum-circuits")
    executed = []
    original_run = AerSimulator.run
    original_recover_order = solution.recover_order

    def measured_order(*args, **kwargs):
        report["stage"] = "continued_fractions_and_order_validation"
        result = original_recover_order(*args, **kwargs)
        report["stage"] = "gcd_factor_recovery"
        return result

    def aer_run(simulator, circuit, *args, **kwargs):
        report["real_aer_run_calls"] += 1
        report["real_total_shots"] += kwargs["shots"]
        report["executions"].append({
            "shots": kwargs["shots"], "seed_simulator": kwargs["seed_simulator"],
            "basis_circuit_metrics": gate_metrics(circuit),
            "executed_measurement_q_to_c": [
                [circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index]
                for item in circuit.data if item.operation.name == "measure"
            ],
        })
        report["stage"] = "aer_quantum_measurement"
        executed.append(circuit)  # Kept only in RAM for the official scoring transform.
        return original_run(simulator, circuit, *args, **kwargs)

    def timed_out(_signum, _frame):
        raise TimeoutError("Tier 8 exceeded its phase budget; stop without retry")

    previous_handler = signal.signal(signal.SIGALRM, timed_out)
    report["stage"] = "build_and_transpile"
    signal.alarm(120)
    started = time.perf_counter()
    try:
        with (patch.object(AerSimulator, "run", new=aer_run),
              patch.object(solution, "recover_order", new=measured_order)):
            factors, diagnostics = solution.recover_factors_with_diagnostics()
        report["quantum_recovery_seconds"] = round(time.perf_counter() - started, 6)
        signal.alarm(0)
        report["recovery_diagnostics"] = diagnostics
        if (len(factors) != 2 or any(type(f) is not int or not 1 < f < diagnostics["modulus"] for f in factors)
                or factors[0] * factors[1] != diagnostics["modulus"]):
            raise RuntimeError("Measured order did not recover a nontrivial factor pair")
        del factors
        if report["real_aer_run_calls"] != diagnostics["aer_run_calls"] or not 1 <= report["real_aer_run_calls"] <= 2:
            raise RuntimeError("Unexpected Aer batch count")
        if report["real_total_shots"] != diagnostics["shots"] or not 1 <= diagnostics["shots"] <= 128:
            raise RuntimeError("Unexpected measurement budget")
        if (not diagnostics["modular_order_check"] or not diagnostics["nontrivial_factors_verified"]
                or not diagnostics["order_evidence"]["minimal_order_verified"]):
            raise RuntimeError("Order/factor verification failed")
        report["stage"] = "scoring_transpile"
        signal.alarm(120)
        started = time.perf_counter()
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
        report["factors_recovered_from_measurements"] = True
        report["status"] = "PASS_QUANTUM_ORDER_AND_FACTORIZATION"
        report["stage"] = "complete"
    except Exception as error:
        report["error_type"] = type(error).__name__
        # No RSA secret has been computed in this runner. Our validation
        # messages describe failure causes without including factor values.
        report["error_message"] = str(error)[:500]
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
    report["process_peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS_QUANTUM_ORDER_AND_FACTORIZATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
