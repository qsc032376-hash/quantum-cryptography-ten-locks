"""Exact affine-coordinate public permutation synthesis (no quantum execution).

Operations are chronological (mask, value, target_bit). The gate toggles target
iff (work & mask) == value; the external control is added by the emitter.
"""
from itertools import groupby

WIDTH = 6
CX_COST = {1: 1, 2: 6, 3: 14, 4: 20, 5: 28, 6: 36}


def table(multiplier, modulus=35, width=WIDTH):
    from math import gcd
    if gcd(multiplier, modulus) != 1:
        raise ValueError("Public multiplier must be invertible")
    return [multiplier*x % modulus if x < modulus else x for x in range(1 << width)]


def encode(x, permutation, flip):
    return sum(((x >> old_bit) & 1) << new_bit
               for new_bit, old_bit in enumerate(permutation)) ^ flip


def inverse_table(mapping):
    inverse = [0] * len(mapping)
    for x, y in enumerate(mapping):
        inverse[y] = x
    return inverse


def short_guard(available, row):
    """Smallest number of positive controls whose unsigned mask is >= row."""
    if available < row:
        raise ValueError("No safe guard")
    guard = 0
    while guard < row:
        bit = 1 << (available.bit_length() - 1)
        guard |= bit
        available ^= bit
    return guard


def eliminate(mapping, policy="short_both", descending=False):
    """Fix each row while preserving all smaller rows, then reverse the gates.

    For a fixed row r, bijectivity implies current y>=r. Setting missing bits
    with a mask subset of y and >=r cannot touch a prior row; clearing surplus
    bits with mask r or a safe subset of the remaining value has the same
    invariant. No target appears in its control mask. Tables are full-domain.
    """
    outputs = list(mapping)
    width = (len(outputs) - 1).bit_length()
    order = range(width - 1, -1, -1) if descending else range(width)
    order = tuple(order)
    gates = []

    def flip(mask, bit):
        target = 1 << bit
        if mask & target:
            raise AssertionError("Control-target overlap")
        gates.append((mask, bit))
        for x, y in enumerate(outputs):
            if y & mask == mask:
                outputs[x] = y ^ target

    for row in range(len(outputs)):
        y = outputs[row]
        mask = short_guard(y, row) if policy != "fixed" else y
        for bit in order:
            if row & ~y & (1 << bit):
                flip(mask, bit)
        surplus = outputs[row] & ~row
        for bit in order:
            if surplus & (1 << bit):
                mask = (short_guard(outputs[row] ^ (1 << bit), row)
                        if policy == "short_both" else row)
                flip(mask, bit)
    if outputs != list(range(len(outputs))):
        raise AssertionError("Row elimination failed")
    return tuple(reversed(gates))


def simplify(operations):
    """Adjacent XOR cancellation and exact complementary-cube merging."""
    out = []
    for raw in operations:
        op = tuple(raw)
        while out:
            last = out[-1]
            if last == op:
                out.pop()
                op = None
                break
            mask, value, target = op
            if last[0] == mask and last[2] == target:
                diff = last[1] ^ value
                if diff.bit_count() == 1:
                    out.pop()
                    op = (mask ^ diff, value & (mask ^ diff), target)
                    continue
            break
        if op is not None:
            out.append(op)
    return tuple(out)


def network(multiplier, config, modulus=35, width=WIDTH):
    permutation = tuple(config["permutation"])
    flip = config["xor_mask"]
    if sorted(permutation) != list(range(width)) or not 0 <= flip < (1 << width):
        raise ValueError("Invalid affine coordinates")
    original = table(multiplier, modulus, width)
    encoding = [encode(x, permutation, flip) for x in range(1 << width)]
    # mapped = E P E^-1: at encoded input E(x), output is E(P(x)).
    mapped = [0] * len(original)
    for x, y in enumerate(original):
        mapped[encoding[x]] = encoding[y]
    if config["inverse"]:
        mapped = inverse_table(mapped)
    ops = eliminate(mapped, config["policy"], config["descending"])
    if config["inverse"]:
        ops = ops[::-1]
    # Conjugate each emitted gate back: E^-1 G E. A positive encoded control
    # j means original bit permutation[j] must equal 1 XOR flip[j]. The target
    # maps to permutation[target]. Target XOR translation cancels in a toggle.
    decoded = [(
        sum(1 << permutation[j] for j in range(width) if mask >> j & 1),
        sum(1 << permutation[j] for j in range(width)
            if mask >> j & 1 and not flip >> j & 1),
        permutation[target],
    ) for mask, target in ops]
    return simplify(decoded)


def grouped(operations):
    for (mask, value), run in groupby(operations, lambda op: tuple(op[:2])):
        targets = 0
        for _, _, target in run:
            targets ^= 1 << target
        if targets:
            if targets & mask:
                raise AssertionError("Grouped target overlaps controls")
            yield mask, value, targets


def cost(operations, fanout=True):
    """Measured isolated dirty-MCX CX costs plus exact fanout CX, not score."""
    if fanout:
        return sum(CX_COST[1 + mask.bit_count()] + 2*(targets.bit_count()-1)
                   for mask, _, targets in grouped(operations))
    return sum(CX_COST[1 + mask.bit_count()] for mask, _, _ in operations)


def apply_operations(operations, x):
    for mask, value, target in operations:
        if mask & (1 << target) or value & mask != value:
            raise AssertionError("Invalid mixed-polarity operation")
        if x & mask == value:
            x ^= 1 << target
    return x


def verify(operations, expected):
    """Full work mapping and inverse; external-off identity is structural."""
    for x, y in enumerate(expected):
        if apply_operations(operations, x) != y:
            raise AssertionError(f"Full-domain mapping mismatch at public state {x}")
        if apply_operations(reversed(operations), y) != x:
            raise AssertionError("Inverse mismatch")
    return {"work_inputs": len(expected), "inverse_inputs": len(expected),
            "padding_preserved": True, "symbolic_pass": True}
