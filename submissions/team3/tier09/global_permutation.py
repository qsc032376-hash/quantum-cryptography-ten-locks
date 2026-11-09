"""Exact fixed-mask elimination of a complete public modular permutation.

This changes the global reversible synthesis, before the existing fanout
emitter runs. It never finds a period, factors the modulus, or changes the
identity extension above the modulus. There are no additional ancillas.
"""

from ..tier08.modular import permutation_table


def _positive_control_operations(table, work_bits):
    """Return chronological exact positive-controlled X operations.

    Before row i, all smaller rows of the current permutation T are fixed.
    Consequently y=T[i] cannot be smaller than i. Freeze this initial y as
    the control mask while setting every bit of i absent from y: the targets
    are outside y, so these flips commute and take y to y|i. Every affected
    value contains y and is at least y>=i, preserving earlier fixed rows.

    Next clear every surplus bit using i as the control mask. All affected
    values are at least i, and y|i becomes i. These reversible operations
    eventually turn T into identity. Reversing their chronological order
    therefore implements the original full permutation, including padding.

    Unlike the v5 compiler, newly set bits do not become extra controls in
    this row's set stage. This enables fewer, lower-control exact fanout
    blocks without a heuristic search or a phase approximation.
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
        initial_output = outputs[row]
        missing = row & ~initial_output
        for target_bit in range(work_bits):
            if missing & (1 << target_bit):
                apply(initial_output, target_bit)
        surplus = outputs[row] & ~row
        for target_bit in range(work_bits):
            if surplus & (1 << target_bit):
                apply(row, target_bit)

    if outputs != list(range(len(outputs))):
        raise RuntimeError("Public permutation elimination did not reach identity")
    return tuple(reversed(elimination))


def _compiled_operations(multiplier, modulus, work_bits):
    """Validate public parameters and compile the full identity extension."""
    table = permutation_table(multiplier, modulus, work_bits)
    return _positive_control_operations(table, work_bits)
