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
PUBLIC_NETWORKS = {2: ((32, 0, 0),
     (32, 0, 4),
     (4, 0, 0),
     (33, 0, 1),
     (33, 0, 4),
     (33, 0, 2),
     (34, 2, 0),
     (34, 2, 4),
     (34, 2, 2),
     (40, 8, 1),
     (40, 8, 2),
     (4, 0, 3),
     (41, 8, 2),
     (41, 8, 1),
     (4, 0, 4),
     (48, 16, 1),
     (48, 16, 2),
     (4, 0, 5),
     (57, 25, 2),
     (4, 0, 1),
     (4, 0, 0),
     (59, 27, 2),
     (4, 0, 3),
     (4, 0, 5),
     (4, 0, 4),
     (45, 0, 4),
     (37, 1, 3),
     (36, 32, 1)),
 4: ((30, 16, 5),
     (20, 16, 5),
     (20, 16, 3),
     (54, 48, 3),
     (45, 9, 4),
     (20, 16, 3),
     (20, 16, 0),
     (20, 16, 5),
     (46, 8, 0),
     (46, 8, 4),
     (36, 0, 0),
     (36, 0, 3),
     (15, 3, 5),
     (15, 3, 4),
     (20, 16, 0),
     (12, 0, 5),
     (12, 0, 0),
     (12, 0, 4),
     (4, 0, 3),
     (58, 24, 0),
     (58, 24, 2),
     (56, 24, 1),
     (50, 16, 0),
     (50, 16, 2),
     (4, 0, 4),
     (48, 16, 0),
     (48, 16, 2),
     (4, 0, 4),
     (33, 0, 4),
     (43, 9, 4),
     (41, 9, 1),
     (35, 1, 4),
     (33, 1, 1),
     (33, 1, 3),
     (42, 8, 4),
     (40, 8, 1),
     (40, 8, 0),
     (40, 8, 2),
     (4, 0, 3),
     (34, 0, 3),
     (40, 0, 1),
     (32, 0, 3),
     (32, 0, 2)),
 11: ((32, 0, 1),
      (32, 0, 4),
      (32, 0, 3),
      (36, 4, 1),
      (36, 4, 3),
      (34, 0, 0),
      (8, 8, 2),
      (8, 8, 1),
      (38, 6, 0),
      (38, 6, 3),
      (16, 0, 0),
      (33, 1, 4),
      (16, 0, 5),
      (16, 0, 2),
      (16, 0, 1),
      (16, 0, 3),
      (8, 8, 4),
      (48, 0, 2),
      (48, 0, 3),
      (8, 8, 2),
      (8, 8, 4),
      (20, 4, 5),
      (20, 4, 1),
      (20, 4, 0),
      (20, 4, 3),
      (8, 8, 5),
      (52, 4, 3),
      (18, 2, 5),
      (18, 2, 0),
      (18, 2, 3),
      (50, 34, 2),
      (22, 6, 5),
      (22, 6, 0),
      (54, 38, 3),
      (49, 33, 1),
      (21, 5, 1),
      (8, 8, 1),
      (8, 8, 0),
      (51, 3, 2),
      (51, 3, 3),
      (23, 3, 3),
      (8, 8, 1),
      (55, 7, 3),
      (8, 8, 5),
      (8, 8, 0),
      (40, 8, 0),
      (40, 8, 4),
      (42, 8, 2),
      (24, 8, 5),
      (24, 8, 1),
      (46, 12, 4),
      (41, 9, 1),
      (24, 8, 2),
      (45, 13, 1),
      (45, 13, 4),
      (24, 24, 1),
      (43, 11, 2),
      (43, 11, 4),
      (24, 8, 1),
      (56, 8, 1),
      (56, 8, 0),
      (26, 10, 2),
      (60, 12, 1),
      (58, 10, 2),
      (57, 9, 2),
      (57, 9, 1),
      (27, 11, 2),
      (61, 13, 1),
      (27, 11, 2)),
 16: ((27, 11, 2),
      (61, 13, 1),
      (27, 11, 2),
      (57, 9, 1),
      (57, 9, 2),
      (58, 10, 2),
      (60, 12, 1),
      (26, 10, 2),
      (56, 8, 0),
      (56, 8, 1),
      (24, 8, 1),
      (43, 11, 4),
      (43, 11, 2),
      (24, 24, 1),
      (45, 13, 4),
      (45, 13, 1),
      (24, 8, 2),
      (41, 9, 1),
      (46, 12, 4),
      (24, 8, 1),
      (24, 8, 5),
      (42, 8, 2),
      (40, 8, 4),
      (40, 8, 0),
      (8, 8, 0),
      (8, 8, 5),
      (55, 7, 3),
      (8, 8, 1),
      (23, 3, 3),
      (51, 3, 3),
      (51, 3, 2),
      (8, 8, 0),
      (8, 8, 1),
      (21, 5, 1),
      (49, 33, 1),
      (54, 38, 3),
      (22, 6, 0),
      (22, 6, 5),
      (50, 34, 2),
      (18, 2, 3),
      (18, 2, 0),
      (18, 2, 5),
      (52, 4, 3),
      (8, 8, 5),
      (20, 4, 3),
      (20, 4, 0),
      (20, 4, 1),
      (20, 4, 5),
      (8, 8, 4),
      (8, 8, 2),
      (48, 0, 3),
      (48, 0, 2),
      (8, 8, 4),
      (16, 0, 3),
      (16, 0, 1),
      (16, 0, 2),
      (16, 0, 5),
      (33, 1, 4),
      (16, 0, 0),
      (38, 6, 3),
      (38, 6, 0),
      (8, 8, 1),
      (8, 8, 2),
      (34, 0, 0),
      (36, 4, 3),
      (36, 4, 1),
      (32, 0, 3),
      (32, 0, 4),
      (32, 0, 1))}


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
    return build_from_operations(operations, work_bits, mode='native')
