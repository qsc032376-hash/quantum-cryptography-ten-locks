"""Exact linear reversible synthesis on explicit, eligible CNOT-only blocks."""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate


def binary_matrix(matrix):
    matrix = np.asarray(matrix)
    if (matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]
            or not matrix.shape[0] or not np.all((matrix == 0) | (matrix == 1))):
        raise ValueError("Expected a nonempty square binary matrix")
    return matrix.astype(np.uint8, copy=True)


def extract_matrix(circuit):
    """Return M in y=Mx, bit j = wire j; global phase is separate metadata.

    Never expands nested or opaque blocks. The caller must own the eligible
    block; this function grants no permission to inspect a protected Oracle.
    """
    if circuit.num_clbits or not circuit.num_qubits:
        raise ValueError("Expected quantum wires only")
    matrix = np.eye(circuit.num_qubits, dtype=np.uint8)
    for item in circuit.data:
        if item.operation.base_class is not CXGate or item.operation.ctrl_state != 1:
            raise ValueError("Only explicit positive-control CX gates are eligible")
        control, target = [circuit.find_bit(q).index for q in item.qubits]
        matrix[target] ^= matrix[control]
    return matrix


def synthesize(matrix):
    """Gauss-Jordan reduction, reverse its self-inverse elementary row adds."""
    matrix = binary_matrix(matrix)
    n = len(matrix)
    operations = []

    def add(control, target):
        matrix[target] ^= matrix[control]
        operations.append((control, target))

    for column in range(n):
        pivot = next((row for row in range(column, n) if matrix[row, column]), None)
        if pivot is None:
            raise ValueError("Singular matrix is not a reversible CNOT map")
        if pivot != column:
            # Exact row exchange, with wire labels preserved.
            add(pivot, column)
            add(column, pivot)
            add(pivot, column)
        for row in range(n):
            if row != column and matrix[row, column]:
                add(column, row)
    circuit = QuantumCircuit(n, name="gf2_synthesized")
    for control, target in reversed(operations):
        circuit.cx(control, target)
    return circuit


def optimize(circuit):
    """Return (circuit, accepted); refuse logical count or depth regressions.

    This is a heuristic candidate, not minimum-CNOT synthesis. The fixed
    official-equivalent compiler still needs a separate measured comparison.
    """
    matrix = extract_matrix(circuit)
    candidate = synthesize(matrix)
    candidate.global_phase = circuit.global_phase
    if not np.array_equal(extract_matrix(candidate), matrix):
        raise AssertionError("Internal GF(2) equivalence failure")
    before = (len(circuit.data), circuit.depth())
    after = (len(candidate.data), candidate.depth())
    accepted = all(a <= b for a, b in zip(after, before)) and after != before
    return (candidate if accepted else circuit.copy()), accepted


def gf2_runs(circuit):
    """Maximal consecutive native CX windows; no nested definitions opened."""
    result = circuit.copy_empty_like()
    pending = []
    stats = {'windows': 0, 'accepted': 0, 'removed_cx': 0, 'max_window_wires': 0}
    certificates = []
    def flush():
        if not pending:
            return
        wires = sorted({circuit.find_bit(q).index for item in pending for q in item.qubits})
        block = QuantumCircuit(len(wires))
        for item in pending:
            block.cx(*[wires.index(circuit.find_bit(q).index) for q in item.qubits])
        candidate, accepted = optimize(block)
        assert np.array_equal(extract_matrix(block), extract_matrix(candidate))
        stats['windows'] += 1
        stats['accepted'] += accepted
        stats['removed_cx'] += block.size() - candidate.size()
        stats['max_window_wires'] = max(stats['max_window_wires'], len(wires))
        if accepted:
            certificates.append((block, candidate))
        for item in candidate.data:
            result.append(item.operation, [wires[candidate.find_bit(q).index] for q in item.qubits])
        pending.clear()
    for item in circuit.data:
        if item.operation.base_class is CXGate and item.operation.ctrl_state == 1:
            pending.append(item)
        else:
            flush()
            result.append(item)
    flush()
    return result, stats, certificates
