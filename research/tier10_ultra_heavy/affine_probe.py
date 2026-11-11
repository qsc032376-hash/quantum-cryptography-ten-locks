"""Bounded affine-coordinate conjugation probe for Tier 10 power blocks.

Only public modular permutations are used.  No key, exponent or plaintext is read.
"""
import itertools
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submissions.team3.tier08.modular import permutation_table
from submissions.team3.tier10 import global_synthesis, shared_control, solution
from submissions.team3.tier10.synthesis import _short_predicates
from tools.check_submission import compute_metrics, load_config

BASIS = ["rz", "sx", "x", "cx"]
SEED = 12345
MODULUS = 83
WIDTH = 7


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
        total += (1, 6, 14)[controls - 1] if controls <= 3 else 8 * controls - 12
        total += 2 * (targets.bit_count() - 1)
    return total


def apply_cnots(value, cnots):
    for control, target in cnots:
        if value >> control & 1:
            value ^= 1 << target
    return value


def affine_map(perm, flip, cnots):
    return [apply_cnots(x, cnots) ^ flip for x in range(1 << WIDTH)]


def inverse_map(perm, flip, cnots):
    inverse = [0] * (1 << WIDTH)
    for x, y in enumerate(perm):
        inverse[y] = x
    return inverse


def conjugate(table, cnots, flip):
    forward = affine_map(None, flip, cnots)
    inverse = inverse_map(forward, None, [])
    mapped = [0] * len(table)
    for x, y in enumerate(table):
        mapped[forward[x]] = forward[y]
    return mapped


def custom_block(ops, cnots, flip, pivot_last=False):
    circuit = QuantumCircuit(WIDTH + 1)
    for control, target in cnots:
        circuit.cx(control + 1, target + 1)
    for bit in range(WIDTH):
        if flip >> bit & 1:
            circuit.x(bit + 1)
    inner = global_synthesis.emit(ops, WIDTH, pivot_last)
    circuit.compose(inner, range(WIDTH + 1), inplace=True)
    for bit in range(WIDTH):
        if flip >> bit & 1:
            circuit.x(bit + 1)
    for control, target in reversed(cnots):
        circuit.cx(control + 1, target + 1)
    return circuit


def ideal_operator(table):
    matrix = np.zeros((1 << (WIDTH + 1),) * 2, dtype=complex)
    for control in (0, 1):
        for x in range(1 << WIDTH):
            y = table[x] if control else x
            matrix[control + (y << 1), control + (x << 1)] = 1
    return matrix


def verify(circuit, table):
    matrix = Operator(circuit).data
    reference = ideal_operator(table)
    return float(np.max(np.abs(matrix - reference)))


def score(circuit):
    simulator = AerSimulator(method="statevector", max_parallel_threads=2)
    started = time.perf_counter()
    native = transpile(
        circuit, simulator, basis_gates=BASIS, optimization_level=1,
        seed_transpiler=SEED, num_processes=1,
    )
    config = load_config()
    options = {key: config[key] for key in (
        "basis_gates", "coupling_map", "initial_layout",
        "optimization_level", "seed_transpiler")}
    metrics = compute_metrics(transpile(native, **options, num_processes=1))
    return metrics, round(time.perf_counter() - started, 1)


def screen(target_d, configs, table):
    current = global_synthesis._operations()[str(target_d)]
    best = {"cost": cost(current), "cnots": [], "flip": 0, "short": False, "inverse": False}
    results = []
    for cnots, flip in configs:
        conjugated = conjugate(table, cnots, flip)
        for inverse, short in itertools.product((False, True), repeat=2):
            source = conjugated
            if inverse:
                source = inverse_map(source, None, [])
            try:
                ops = _short_predicates(source, short)
            except Exception:
                continue
            if inverse:
                ops = ops[::-1]
            triples = [(m, m, t) for m, t in ops]
            proxy = cost(triples) + 2 * len(cnots)
            if proxy < best["cost"]:
                circuit = custom_block(triples, cnots, flip)
                error = verify(circuit, table)
                if error < 1e-9:
                    best = {"cost": proxy, "cnots": list(cnots), "flip": flip,
                            "short": short, "inverse": inverse, "error": error}
        results.append({"cnots": list(cnots), "flip": flip, "best_cost": best["cost"]})
    return best, results


def main():
    parameters = solution._public_parameters()
    p, g, A = parameters["p"], parameters["g"], parameters["A"]
    d_a = pow(A, 32, p)
    d_g = pow(g, 32, p)
    tables = {d: permutation_table(d, p, WIDTH) for d in (d_a, d_g)}

    rng = random.Random(20261111)
    configs = [([], 0)]
    for length in range(1, 5):
        for _ in range(40):
            cnots = []
            for _ in range(length):
                control = rng.randrange(WIDTH)
                target = rng.randrange(WIDTH - 1)
                if target >= control:
                    target += 1
                cnots.append((control, target))
            configs.append((cnots, 0))
            configs.append((cnots, rng.randrange(1, 128)))

    baseline_metrics = score(solution.build_circuit())[0]
    print("baseline", baseline_metrics, flush=True)

    best_by_d = {}
    for d in (d_a, d_g):
        best, _ = screen(d, configs, tables[d])
        best_by_d[d] = best
        print("screen", d, best, flush=True)

    for label, targets in (("A32", (d_a,)), ("g32", (d_g,)), ("both", (d_a, d_g))):
        original = shared_control.fanout_multiplier

        def patched(d, modulus, work_bits):
            if d in targets:
                info = best_by_d[d]
                conjugated = conjugate(tables[d], info["cnots"], info["flip"])
                source = conjugated
                if info["inverse"]:
                    source = inverse_map(source, None, [])
                ops = _short_predicates(source, info["short"])
                if info["inverse"]:
                    ops = ops[::-1]
                return custom_block([(m, m, t) for m, t in ops], info["cnots"], info["flip"])
            return original(d, modulus, work_bits)

        shared_control.fanout_multiplier = patched
        try:
            metrics, seconds = score(solution.build_circuit())
        finally:
            shared_control.fanout_multiplier = original
        print("whole", label, metrics, seconds, flush=True)


if __name__ == "__main__":
    main()
