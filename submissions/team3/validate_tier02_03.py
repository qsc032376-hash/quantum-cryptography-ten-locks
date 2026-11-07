"""Run artificial tests, then one real Tier 2 and Tier 3 validation.

Only aggregate resource/QBER statistics are persisted. Never serialize keys,
plaintext, measured bits, per-oracle classifications, or hidden preparations.
The Tier 2 scorer uses Bob's public measurement circuits in Channel.log.
"""

from collections import Counter
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

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import is_correct
from submissions.team3.tier02 import solution as bb84
from submissions.team3.tier03 import solution as dj


REPORT_PATH = Path(__file__).with_name("tier02_03_validation.json")
BASIS_GATES = ["rz", "sx", "x", "cx"]


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
        "depth_including_measurements": circuit.depth(),
    }


def summarize_metrics(metrics):
    """Keep the distribution, but omit any association with Oracle indices."""
    fields = tuple(metrics[0])
    histogram = Counter(tuple(entry[field] for field in fields) for entry in metrics)
    return {
        "circuit_count": len(metrics),
        "total_gate_count": sum(m["gate_count"] for m in metrics),
        "total_two_qubit_gate_count": sum(m["two_qubit_gate_count"] for m in metrics),
        "max_gate_depth": max(m["gate_depth"] for m in metrics),
        "scoring_selected_circuit": max(
            metrics, key=lambda m: (m["two_qubit_gate_count"], m["gate_depth"])
        ),
        "metric_histogram_without_oracle_indices": [
            {"occurrences": count, **dict(zip(fields, values))}
            for values, count in sorted(histogram.items())
        ],
    }


def tier02_validation(report):
    channel_type = bb84.helper.Channel
    original_init = channel_type.__init__
    original_receive = channel_type.receive_all
    original_finish = channel_type.finish
    original_reconcile = bb84.helper.reconcile
    original_recover = bb84.recover_key_with_diagnostics
    original_run = AerSimulator.run
    names = {}
    events = []
    calls = {name: Counter() for name in bb84.helper.LINKS}
    report.update(aer_run_calls=0, aer_experiments=0, total_shots=0, reconcile_invocations=0)

    def channel_init(channel, name):
        names[id(channel)] = name  # Public constructor argument, not private state.
        calls[name]["construct"] += 1
        events.append(["construct", name])
        original_init(channel, name)

    def receive(channel, circuits):
        name = names[id(channel)]
        calls[name]["receive_all"] += 1
        events.append(["receive_all", name])
        return original_receive(channel, circuits)

    def finish(channel):
        name = names[id(channel)]
        calls[name]["finish"] += 1
        events.append(["finish", name])
        return original_finish(channel)

    def reconcile(*args, **kwargs):
        report["reconcile_invocations"] += 1
        return original_reconcile(*args, **kwargs)

    def recover():
        key, diagnostics = original_recover()
        report["measurement_diagnostics"] = diagnostics
        return key, diagnostics

    def aer_run(simulator, circuits, *args, **kwargs):
        # Count only. Do not inspect the hidden state preparations composed by Channel.
        count = 1 if isinstance(circuits, QuantumCircuit) else len(circuits)
        report["aer_run_calls"] += 1
        report["aer_experiments"] += count
        report["total_shots"] += count * kwargs.get("shots", simulator.options.shots)
        return original_run(simulator, circuits, *args, **kwargs)

    with (
        patch.object(channel_type, "__init__", new=channel_init),
        patch.object(channel_type, "receive_all", new=receive),
        patch.object(channel_type, "finish", new=finish),
        patch.object(bb84.helper, "reconcile", new=reconcile),
        patch.object(bb84, "recover_key_with_diagnostics", new=recover),
        patch.object(AerSimulator, "run", new=aer_run),
    ):
        plaintext = bb84.solve()
    report["plaintext_hash_verified"] = bool(is_correct(2, plaintext))
    del plaintext
    report["channel_calls"] = {name: dict(counts) for name, counts in calls.items()}
    report["channel_call_order"] = events
    if not report["plaintext_hash_verified"]:
        raise RuntimeError("Tier 2 plaintext verification failed; do not remeasure")
    if any(dict(counts) != {"construct": 1, "receive_all": 1, "finish": 1} for counts in calls.values()):
        raise RuntimeError("Channel call limits were not respected")
    if report["reconcile_invocations"] != 1:
        raise RuntimeError("Expected exactly one public reconciliation")

    log = channel_type.log  # Documented public Bob circuits, before hidden preparation.
    expected = report["measurement_diagnostics"]["measurement_circuits"]
    if len(log) != expected or len({(name, index) for name, index, _ in log}) != expected:
        raise RuntimeError("Missing or repeated Channel measurements")
    for name, stats in report["measurement_diagnostics"]["links"].items():
        if {index for link, index, _ in log if link == name} != set(range(stats["qubits"])):
            raise RuntimeError("Channel did not measure every index exactly once")
    if report["aer_experiments"] != expected or report["total_shots"] != expected:
        raise RuntimeError("Expected one actual single-shot experiment per received qubit")

    # All Bob circuits have just two public shapes. Compile one actual logged
    # representative of each, then account for its observed multiplicity.
    cache = {}
    metrics = []
    for _, _, circuit in log:
        signature = tuple(item.operation.name for item in circuit.data)
        if signature not in {("measure",), ("h", "measure")}:
            raise RuntimeError("Unexpected public Bob measurement circuit")
        if signature not in cache:
            compiled = transpile(
                circuit, basis_gates=BASIS_GATES, optimization_level=1,
                seed_transpiler=12345,
            )
            cache[signature] = gate_metrics(compiled)
        metrics.append(cache[signature])
    report["scoring_metrics_for_public_bob_circuits"] = summarize_metrics(metrics)
    report["unique_link_index_measurements"] = len(log)
    report["key_recovered_from_measurements"] = True
    report["status"] = "PASS_SOLVE_AND_HASH"


