"""Exact mixed-predicate gate emission; no order recovery or secret inputs.

Operations are chronological (mask, required_value, target_bit) work gates.
The external control is always wire 0. Work is 1..w; extra wires are dirty.
"""
from itertools import groupby
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate
from .modular import _mcx_template, dirty_qubit_count, permutation_table


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


# Generated only from public modulo-35 permutation synthesis. These are gate
# networks, not recovered periods, factors, keys or plaintext. Reproduce from
# research/tier08_extreme/selected.json and the recorded exact synthesis stages.
PUBLIC_NETWORKS = {2: ((32, 0, 3),
     (32, 0, 2),
     (1, 1, 1),
     (34, 2, 0),
     (1, 1, 1),
     (33, 1, 4),
     (8, 0, 4),
     (48, 16, 3),
     (8, 0, 2),
     (36, 4, 3),
     (36, 4, 4),
     (36, 4, 0),
     (8, 0, 2),
     (8, 0, 0),
     (37, 5, 3),
     (8, 0, 2),
     (8, 0, 5),
     (53, 21, 3),
     (8, 0, 0),
     (8, 0, 1),
     (55, 23, 3),
     (8, 0, 2),
     (8, 0, 4),
     (8, 0, 1),
     (8, 0, 5),
     (40, 0, 0),
     (45, 5, 4)),
 4: ((54, 20, 3),
     (34, 0, 4),
     (30, 0, 5),
     (57, 24, 2),
     (33, 0, 3),
     (50, 2, 2),
     (50, 2, 3),
     (48, 0, 1),
     (48, 0, 0),
     (36, 0, 4),
     (48, 0, 2),
     (40, 0, 0),
     (40, 0, 2),
     (37, 0, 3),
     (32, 0, 0),
     (32, 0, 4),
     (29, 0, 5),
     (32, 0, 0),
     (32, 0, 4),
     (32, 0, 2),
     (32, 0, 3)),
 11: ((32, 0, 0),
      (32, 0, 4),
      (29, 0, 5),
      (32, 0, 3),
      (48, 0, 3),
      (48, 0, 2),
      (40, 0, 4),
      (2, 0, 2),
      (2, 0, 3),
      (2, 0, 4),
      (36, 0, 1),
      (33, 0, 3),
      (33, 0, 2),
      (2, 0, 3),
      (2, 0, 0),
      (2, 0, 2),
      (41, 0, 1),
      (2, 0, 0),
      (2, 0, 4),
      (45, 8, 1),
      (48, 0, 3),
      (48, 0, 0),
      (2, 0, 3),
      (2, 0, 2),
      (2, 0, 0),
      (56, 0, 1),
      (2, 0, 4),
      (60, 8, 1),
      (2, 0, 4),
      (57, 0, 1),
      (2, 0, 0),
      (2, 0, 4),
      (2, 0, 3),
      (53, 0, 3),
      (61, 8, 1),
      (2, 0, 2),
      (2, 0, 4),
      (34, 0, 3),
      (34, 0, 2),
      (34, 0, 0),
      (30, 0, 5),
      (34, 0, 3),
      (34, 0, 0),
      (31, 0, 5),
      (34, 0, 3),
      (50, 16, 3),
      (50, 16, 0),
      (42, 8, 4),
      (46, 4, 0),
      (35, 1, 2),
      (50, 0, 0),
      (50, 0, 2),
      (43, 0, 4),
      (50, 0, 2),
      (39, 0, 4),
      (50, 0, 3),
      (50, 0, 2),
      (54, 0, 0)),
 16: ((54, 0, 0),
      (50, 0, 2),
      (50, 0, 3),
      (39, 0, 4),
      (50, 0, 2),
      (43, 0, 4),
      (50, 0, 2),
      (50, 0, 0),
      (35, 1, 2),
      (46, 4, 0),
      (42, 8, 4),
      (50, 16, 0),
      (50, 16, 3),
      (34, 0, 3),
      (31, 0, 5),
      (34, 0, 0),
      (34, 0, 3),
      (30, 0, 5),
      (34, 0, 0),
      (34, 0, 2),
      (34, 0, 3),
      (2, 0, 4),
      (2, 0, 2),
      (61, 8, 1),
      (53, 0, 3),
      (2, 0, 3),
      (2, 0, 4),
      (2, 0, 0),
      (57, 0, 1),
      (2, 0, 4),
      (60, 8, 1),
      (2, 0, 4),
      (56, 0, 1),
      (2, 0, 0),
      (2, 0, 2),
      (2, 0, 3),
      (48, 0, 0),
      (48, 0, 3),
      (45, 8, 1),
      (2, 0, 4),
      (2, 0, 0),
      (41, 0, 1),
      (2, 0, 2),
      (2, 0, 0),
      (2, 0, 3),
      (33, 0, 2),
      (33, 0, 3),
      (36, 0, 1),
      (2, 0, 4),
      (2, 0, 3),
      (2, 0, 2),
      (40, 0, 4),
      (48, 0, 2),
      (48, 0, 3),
      (32, 0, 3),
      (29, 0, 5),
      (32, 0, 4),
      (32, 0, 0))}


def build_controlled_multiplier(multiplier, modulus=35, work_bits=6):
    """Exact public cached network, with every work/padding branch checked.

    Two idle local dirty-wire slots retain the original caller ABI. Native
    MCX gates do not assume a zero pivot or these slots initially zero.
    Full-circuit synthesis may allocate workspace under Qiskit's state tracking.
    """
    expected = permutation_table(multiplier, modulus, work_bits)
    if modulus != 35 or work_bits != 6:
        raise ValueError("The cached networks are scoped to public Tier 8")
    operations = PUBLIC_NETWORKS[multiplier % modulus]
    if symbolic(operations, work_bits) != expected:
        raise RuntimeError("Public-operation cache does not match modular specification")
    return build_from_operations(operations, work_bits, mode='native', pivot='last')
