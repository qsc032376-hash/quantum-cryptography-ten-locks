"""One bounded Tier 10 quantum run and scoring of the circuit actually run.

Never persist the exponent, witness pair, raw counts, shared secret, or
plaintext. Report empirical sample support separately from public-relation
verification. Complete decryption remains pending the shared classical module.
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

from submissions.team3.tier10 import solution
from submissions.team3.tier10.readout import equation_from_counts, measurement_from_counts

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


def peak_rss_mib():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3)


def main():
    classical = Path(__file__).resolve().parents[1] / "dh_classical.py"
    report = {
        "status": "FAIL",
        "python": platform.python_version(),
        "qiskit": importlib.metadata.version("qiskit"),
        "qiskit_aer": importlib.metadata.version("qiskit-aer"),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
        "tested_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "theory_reference_commit": "758aab5e33dd0ecae07e8d986f8f8d083739bf4a",
        "classical_reference_commit": "dc47b15bdfdd5411d6cc5524fa1641f4f8116816",
        "scoring_basis_gates": solution.BASIS_GATES,
        "simulation_basis": "Aer statevector native basis",
        "optimization_level": 1,
        "seed_transpiler": solution.SEED_TRANSPILER,
        "aer_memory_limit_mb": 512,
        "aer_max_parallel_threads": 2,
        "solve_timeout_seconds": 120,
        "scoring_transpile_timeout_seconds": 120,
        "real_aer_run_calls": 0,
        "real_total_shots": 0,
        "observed_public_candidate_checks": 0,
        "executions": [],
        "aer_success": False,
        "public_relation_verified": False,
        "exponent_recovered_from_measurements": False,
        "scoring_success": False,
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
    original_check = solution.verify_public_candidate

    def candidate_check(*args, **kwargs):
        report["stage"] = "verification_of_measurement_derived_candidate"
        report["observed_public_candidate_checks"] += 1
        return original_check(*args, **kwargs)

    def aer_run(simulator, circuit, *args, **kwargs):
        report["real_aer_run_calls"] += 1
        report["real_total_shots"] += kwargs["shots"]
        report["executions"].append({
            "shots": kwargs["shots"], "seed_simulator": kwargs["seed_simulator"],
            "native_circuit_metrics_not_scoring_metrics": gate_metrics(circuit),
            "native_operation_counts": {name: int(count) for name, count in circuit.count_ops().items()},
            "executed_measurement_q_to_c": [
                [circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index]
                for item in circuit.data if item.operation.name == "measure"
            ],
            "virtual_to_output_wire_map": (
                circuit.layout.final_index_layout(filter_ancillas=True)
                if circuit.layout is not None else list(range(circuit.num_qubits))
            ),
        })
        report["stage"] = "native_aer_quantum_measurement"
        executed.append(circuit)  # RAM only, for the official scoring transform.
        return original_run(simulator, circuit, *args, **kwargs)

    def timed_out(_signum, _frame):
        raise TimeoutError("Tier 10 stage budget exceeded; stop without retry")

    previous_handler = signal.signal(signal.SIGALRM, timed_out)
    report["stage"] = "build_and_native_transpile"
    started = time.perf_counter()
    signal.alarm(120)
    try:
        with (patch.object(AerSimulator, "run", new=aer_run),
              patch.object(solution, "verify_public_candidate", new=candidate_check)):
            recovery = solution.recover_exponent_with_diagnostics()
        report["quantum_recovery_seconds"] = round(time.perf_counter() - started, 6)
        report["peak_rss_before_scoring_mib"] = peak_rss_mib()
        signal.alarm(0)
        diagnostics = recovery.diagnostics
        report["recovery_diagnostics"] = diagnostics
        parameters = solution._public_parameters()
        order = parameters["order"]
        if not original_check(recovery.exponent, parameters):
            raise RuntimeError("Measured exponent failed the public relation")
        if recovery.counts.get(recovery.counts_key, 0) <= 0:
            raise RuntimeError("The verified witness is not an actual observed counts key")
        if (measurement_from_counts(recovery.counts_key, order) != recovery.measurement
                or equation_from_counts(recovery.counts_key, order) != (recovery.exponent, order)):
            raise RuntimeError("Witness bit order or full-modulus equation is inconsistent")
        if (report["real_aer_run_calls"] != diagnostics["aer_run_calls"]
                or not 1 <= report["real_aer_run_calls"] <= 2
                or report["real_total_shots"] != diagnostics["shots"]
                or not 1 <= diagnostics["shots"] <= 256):
            raise RuntimeError("Unexpected quantum sampling budget")
        if (report["observed_public_candidate_checks"] != diagnostics["public_candidate_checks"]
                or not 1 <= diagnostics["public_candidate_checks"] <= 16):
            raise RuntimeError("Unexpected measurement-derived candidate budget")
        if not 0 < diagnostics["verified_informative_support_shots"] <= diagnostics["shots"]:
            raise RuntimeError("No informative sample supports the verified exponent")
        del recovery
        report["aer_success"] = True
        report["public_relation_verified"] = True
        report["exponent_recovered_from_measurements"] = True
        report["witness_mapping_and_full_modulus_verified"] = True
        report["counts_format"] = "12 bits: left Z[5:0], right X[5:0]; no reversal"
        report["stage"] = "official_scoring_transpile_of_executed_circuit"
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
        report["scoring_source"] = "the exact native circuit passed to AerSimulator.run"
        report["scoring_success"] = True
        report["status"] = "PASS_QUANTUM_DISCRETE_LOG_AND_SCORING"
        report["stage"] = "complete"
    except Exception as error:
        # Shared-equation error messages may reveal candidate residues. Keep
        # only the stage and type, never the raw exception text or traceback.
        report["error_type"] = type(error).__name__
        if isinstance(error, solution.InsufficientQuantumEvidence):
            report["error_reason"] = "No observed candidate passed the public relation within the shot and candidate limits"
        elif isinstance(error, TimeoutError):
            report["error_reason"] = "The recorded stage exceeded its finite time budget; no automatic retry"
        elif isinstance(error, MemoryError):
            report["error_reason"] = "Memory allocation failed in the recorded stage; no automatic retry"
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
    report["process_peak_rss_mib"] = peak_rss_mib()
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS_QUANTUM_DISCRETE_LOG_AND_SCORING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
