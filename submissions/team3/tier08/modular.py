"""Compile small public modular permutations into exact controlled gates.

No dense unitary matrix is synthesized. Public permutation cycles are used
solely to compile basis transpositions; their lengths are neither returned
nor used to determine an order or factor. Dirty ancillas are restored exactly,
including when entangled with the work or other phase-estimation controls.
"""

from functools import lru_cache
from math import gcd

from qiskit import QuantumCircuit
from qiskit.synthesis import synth_mcx_n_dirty_i15


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
    """Private synthesis template; wire order is controls, target, ancillas."""
    if controls == 1:
        circuit = QuantumCircuit(2)
        circuit.cx(0, 1)
        return circuit
    if controls == 2:
        circuit = QuantumCircuit(3)
        circuit.ccx(0, 1, 2)
        return circuit
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
        seen.add(anchor)
        current = table[anchor]
        # Append (anchor, p(anchor)), (anchor, p^2(anchor)), ... in that
        # order to realize p. Traversal is only a generic permutation compiler;
        # no cycle length is recorded or used as an order-finding result.
        while current != anchor:
            if current in seen:
                raise RuntimeError("The public mapping is not a disjoint-cycle permutation")
            seen.add(current)
            _append_basis_transposition(circuit, anchor, current, work, dirty, mcx)
            current = table[current]
    return circuit
