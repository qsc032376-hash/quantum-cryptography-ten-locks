"""Pinned official-equivalent metrics for static synthetic circuits only."""

import time
from qiskit import transpile

BASIS = ["rz", "sx", "x", "cx"]
IGNORED = {"measure", "reset", "barrier", "delay"}


def metrics(circuit):
    levels, total, two = {}, 0, 0
    for item in circuit.data:
        if item.operation.name in IGNORED:
            continue
        if getattr(item.operation, "blocks", None):
            raise ValueError("This research counter does not support control flow")
        wires = [circuit.find_bit(q).index for q in item.qubits]
        level = max((levels.get(q, 0) for q in wires), default=0) + 1
        for q in wires:
            levels[q] = level
        total += 1
        two += len(wires) == 2
    return {"two_qubit_gates": two, "total_gates": total,
            "depth": max(levels.values(), default=0),
            "allocated_qubits": circuit.num_qubits, "active_qubits": len(levels)}


def compile_metrics(circuit):
    started = time.perf_counter()
    compiled = transpile(circuit, basis_gates=BASIS, coupling_map=None,
                         initial_layout=None, optimization_level=1,
                         seed_transpiler=12345, num_processes=1)
    seconds = time.perf_counter() - started
    return compiled, {**metrics(compiled), "compilation_seconds": seconds}
