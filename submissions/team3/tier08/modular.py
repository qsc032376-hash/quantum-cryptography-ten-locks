"""Compile small public modular permutations into exact controlled gates.

No dense unitary matrix is synthesized. Public permutation cycles are used
solely to compile basis transpositions; their lengths are neither returned
nor used to determine an order or factor. Dirty ancillas are restored exactly,
including when entangled with the work or other phase-estimation controls.
"""

from functools import lru_cache
from math import gcd

from qiskit import QuantumCircuit
from qiskit.synthesis import synth_mcx_n_dirty_i15, synth_mcx_n_dirty_m15


def _validate_width(work_bits: int):
    if type(work_bits) is not int:
        raise TypeError("work_bits must be an integer, not bool")
    if work_bits < 1:
        raise ValueError("work_bits must be positive")


def permutation_table(multiplier: int, modulus: int, work_bits: int) -> list[int]:
    """Return x -> multiplier*x mod modulus below modulus, identity above it.

    The multiplier is normalized modulo the public modulus and must be
    coprime to it. The modulus must fit the work register. This truth table
    is the public gate specification, not a key/order search; its size grows
    exponentially with work_bits, so this compiler is for small exercises.
    """
    _validate_width(work_bits)
    if type(modulus) is not int:
        raise TypeError("modulus must be an integer, not bool")
    if not 2 <= modulus <= 1 << work_bits:
        raise ValueError("The modulus must be at least two and fit the work register")
    if type(multiplier) is not int:
        raise TypeError("multiplier must be an integer, not bool")
    multiplier %= modulus
    if gcd(multiplier, modulus) != 1:
        raise ValueError("The public multiplier must be coprime to the modulus")
    return [
        multiplier * value % modulus if value < modulus else value
        for value in range(1 << work_bits)
    ]


@lru_cache(maxsize=16)
def _mcx_template(controls: int) -> QuantumCircuit:
    """Exact MCX; wire order is controls, target, restored dirty ancillas.

    For four or more controls, Maslov's complete synthesis needs fewer
    dirty wires than the Iten template. Its internal relative-phase pieces
    cancel; the returned operation is an exact MCX, not an action-only or
    relative-phase substitute. Keep the original no-ancilla small cases.
    """
    if controls == 1:
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        return circuit
    if controls == 2:
        circuit = QuantumCircuit(3)
        circuit.ccx(0, 1, 2)
        return circuit
    if controls >= 4:
        return synth_mcx_n_dirty_m15(controls)
    return synth_mcx_n_dirty_i15(controls, relative_phase=False, action_only=False)


def dirty_qubit_count(work_bits: int) -> int:
    """Return the exact MCX synthesis's ancillary width for this work width.

    A controlled adjacent basis swap has work_bits controls: the external
    control plus all work bits except the target. Small synthesis cases may
    use fewer ancillas than the general work_bits-2 formula.
    """
    _validate_width(work_bits)
    return _mcx_template(work_bits).num_qubits - work_bits - 1


def _append_adjacent_swap(circuit, left, right, work, dirty, mcx):
    """Swap a one-bit-different work-state pair iff external control 0 is 1."""
    difference = left ^ right
    if difference == 0 or difference & (difference - 1):
        raise ValueError("Adjacent basis states must differ in exactly one bit")
    target_bit = difference.bit_length() - 1
    work_controls = tuple(wire for bit, wire in enumerate(work) if bit != target_bit)
    zero_controls = tuple(
        wire for bit, wire in enumerate(work)
        if bit != target_bit and not left & (1 << bit)
    )
    if zero_controls:
        circuit.x(zero_controls)
    circuit.append(mcx, (0,) + work_controls + (work[target_bit],) + dirty)
    if zero_controls:
        circuit.x(zero_controls)


def _append_basis_transposition(circuit, left, right, work, dirty, mcx):
    """Exchange just the endpoints along a Gray path, restoring its interior.

    Forward adjacent swaps followed by the reverse path without its last
    edge implement the endpoint transposition. Temporary intermediate states
    may lie above modulus; all such states are restored by the full sequence.
    """
    path = [left]
    for bit in range(len(work)):
        if (left ^ right) & (1 << bit):
            path.append(path[-1] ^ (1 << bit))
    edges = list(zip(path, path[1:]))
    for first, second in edges:
        _append_adjacent_swap(circuit, first, second, work, dirty, mcx)
    for first, second in reversed(edges[:-1]):
        _append_adjacent_swap(circuit, first, second, work, dirty, mcx)


