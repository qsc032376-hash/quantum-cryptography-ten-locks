"""Exact mixed-predicate gate emission; no order recovery or secret inputs.

Operations are chronological (mask, required_value, target_bit) work gates.
The external control is always wire 0. Work is 1..w; extra wires are dirty.
"""
from itertools import groupby
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate
from submissions.team3.tier08.modular import _mcx_template, dirty_qubit_count


def grouped(operations):
    for (mask, value), run in groupby(operations, lambda op: tuple(op[:2])):
        targets = 0
        for m, v, target in run:
            if v & ~m or m & (1 << target):
                raise ValueError('Malformed Boolean predicate')
            targets ^= 1 << target
        if targets:
            yield mask, value, targets


def build_from_operations(operations, work_bits=6, mode='dirty', pivot='first', allocation='work_first'):
    count = dirty_qubit_count(work_bits)
    circuit = QuantumCircuit(1 + work_bits + count, name='tier08_controlled_modular_multiply')
    for mask, value, target_mask in grouped(operations):
        if mask >= 1 << work_bits or target_mask >= 1 << work_bits:
            raise ValueError('Operation outside work width')
        controls = [0] + [j + 1 for j in range(work_bits) if mask >> j & 1]
        targets = [j + 1 for j in range(work_bits) if target_mask >> j & 1]
        if pivot == 'last':
            targets.reverse()
        elif pivot != 'first':
            raise ValueError('Unknown pivot')
        lead, *others = targets
        negatives = [j + 1 for j in range(work_bits) if (mask ^ value) >> j & 1]
        for q in negatives:
            circuit.x(q)
        for q in others:
            circuit.cx(lead, q)
        if mode == 'native':
            circuit.append(MCXGate(len(controls)), controls + [lead])
        elif mode == 'dirty':
            template = _mcx_template(len(controls))
            needed = template.num_qubits - len(controls) - 1
            available = [q for q in range(1, circuit.num_qubits) if q not in controls and q != lead]
            if allocation == 'external_first':
                available.sort(key=lambda q: (q <= work_bits, q))
            elif allocation != 'work_first':
                raise ValueError('Unknown dirty allocation')
            if needed > len(available):
                raise ValueError('Insufficient dirty wires')
            circuit.compose(template, controls + [lead] + available[:needed], inplace=True)
        else:
            raise ValueError('Unknown exact MCX mode')
        for q in reversed(others):
            circuit.cx(lead, q)
        for q in reversed(negatives):
            circuit.x(q)
    return circuit


def symbolic(operations, width=6):
    result = []
    for x in range(1 << width):
        for mask, value, target in operations:
            if x & mask == value:
                x ^= 1 << target
        result.append(x)
    return result
