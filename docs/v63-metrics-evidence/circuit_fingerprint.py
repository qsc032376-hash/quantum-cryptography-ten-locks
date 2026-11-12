#!/usr/bin/env python3
"""Parameter-free structural fingerprints for the v6.3 audit.

This deliberately is NOT a unitary or semantic fingerprint. Numeric parameter
values, global phase, labels, names of composite gates, circuit metadata and
opaque definitions are excluded. Equal digests establish equality only of the
declared schema. Exact native-parameter comparisons, where authorized, must be
performed transiently and published only as booleans in a separate diagnostic.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json


SCHEMA = "v63-parameter-free-ordered-structure-v1"
_CORE_OPERATIONS = {
    ("qiskit.circuit.measure", "Measure"): "measure",
    ("qiskit.circuit.reset", "Reset"): "reset",
    ("qiskit.circuit.barrier", "Barrier"): "barrier",
    ("qiskit.circuit.delay", "Delay"): "delay",
}


def _public_class(operation):
    """Qiskit's public base_class avoids its dynamic singleton class names."""
    base = operation.base_class
    return base.__module__, base.__qualname__


def _operation_identity(operation):
    module, name = _public_class(operation)
    if module.startswith("qiskit.circuit.library.standard_gates."):
        return operation.name, f"{module}.{name}", False
    core = _CORE_OPERATIONS.get((module, name))
    if core:
        return core, f"{module}.{name}", False
    # Public Qiskit classes are stable identifiers. Arbitrary dynamically named
    # user subclasses are normalized, so UUIDs or hidden names cannot leak.
    public_class = f"{module}.{name}" if module.startswith("qiskit.") else "opaque_user_instruction"
    identity = f"opaque:{public_class}[q={operation.num_qubits},c={operation.num_clbits}]"
    return identity, public_class, True


def _parameter_type(value):
    cls = type(value)
    module = cls.__module__
    if module == "builtins" or module.startswith(("numpy", "qiskit", "sympy")):
        return f"{module}.{cls.__qualname__}"
    return "opaque_parameter_type"


def summarize(circuit, checker):
    """Return public structure/cost metadata without descending into Gate.definition.

    Costs use the unchanged official compute_metrics function on the circuit
    representation supplied. For opaque constructed circuits this is a
    top-level cost, not the gate cost of the eventual decomposed circuit.
    """
    operations = []
    histogram = Counter()
    literal_cx = 0
    opaque_count = 0
    measurement_map = []
    for instruction in circuit.data:
        operation = instruction.operation
        identity, public_class, opaque = _operation_identity(operation)
        qargs = [circuit.find_bit(bit).index for bit in instruction.qubits]
        cargs = [circuit.find_bit(bit).index for bit in instruction.clbits]
        parameter_types = [_parameter_type(value) for value in operation.params]
        operations.append({
            "operation": identity,
            "public_class": public_class,
            "quantum_arity": operation.num_qubits,
            "classical_arity": operation.num_clbits,
            "qargs": qargs,
            "cargs": cargs,
            "parameter_types": parameter_types,
        })
        histogram[identity] += 1
        literal_cx += operation.name == "cx"
        opaque_count += opaque
        if identity == "measure":
            measurement_map.append({"qargs": qargs, "cargs": cargs})
    canonical = {
        "schema": SCHEMA,
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "operations": operations,
    }
    payload = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    return {
        "schema": SCHEMA,
        "structural_digest": hashlib.sha256(payload).hexdigest(),
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "literal_cx": literal_cx,
        "metrics": checker.compute_metrics(circuit),
        "instruction_histogram": dict(sorted(histogram.items())),
        "instruction_count_including_measurements": len(circuit.data),
        "opaque_instruction_count": opaque_count,
        "measurement_map": measurement_map,
        "metric_scope": "stored representation; opaque composites are not expanded",
        "digest_scope": "ordered public structure only; numeric parameters and global phase excluded",
    }
