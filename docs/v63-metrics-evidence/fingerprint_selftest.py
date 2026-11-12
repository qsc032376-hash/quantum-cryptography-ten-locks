#!/usr/bin/env python3
"""Cheap synthetic checks of audit metadata only; never execute Aer."""

import argparse
import ast
import importlib.util
import json
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.circuit import Gate


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    for filename in ("circuit_fingerprint.py", "four_stage_probe.py"):
        ast.parse((root / filename).read_text())
    helper = load(root / "circuit_fingerprint.py", "fingerprint_selftest_helper")
    probe = load(root / "four_stage_probe.py", "fingerprint_selftest_probe")
    checker = load(args.official_root / "tools/check_submission.py", "checker_selftest")
    def native_circuit(angle):
        circuit = QuantumCircuit(2, 2, name="ignored_A")
        circuit.sx(0)
        circuit.rz(angle, 0)
        circuit.cx(0, 1)
        circuit.measure([0, 1], [0, 1])
        return circuit

    first = native_circuit(0.125)
    second = native_circuit(0.875)
    second.name = "ignored_B"
    second.metadata = {"ignored": "metadata"}
    second.global_phase = 0.375
    a, b = helper.summarize(first, checker), helper.summarize(second, checker)
    assert a["structural_digest"] == b["structural_digest"]
    assert a["literal_cx"] == 1 and a["metrics"]["two_qubit_gates"] == 1
    assert not probe.native_equal(first, second)
    assert probe.native_equal(first, first.copy())
    parameter_only = native_circuit(0.875)
    assert not probe.native_equal(first, parameter_only)
    reversed_wire = QuantumCircuit(2, 2)
    reversed_wire.sx(1)
    reversed_wire.rz(0.125, 1)
    reversed_wire.cx(1, 0)
    reversed_wire.measure([0, 1], [0, 1])
    assert a["structural_digest"] != helper.summarize(reversed_wire, checker)["structural_digest"]
    opaque_a, opaque_b = QuantumCircuit(2), QuantumCircuit(2)
    opaque_a.append(Gate("arbitrary_label_alpha", 2, [0.125]), [0, 1])
    opaque_b.append(Gate("arbitrary_label_beta", 2, [0.875]), [0, 1])
    oa, ob = helper.summarize(opaque_a, checker), helper.summarize(opaque_b, checker)
    assert oa["structural_digest"] == ob["structural_digest"]
    assert oa["opaque_instruction_count"] == 1
    serialized = json.dumps(oa)
    assert "arbitrary_label_alpha" not in serialized and "0.125" not in serialized
    try:
        probe.native_equal(opaque_a, opaque_b)
    except ValueError:
        pass
    else:
        raise AssertionError("Native equality must reject opaque gates")
    result = {
        "ast_parse": "PASS", "parameter_phase_metadata_exclusion": "PASS",
        "wire_order_sensitive": "PASS", "opaque_name_parameter_exclusion": "PASS",
        "literal_cx_and_official_metrics": "PASS", "native_exact_equality_guards": "PASS",
        "quantum_execution": False,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
