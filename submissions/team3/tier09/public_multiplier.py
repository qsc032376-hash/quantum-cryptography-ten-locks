"""Controlled multiplication using the approved public mod-77 networks."""
import itertools
import json
from functools import lru_cache
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

from .shared_controls import build_controlled_multiplier as generic_multiplier

WIDTH = 7
PUBLIC_MULTIPLIERS = frozenset({2, 4, 9, 16, 25})


@lru_cache(maxsize=1)
def _operations():
    return json.loads(Path(__file__).with_name("public_operations.json").read_bytes())


def grouped(ops):
    for (mask, val), run in itertools.groupby(ops, lambda o: o[:2]):
        targets = 0
        for _, _, target in run:
            targets ^= 1 << target
        if targets:
            yield mask, val, targets


def emit(ops, width=WIDTH, pivot_last=False):
    circuit = QuantumCircuit(width + 1)
    for mask, val, targets in grouped(ops):
        bits = [j + 1 for j in range(width) if targets >> j & 1]
        controls = [0] + [j + 1 for j in range(width) if mask >> j & 1]
        negative = [j + 1 for j in range(width) if (mask ^ val) >> j & 1]
        if pivot_last:
            bits.reverse()
        pivot, *others = bits
        for j in negative:
            circuit.x(j)
        for j in others:
            circuit.cx(pivot, j)
        circuit.append(MCXGate(len(controls)), controls + [pivot])
        for j in others[::-1]:
            circuit.cx(pivot, j)
        for j in negative:
            circuit.x(j)
    return circuit


def build_controlled_multiplier(multiplier, modulus, work_bits=WIDTH):
    if (modulus, work_bits) == (77, WIDTH) and multiplier in PUBLIC_MULTIPLIERS:
        return emit(_operations()[str(multiplier)], work_bits)
    return generic_multiplier(multiplier, modulus, work_bits)