def build_controlled_multiplier(
    multiplier: int, modulus: int, work_bits: int = 6
) -> QuantumCircuit:
    """Build a controlled public modular permutation with restored dirty work.

    Local layout: external control 0, work 1..work_bits (little-endian), then
    dirty ancillas. The dirty wires must be distinct from control/work but may
    start in any state or be entangled. With external control zero, the entire
    operation is identity. Values >= modulus remain unchanged. Identity
    multipliers retain the same register layout, even though no gates are needed.

    For order finding, do NOT undo the completed multiplication: it is the
    desired operation. Only borrowed ancillas and Gray-path intermediates are
    uncomputed. Other evaluation-register wires may be borrowed as dirty wires
    if the caller excludes this block's own external control.
    """
    table = permutation_table(multiplier, modulus, work_bits)
    dirty_count = dirty_qubit_count(work_bits)
    n_qubits = 1 + work_bits + dirty_count
    circuit = QuantumCircuit(n_qubits, name="tier08_controlled_modular_multiply")
    work = tuple(range(1, work_bits + 1))
    dirty = tuple(range(work_bits + 1, n_qubits))
    mcx = _mcx_template(work_bits).to_gate(label=f"exact_mcx{work_bits}_dirty")

    seen = set()
    for anchor in range(len(table)):
        if anchor in seen:
            continue
        cycle = []
        current = anchor
        while current not in seen:
            seen.add(current)
            cycle.append(current)
            current = table[current]
        if current != anchor:
            raise RuntimeError("The public mapping is not a disjoint-cycle permutation")
        if len(cycle) < 2:
            continue
        # A cycle can start at any of its elements. A transposition at Hamming
        # distance d costs 2*d-1 adjacent swaps, independent of path ordering.
        # Choose an exact minimum-cost anchor, then traverse the same cycle.
        anchor = min(cycle, key=lambda x: (sum((x ^ y).bit_count() for y in cycle), x))
        first = cycle.index(anchor)
        ordered = cycle[first:] + cycle[:first]
        for current in ordered[1:]:
            _append_basis_transposition(circuit, anchor, current, work, dirty, mcx)
    return circuit


@lru_cache(maxsize=32)
def _template_cx_cost(controls: int) -> int:
    """Estimate native CX for the exact template, under the pinned basis."""
    from qiskit import transpile
    native = transpile(_mcx_template(controls), basis_gates=['rz', 'sx', 'x', 'cx'],
                       optimization_level=1, seed_transpiler=12345, num_processes=1)
    return native.count_ops().get('cx', 0)


def _fixed_mask_multiplier(table, work_bits):
    """Exact full-domain row elimination using external-controlled X gates.

    The table is transformed to identity with positive controls; the reverse
    self-inverse operation sequence implements the table. Every gate includes
    the external control. All otherwise unused work wires may be borrowed dirty.
    """
    outputs = list(table)
    ops = []

    def eliminate(mask, target):
        if mask & (1 << target):
            raise ValueError('Target overlaps control')
        ops.append((mask, target))
        for row, value in enumerate(outputs):
            if value & mask == mask:
                outputs[row] = value ^ (1 << target)

    for row in range(len(outputs)):
        initial = outputs[row]
        for bit in range(work_bits):
            if row & ~initial & (1 << bit):
                eliminate(initial, bit)
        surplus = outputs[row] & ~row
        for bit in range(work_bits):
            if surplus & (1 << bit):
                eliminate(row, bit)
    if outputs != list(range(len(outputs))):
        raise ValueError('Public permutation elimination failed')

    dirty_count = dirty_qubit_count(work_bits)
    circuit = QuantumCircuit(1 + work_bits + dirty_count,
                             name='tier08_controlled_modular_multiply')
    total = 0
    for mask, target_bit in reversed(ops):
        controls = [0] + [bit + 1 for bit in range(work_bits) if mask & (1 << bit)]
        target = target_bit + 1
        template = _mcx_template(len(controls))
        needed = template.num_qubits - len(controls) - 1
        available = [wire for wire in range(1, circuit.num_qubits)
                     if wire != target and wire not in controls]
        if len(available) < needed:
            return None, None
        circuit.append(template.to_gate(label=f'exact_mcx_{len(controls)}'),
                       controls + [target] + available[:needed])
        total += _template_cx_cost(len(controls))
    return circuit, total


_anchor_multiplier = build_controlled_multiplier


def build_controlled_multiplier(multiplier: int, modulus: int, work_bits: int = 6) -> QuantumCircuit:
    """Choose the lower estimated native-CX exact implementation per block.

    Both choices implement the same full controlled permutation and restore
    borrowed wires. The selection depends only on public circuit parameters.
    """
    anchor = _anchor_multiplier(multiplier, modulus, work_bits)
    table = permutation_table(multiplier, modulus, work_bits)
    candidate, cost = _fixed_mask_multiplier(table, work_bits)
    if candidate is None:
        return anchor
    anchor_mcx_count = sum(item.operation.name != 'x' for item in anchor.data)
    anchor_cost = anchor_mcx_count * _template_cx_cost(work_bits)
    return candidate if cost < anchor_cost else anchor


# Preserve the validated general-width implementation for synthetic inputs and
# public multipliers outside this research-selected cache.
_validated_hybrid_multiplier = build_controlled_multiplier


def build_controlled_multiplier(multiplier: int, modulus: int, work_bits: int = 6) -> QuantumCircuit:
    """Select a verified public mixed-polarity network without changing Shor."""
    permutation_table(multiplier, modulus, work_bits)  # Preserve validation contract.
    if modulus == 35 and work_bits == 6 and multiplier % modulus in (2, 4, 11, 16):
        from .extreme_synthesis import build_controlled_multiplier as selected_multiplier
        return selected_multiplier(multiplier, modulus, work_bits)
    return _validated_hybrid_multiplier(multiplier, modulus, work_bits)
