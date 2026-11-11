"""Paired synthetic Grover iterations with a public three-wire predicate."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np
import psutil
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from research.tier06_extreme.profile import compile_block, metrics, reflection

METHODS = ("n_clean_m15", "2_clean_kg24")
PREDICATES = ("scratch", "direct")


def blocks(n, method, predicate, rounds, *, prepare=False, measure=False):
    diffuser = reflection(n, method)
    width = n + 8 if prepare else max(n + 1, diffuser.num_qubits)
    circuit = QuantumCircuit(width, n if measure else 0)
    if prepare:
        circuit.h(range(n))
    for _ in range(rounds):
        if predicate == "scratch":
            circuit.cx(1, n)
            circuit.cx(3, n)
            circuit.cz(0, n)
            circuit.cx(3, n)
            circuit.cx(1, n)
        else:
            circuit.cz(0, 1)
            circuit.cz(0, 3)
        circuit.compose(diffuser, range(diffuser.num_qubits), inplace=True)
    if measure:
        circuit.measure(range(n), range(n))
    return circuit


def marked(x):
    return (x & 1) & ((x >> 1) ^ (x >> 3))


def exact(n, method, predicate):
    circuit = compile_block(blocks(n, method, predicate, 2))
    dim = 1 << n
    signs = 1 - 2 * marked(np.arange(dim))
    step = (2 * np.ones((dim, dim)) / dim - np.eye(dim)) * signs
    wanted = step @ step
    columns = Operator(circuit).data[:, :dim]
    return float(max(abs(columns[:dim] - wanted).max(), abs(columns[dim:]).max()))


def trial(method, predicate, seed):
    n, rounds, shots = 14, 2, 2048
    start = perf_counter()
    circuit = compile_block(blocks(n, method, predicate, rounds, prepare=True, measure=True))
    compiled = perf_counter() - start
    backend = AerSimulator(method="statevector", enable_truncation=False, max_parallel_threads=2)
    start = perf_counter()
    exp = backend.run(circuit, shots=shots, seed_simulator=seed).result().results[0]
    elapsed = perf_counter() - start
    assert exp.success and exp.seed_simulator == seed
    hits = sum(count for hexword, count in exp.data.counts.items() if marked(int(hexword, 16)))
    # The marked fraction is 1/4. After two rounds sin^2(5*pi/6)=1/4.
    z = (hits - shots / 4) / np.sqrt(shots * 0.25 * 0.75)
    return dict(method=method, predicate=predicate, seed=exp.seed_simulator,
                shots=shots, rounds=rounds, fraction=hits/shots, z=float(z),
                passed=bool(abs(z) < 5), compile_s=compiled, aer_s=elapsed,
                peak_working_set_MiB=psutil.Process().memory_info().peak_wset/2**20)


def main():
    rows = []
    for method in METHODS:
        for predicate in PREDICATES:
            error = exact(5, method, predicate)
            assert error < 1e-10
            circuit = compile_block(blocks(14, method, predicate, 2, prepare=True, measure=True))
            rows.append(dict(method=method, predicate=predicate, operator_error=error,
                             **metrics(circuit)))
    best = min(rows, key=lambda row: (row["cx"], row["depth"], row["gates"]))
    shallowest = min(rows, key=lambda row: row["depth"])
    pairs = list(dict.fromkeys([(METHODS[0], PREDICATES[0]),
                                (best["method"], best["predicate"]),
                                (shallowest["method"], shallowest["predicate"])]))
    samples = []
    for seed in range(6600, 6605):
        for method, predicate in pairs[::1 if seed % 2 == 0 else -1]:
            raw = subprocess.check_output([sys.executable, "-m", "research.tier06_extreme_v2.study",
                                           "--trial", method, predicate, str(seed)], timeout=120)
            samples.append(json.loads(raw))
    data = dict(component_combinations=rows, synthetic_runs=samples)
    Path(__file__).with_name("results.json").write_text(json.dumps(data, indent=2) + "\n")
    print(rows)
    print("samples passed", sum(row["passed"] for row in samples), "/", len(samples))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", nargs=3)
    args = parser.parse_args()
    if args.trial:
        method, predicate, seed = args.trial
        print(json.dumps(trial(method, predicate, int(seed))))
    else:
        main()
