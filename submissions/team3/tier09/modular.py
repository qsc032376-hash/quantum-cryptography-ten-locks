"""Compile a public modular permutation into positive-controlled X gates.

The compiler enumerates the public truth table to synthesize a reversible
circuit; it does not inspect permutation cycles or calculate an order or
factor. The representation is intended for small challenge moduli, not for
scalable large-integer modular arithmetic.

Native MCX names are preserved so Aer can execute these gates directly. The
official scoring transform separately decomposes the same executed circuit
into its prescribed basis. No dense unitary or additional ancilla is used.
"""

from collections import Counter

from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

from ..tier08.modular import permutation_table


def _positive_control_operations(table, work_bits):
    """Return chronological ``(positive_control_mask, target_bit)`` pairs.

    Let T be the current output table. Process input rows i in increasing
    order, with all earlier rows already fixed. Its current output y=T[i]
    cannot be smaller than i, because T remains a permutation.

    First set each missing one-bit of i, using every current one-bit of y
    as a positive control. Any affected basis value contains all bits of y,
    so is at least y >= i. Next clear each surplus one-bit using all one-bits
    of i as controls; any affected value is at least i. Thus neither stage
    changes any earlier fixed row. The target bit is absent from its control
    mask in both stages. Applying each gate to every output preserves the
    permutation and eventually makes T the identity.

    These elimination gates act on the output side of the original mapping.
    Since every controlled X is self-inverse, reversing their chronological
    order implements the original mapping. Adding an external positive
    control to every returned gate makes the whole mapping conditional while
    retaining exact phases and requiring no scratch register.

    The caller supplies an already validated public permutation table.
    """
    outputs = list(table)
    elimination = []

    def apply(control_mask, target_bit):
        target_mask = 1 << target_bit
        if control_mask & target_mask:
            raise RuntimeError("A synthesis target cannot also be a control")
        elimination.append((control_mask, target_bit))
        for index, value in enumerate(outputs):
            if value & control_mask == control_mask:
                outputs[index] = value ^ target_mask

    for row in range(len(outputs)):
        for target_bit in range(work_bits):
            target_mask = 1 << target_bit
            if row & target_mask and not outputs[row] & target_mask:
                apply(outputs[row], target_bit)
        for target_bit in range(work_bits):
            target_mask = 1 << target_bit
            if outputs[row] & target_mask and not row & target_mask:
                apply(row, target_bit)

    if outputs != list(range(len(outputs))):
        raise RuntimeError("Public permutation elimination did not reach identity")
    return tuple(reversed(elimination))


def _compiled_operations(multiplier, modulus, work_bits):
    table = permutation_table(multiplier, modulus, work_bits)
    return _positive_control_operations(table, work_bits)


def build_controlled_multiplier(multiplier, modulus, work_bits=7) -> QuantumCircuit:
    """Return an exact controlled modular permutation on 1 + work_bits wires.

    Local wire 0 is the external control; wires 1..work_bits encode the work
    integer little-endian. For external control 1, inputs below modulus map
    to multiplier*x % modulus and larger encodings remain fixed. For control
    0 the circuit is identity, including relative phases. There are no extra
    wires, dirty borrowing, or zero-control X normalization gates.

    Input validation and the identity extension come from Tier 8's public
    ``permutation_table``. Identity multipliers retain this register layout.
    """
    operations = _compiled_operations(multiplier, modulus, work_bits)
    circuit = QuantumCircuit(1 + work_bits, name="tier09_controlled_modular_multiply")
    for control_mask, target_bit in operations:
        controls = [0] + [
            bit + 1 for bit in range(work_bits) if control_mask & (1 << bit)
        ]
        # Do not rename this native gate: Aer recognizes mcx/cx/ccx by name.
        circuit.append(MCXGate(len(controls)), [*controls, target_bit + 1])
    return circuit


def public_compilation_stats(multiplier, modulus, work_bits=7) -> dict:
    """Return public gate counts only, without cycle/order/factor information.

    Histogram keys count all controls, including the external control.
    Gate count refers to native controlled-X blocks before basis synthesis.
    """
    operations = _compiled_operations(multiplier, modulus, work_bits)
    histogram = Counter(control_mask.bit_count() + 1 for control_mask, _ in operations)
    return {
        "gate_count": len(operations),
        "control_count_histogram": dict(sorted(histogram.items())),
        "normalizing_x_count": 0,
    }
