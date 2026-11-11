"""Affine-conjugated Tier 10 multiplier overrides (research candidate)."""
import itertools
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submissions.team3.tier08.modular import permutation_table  # noqa: E402
from submissions.team3.tier10 import global_synthesis  # noqa: E402
from submissions.team3.tier10.synthesis import _short_predicates  # noqa: E402

WIDTH = 7
MODULUS = 83
CONFIG = json.loads((Path(__file__).with_name("affine_candidate.json")).read_text())


def apply_cnots(value, cnots):
    for control, target in cnots:
        if value >> control & 1:
            value ^= 1 << target
    return value


def conjugate(table, cnots, flip):
    forward = [apply_cnots(x, cnots) ^ flip for x in range(1 << WIDTH)]
    mapped = [0] * len(table)
    for x, y in enumerate(table):
        mapped[forward[x]] = forward[y]
    return mapped, forward


def invert_map(mapping):
    inverse = [0] * len(mapping)
    for x, y in enumerate(mapping):
        inverse[y] = x
    return inverse


def custom_block(ops, cnots, flip):
    circuit = QuantumCircuit(WIDTH + 1)
    for control, target in cnots:
        circuit.cx(control + 1, target + 1)
    for bit in range(WIDTH):
        if flip >> bit & 1:
            circuit.x(bit + 1)
    inner = global_synthesis.emit(ops, WIDTH)
    circuit.compose(inner, range(WIDTH + 1), inplace=True)
    for bit in range(WIDTH):
        if flip >> bit & 1:
            circuit.x(bit + 1)
    for control, target in reversed(cnots):
        circuit.cx(control + 1, target + 1)
    return circuit


def multiplier_for(d):
    entry = CONFIG.get(str(d))
    if entry is None:
        return None
    table = permutation_table(d, MODULUS, WIDTH)
    cnots = [tuple(pair) for pair in entry["cnots"]]
    conjugated, forward = conjugate(table, cnots, entry["flip"])
    source = conjugated
    if entry["inverse"]:
        source = invert_map(source)
    ops = _short_predicates(source, entry["short"])
    if entry["inverse"]:
        ops = ops[::-1]
    return custom_block([(m, m, t) for m, t in ops], cnots, entry["flip"])


def patched_fanout(original):
    def fanout(d, modulus, work_bits):
        custom = multiplier_for(d) if modulus == MODULUS and work_bits == WIDTH else None
        if custom is not None:
            return custom
        return original(d, modulus, work_bits)

    return fanout
