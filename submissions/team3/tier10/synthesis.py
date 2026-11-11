"""Synthesize public permutations by fixing rows with short positive predicates.

No state initialization is assumed. The external control is attached by the
fanout emitter, after selecting a sequence of reversible work-register gates.
"""
from itertools import groupby
from operator import itemgetter

from ..tier08.modular import permutation_table
from ..tier09.modular import _positive_control_operations


def _guard(available, row):
    """Fewest high bits of available whose unsigned mask is at least row."""
    if available < row:
        raise ValueError("Cannot protect fixed rows with the available controls")
    mask = 0
    while mask < row:
        bit = 1 << (available.bit_length() - 1)
        mask |= bit
        available ^= bit
    return mask


def _short_predicates(table, shorten_clear):
    outputs = list(table)
    gates = []

    def flip(mask, targets):
        while targets:
            bit = targets & -targets
            targets ^= bit
            gates.append((mask, bit.bit_length() - 1))
            for i, value in enumerate(outputs):
                if value & mask == mask:
                    outputs[i] = value ^ bit

    for row in range(len(outputs)):
        value = outputs[row]
        # One guard works for all missing target bits.
        flip(_guard(value, row), row & ~value)
        surplus = outputs[row] & ~row
        if shorten_clear:
            while surplus:
                target = surplus & -surplus
                surplus ^= target
                flip(_guard(outputs[row] ^ target, row), target)
        else:
            flip(row, surplus)
    if outputs != list(range(len(table))):
        raise RuntimeError("Permutation synthesis did not reach identity")
    return tuple(reversed(gates))


def groups(ops):
    """Parity of targets in each run of identical work controls."""
    for mask, run in groupby(ops, key=itemgetter(0)):
        targets = 0
        for _, target in run:
            targets ^= 1 << target
        if targets:
            yield mask, targets


def _cost(operations):
    # Cheap rank for choosing among exact networks; the Checker measures cost.
    cost = 0
    for mask, targets in groups(operations):
        controls = 1 + mask.bit_count()
        mcx = (1, 6, 14)[controls - 1] if controls <= 3 else 8 * controls - 12
        cost += mcx + 2 * (targets.bit_count() - 1)
    return cost


def select_operations(d, modulus, work_bits):
    """Consider forward and reverse synthesis without changing register order."""
    table = permutation_table(d, modulus, work_bits)
    best = _positive_control_operations(table, work_bits)
    best_cost = _cost(best)
    inverse = [0] * len(table)
    for x, y in enumerate(table):
        inverse[y] = x
    for mapping, backwards in ((table, False), (inverse, True)):
        for shorten_clear in (False, True):
            ops = _short_predicates(mapping, shorten_clear)
            if backwards:
                ops = ops[::-1]  # Each generalized Toffoli is its own inverse.
            cost = _cost(ops)
            if cost < best_cost:
                best, best_cost = ops, cost
    return best