def tier03_validation(report):
    original_build = dj.build_circuit
    original_run = AerSimulator.run
    oracle_indices = []
    oracle_calls = []
    report.update(aer_run_calls=0, aer_experiments=0, total_shots=0)

    def build(index=0):
        circuit = original_build(index)
        oracle_indices.append(index)
        oracle_calls.append(dj.helper.count_oracle_calls(circuit))
        report.setdefault("logical_opaque_oracle_metrics", gate_metrics(circuit))
        return circuit

    def aer_run(simulator, circuits, *args, **kwargs):
        report["aer_run_calls"] += 1
        report["aer_experiments"] += len(circuits)
        report["total_shots"] += len(circuits) * kwargs.get("shots", simulator.options.shots)
        report["executed_basis_circuit_metrics"] = summarize_metrics(
            [gate_metrics(circuit) for circuit in circuits]
        )
        return original_run(simulator, circuits, *args, **kwargs)

    with patch.object(dj, "build_circuit", new=build), patch.object(AerSimulator, "run", new=aer_run):
        key_bits = dj.recover_key_bits()
    if not isinstance(key_bits, str) or len(key_bits) != 24 or set(key_bits) - {"0", "1"}:
        raise RuntimeError("Expected a 24-character classification string")
    del key_bits
    if oracle_indices != list(range(24)) or oracle_calls != [1] * 24:
        raise RuntimeError("Oracle order or one-query limit failed")
    if (report["aer_run_calls"], report["aer_experiments"], report["total_shots"]) != (1, 24, 24):
        raise RuntimeError("Expected one batch of 24 single-shot circuits")
    report["oracle_indices_executed"] = oracle_indices
    report["oracle_calls_before_transpilation"] = oracle_calls
    report["key_recovered_from_measurements"] = True
    report["plaintext_hash_verified"] = False
    report["solve_status"] = (
        "NOT_VALIDATED" if Path(__file__).with_name("classical_keystream.py").is_file()
        else "PENDING_CLASSICAL_INTEGRATION"
    )
    report["status"] = "PASS_QUANTUM_ONLY"


def main():
    report = {
        "status": "FAIL",
        "python": platform.python_version(),
        "qiskit": importlib.metadata.version("qiskit"),
        "qiskit_aer": importlib.metadata.version("qiskit-aer"),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
        "tested_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "basis_gates": BASIS_GATES,
        "optimization_level": 1,
        "seed_transpiler": 12345,
        "per_tier_timeout_seconds": 120,
        "secret_values_recorded": False,
        "tier02": {"status": "NOT_RUN"},
        "tier03": {"status": "NOT_RUN"},
    }
    if sys.version_info[:2] != (3, 12) or (report["qiskit"], report["qiskit_aer"]) != ("2.6.1", "0.18.2"):
        raise RuntimeError("Use Python 3.12 and the official Qiskit/Aer versions")
    if report["branch"] != "feature/quantum-circuits":
        raise RuntimeError("Run on feature/quantum-circuits")
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "submissions.team3.tier02.test_solution", "submissions.team3.tier03.test_solution"
    ])
    tests = unittest.TextTestRunner(verbosity=1).run(suite)
    report["unit_tests_run"] = tests.testsRun
    report["unit_tests_passed"] = tests.wasSuccessful()

    def timed_out(_signum, _frame):
        raise TimeoutError("Tier runtime exceeded the budget; do not retry")

    if tests.wasSuccessful():
        previous_handler = signal.signal(signal.SIGALRM, timed_out)
        try:
            for name, validate in (("tier02", tier02_validation), ("tier03", tier03_validation)):
                started = time.perf_counter()
                signal.alarm(120)
                try:
                    validate(report[name])
                except Exception as error:
                    report[name]["status"] = "FAIL"
                    report[name]["error_type"] = type(error).__name__
                finally:
                    signal.alarm(0)
                report[name]["validation_seconds"] = round(time.perf_counter() - started, 6)
                REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                print(name + ": " + report[name]["status"], flush=True)
        finally:
            signal.signal(signal.SIGALRM, previous_handler)

    passed = report["tier02"]["status"] == "PASS_SOLVE_AND_HASH" and report["tier03"]["status"] == "PASS_QUANTUM_ONLY"
    if passed:
        report["status"] = "PASS_TIER02_SOLVE_AND_TIER03_QUANTUM"
    report["process_peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Validation record: " + str(REPORT_PATH))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
