"""Bounded Tier 9 global synthesis search (public permutations only).

Adapts the Tier 10 affine-coordinate mixed-polarity synthesis to the seven-bit
mod-77 multiplication table.  No secret, exponent, order or plaintext is read.
"""
import hashlib
import itertools
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import MCXGate
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submissions.team3.tier08.modular import permutation_table
from submissions.team3.tier09 import solution
from submissions.team3.tier10.synthesis import _short_predicates
from tools.check_submission import compute_metrics, load_config

BASIS = ["rz", "sx", "x", "cx"]
SEED = 12345
MODULUS = 77
BASE = 2
WIDTH = 7


def encode(x, perm, flip):
    return sum(((x >> p) & 1) << j for j, p in enumerate(perm)) ^ flip


def network(multiplier, perm, flip, inverse, short):
    table = permutation_table(multiplier, MODULUS, WIDTH)
    enc = [encode(x, perm, flip) for x in range(1 << WIDTH)]
    mapped = [0] * len(table)
    for x, y in enumerate(table):
        mapped[enc[x]] = enc[y]
    if inverse:
        inv = [0] * len(table)
        for x, y in enumerate(mapped):
            inv[y] = x
        mapped = inv
    ops = _short_predicates(mapped, short)
    if inverse:
        ops = ops[::-1]
    return [
        (
            sum(1 << perm[j] for j in range(WIDTH) if mask >> j & 1),
            sum(
                1 << perm[j]
                for j in range(WIDTH)
                if mask >> j & 1 and not flip >> j & 1
            ),
            perm[t],
        )
        for mask, t in ops
    ]


def simplify(ops):
    out = []
    for op in ops:
        if out and out[-1] == op:
            out.pop()
            continue
        if out and out[-1][0] == op[0] and out[-1][2] == op[2]:
            mask, val, target = op
            diff = val ^ out[-1][1]
            if diff.bit_count() == 1:
                out[-1] = (mask ^ diff, val & (mask ^ diff), target)
                continue
        out.append(op)
    return out


def grouped(ops):
    for (mask, val), run in itertools.groupby(ops, lambda o: o[:2]):
        targets = 0
        for _, _, target in run:
            targets ^= 1 << target
        if targets:
            yield mask, val, targets


def cost(ops):
    total = 0
    for mask, val, targets in grouped(ops):
        controls = 1 + mask.bit_count()
        total += ((1, 6, 14)[controls - 1] if controls <= 3 else 8 * controls - 12)
        total += 2 * (targets.bit_count() - 1)
    return total


def verify(ops, table):
    for x in range(len(table)):
        y = x
        for mask, val, target in ops:
            assert not mask >> target & 1 and val & mask == val
            if y & mask == val:
                y ^= 1 << target
        assert y == table[x]


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


def make_builder(selected, pivot_last=False):
    def multiplier(d, modulus, work_bits):
        return emit(selected[str(d)], work_bits, pivot_last)

    return multiplier


def score(circuit):
    simulator = AerSimulator(method="statevector", max_parallel_threads=2)
    started = time.perf_counter()
    native = transpile(
        circuit,
        simulator,
        basis_gates=BASIS,
        optimization_level=1,
        seed_transpiler=SEED,
        num_processes=1,
    )
    config = load_config()
    options = {
        key: config[key]
        for key in (
            "basis_gates",
            "coupling_map",
            "initial_layout",
            "optimization_level",
            "seed_transpiler",
        )
    }
    scored = transpile(native, **options, num_processes=1)
    return {
        "metrics": compute_metrics(scored),
        "seconds": round(time.perf_counter() - started, 3),
    }


def main():
    started = time.perf_counter()
    multipliers = sorted({pow(BASE, 1 << j, MODULUS) for j in range(14)})
    tables = {d: permutation_table(d, MODULUS, WIDTH) for d in multipliers}

    selected = {}
    for d in multipliers:
        best = [(mask, mask, target) for mask, target in _short_predicates(tables[d], False)]
        selected[str(d)] = best
        verify(best, tables[d])

    # Baseline whole circuit.
    baseline = score(solution.build_circuit())
    print("baseline", baseline["metrics"], flush=True)

    rng = random.Random(20261111)
    configs = [(list(range(WIDTH)), 0)]
    for k in range(95):
        perm = list(range(WIDTH))
        rng.shuffle(perm)
        configs.append((perm, 0 if k < 47 else rng.randrange(128)))

    fingerprints = set()
    checkpoints = {0, 7, 15, 31, 47, 63, 95}
    rows = [{"name": "baseline", "metrics": baseline["metrics"]}]

    for index, (perm, flip) in enumerate(configs):
        for d in multipliers:
            table = tables[d]
            for inverse, short in itertools.product((False, True), repeat=2):
                ops = simplify(network(d, perm, flip, inverse, short))
                verify(ops, table)
                fingerprint = hashlib.sha256(repr(ops).encode()).hexdigest()
                if fingerprint in fingerprints:
                    continue
                fingerprints.add(fingerprint)
                if cost(ops) < cost(selected[str(d)]):
                    selected[str(d)] = ops
        if index in checkpoints:
            original = solution.build_controlled_multiplier
            solution.build_controlled_multiplier = make_builder(selected)
            try:
                row = {
                    "name": f"prefix_{index + 1}",
                    **score(solution.build_circuit()),
                }
            finally:
                solution.build_controlled_multiplier = original
            rows.append(row)
            print(row["name"], row["metrics"], flush=True)

    best = min(rows, key=lambda r: r["metrics"]["two_qubit_gates"])
    chosen_name = best["name"]
    # Rebuild the chosen selection by replaying the same deterministic search.
    solution.build_controlled_multiplier = make_builder(selected)
    try:
        final_metrics = score(solution.build_circuit())
    finally:
        pass

    output = {
        "modulus": MODULUS,
        "base": BASE,
        "multipliers": multipliers,
        "baseline": baseline["metrics"],
        "rows": rows,
        "best_checkpoint": chosen_name,
        "best_metrics": best["metrics"],
        "final_selection_metrics": final_metrics["metrics"],
        "search_seconds": round(time.perf_counter() - started, 1),
        "candidate": {
            str(d): [[int(m), int(v), int(t)] for m, v, t in ops]
            for d, ops in selected.items()
        },
    }
    Path(__file__).with_name("search.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
