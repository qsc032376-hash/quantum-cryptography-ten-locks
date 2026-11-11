"""Extend the affine override to the next two Tier 10 blocks (A8, g1)."""
import json
import random
import sys
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import candidate_base as cb  # noqa: E402
from qiskit.circuit.library import MCXGate  # noqa: E402

from submissions.team3.tier08.modular import permutation_table  # noqa: E402
from submissions.team3.tier10 import global_synthesis, shared_control, solution  # noqa: E402
from submissions.team3.tier10.synthesis import _short_predicates  # noqa: E402
from tools.check_submission import compute_metrics, load_config  # noqa: E402

BASIS = ["rz", "sx", "x", "cx"]
WIDTH = 7


def block_cost(ops):
    total = 0
    for (mask, val), run in __import__("itertools").groupby(ops, lambda o: o[:2]):
        targets = 0
        for _, _, target in run:
            targets ^= 1 << target
        if not targets:
            continue
        controls = 1 + mask.bit_count()
        total += (1, 6, 14)[controls - 1] if controls <= 3 else 8 * controls - 12
        total += 2 * (targets.bit_count() - 1)
    return total


def ideal(table):
    matrix = np.zeros((1 << 8,) * 2, dtype=complex)
    for control in (0, 1):
        for x in range(128):
            y = table[x] if control else x
            matrix[control + (y << 1), control + (x << 1)] = 1
    return matrix


def screen(d, configs):
    current = global_synthesis._operations()[str(d)]
    best = {"cost": block_cost(current), "cnots": [], "flip": 0, "short": False, "inverse": False}
    table = permutation_table(d, 83, WIDTH)
    for cnots, flip in configs:
        conjugated, _ = cb.conjugate(table, cnots, flip)
        for inverse, short in ((False, False), (False, True), (True, False), (True, True)):
            source = cb.invert_map(conjugated) if inverse else conjugated
            try:
                ops = _short_predicates(source, short)
            except Exception:
                continue
            if inverse:
                ops = ops[::-1]
            triples = [(m, m, t) for m, t in ops]
            proxy = block_cost(triples) + 2 * len(cnots)
            if proxy < best["cost"]:
                circuit = cb.custom_block(triples, cnots, flip)
                if np.max(np.abs(Operator(circuit).data - ideal(table))) < 1e-9:
                    best = {"cost": proxy, "cnots": list(cnots), "flip": flip,
                            "short": short, "inverse": inverse}
    return best


def score(circuit):
    sim = AerSimulator(method="statevector", max_parallel_threads=2)
    native = transpile(circuit, sim, basis_gates=BASIS, optimization_level=1,
                       seed_transpiler=12345, num_processes=1)
    cfg = load_config()
    opts = {k: cfg[k] for k in ("basis_gates", "coupling_map", "initial_layout",
                                "optimization_level", "seed_transpiler")}
    return compute_metrics(transpile(native, **opts, num_processes=1))


def main():
    p = solution._public_parameters()
    targets = {
        "A8": pow(p["A"], 8, p["p"]),
        "g1": pow(p["g"], 1, p["p"]),
    }
    base_config = json.loads((HERE / "affine_candidate_base.json").read_text())
    cb.CONFIG = dict(base_config)

    rng = random.Random(20261112)
    configs = [([], 0)]
    for _ in range(300):
        length = rng.randrange(1, 5)
        cnots = []
        for _ in range(length):
            control = rng.randrange(WIDTH)
            target = rng.randrange(WIDTH - 1)
            if target >= control:
                target += 1
            cnots.append((control, target))
        configs.append((cnots, 0 if rng.random() < 0.5 else rng.randrange(1, 128)))

    baseline = score(solution.build_circuit())
    print("baseline38k", baseline, flush=True)
    for label, d in targets.items():
        best = screen(d, configs)
        print(label, d, best, flush=True)
        if best["cost"] < block_cost(global_synthesis._operations()[str(d)]):
            cb.CONFIG[str(d)] = {
                "cnots": best["cnots"], "flip": best["flip"],
                "short": best["short"], "inverse": best["inverse"],
            }

    original = shared_control.fanout_multiplier
    shared_control.fanout_multiplier = cb.patched_fanout(original)
    metrics = score(solution.build_circuit())
    print("combined", metrics, flush=True)
    (HERE / "affine_candidate_v2.json").write_text(json.dumps(cb.CONFIG, indent=2) + "\n")


if __name__ == "__main__":
    main()
