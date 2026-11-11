"""Synthetic reflection benchmark. Run from repository root with python -m."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import psutil
import qiskit
from qiskit import QuantumCircuit, transpile, synthesis
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from submissions.team3.tier06 import oracle

METHODS = ("n_clean_m15", "1_clean_kg24", "2_clean_kg24", "1_dirty_kg24", "noaux_v24")
BASIS = ["rz", "sx", "x", "cx"]
HERE = Path(__file__).resolve().parent


def reflection(n, method):
    mcx = getattr(synthesis, "synth_mcx_" + method)(n - 1)
    circuit = QuantumCircuit(mcx.num_qubits)
    circuit.h(range(n))
    circuit.x(range(n))
    circuit.h(n - 1)
    circuit.compose(mcx, inplace=True)
    circuit.h(n - 1)
    circuit.x(range(n))
    circuit.h(range(n))
    circuit.global_phase = np.pi
    return circuit


def compile_block(circuit):
    for level in (2, 1):
        circuit = transpile(circuit, basis_gates=BASIS, optimization_level=level,
                            seed_transpiler=12345, num_processes=1)
    return circuit


def metrics(circuit):
    return dict(cx=circuit.count_ops().get("cx", 0), depth=circuit.depth(),
                gates=circuit.size(), active=len({q for op in circuit.data for q in op.qubits}))


def exact_error(method):
    n = 5
    dim = 1 << n
    op = Operator(compile_block(reflection(n, method))).data
    ref = np.kron(np.eye(len(op) // dim), 2 * np.ones((dim, dim)) / dim - np.eye(dim))
    cols = len(op) if "dirty" in method else dim
    return float(np.max(np.abs(op[:, :cols] - ref[:, :cols])))


def trial(method, seed):
    n = 14
    size = 1 << n
    circ = compile_block(reflection(n, method))
    rng = np.random.default_rng(seed)
    initial = rng.normal(size=size) + 1j * rng.normal(size=size)
    initial /= np.linalg.norm(initial)
    padded = np.zeros(1 << circ.num_qubits, dtype=complex)
    padded[:size] = initial
    test = QuantumCircuit(circ.num_qubits)
    test.set_statevector(padded)
    test.compose(circ, inplace=True)
    test.save_statevector()
    backend = AerSimulator(method="statevector", max_parallel_threads=2)
    start = perf_counter()
    result = backend.run(test, shots=1, seed_simulator=seed).result()
    elapsed = perf_counter() - start
    actual = np.asarray(result.get_statevector())
    padded[:size] = 2 * initial.mean() - initial
    overlap = np.vdot(padded, actual)
    assert abs(overlap) > 1 - 1e-9
    err = float(np.max(np.abs(actual - padded * (overlap / abs(overlap)))))
    assert result.success and err < 1e-9
    return dict(seed=seed, method=method, seconds=elapsed, max_error=err,
                peak_process_MiB=psutil.Process().memory_info().peak_wset / 2**20)


def main():
    rows = {}
    for method in METHODS:
        error = exact_error(method)
        assert error < 1e-9
        rows[method] = dict(metrics(compile_block(reflection(14, method))), operator_error=error)
    baseline = metrics(compile_block(oracle.build_diffuser()))
    assert all(rows[METHODS[0]][k] == v for k, v in baseline.items())
    components = {name: metrics(compile_block(circuit)) for name, circuit in (
        ("mask", oracle._build_mask(oracle.MAIN_QUBITS)),
        ("phase_synthetic_byte_0", oracle.build_phase_oracle(0)),
        ("bit_synthetic_byte_0", oracle.build_bit_oracle(0)),
        ("v6_diffuser", oracle.build_diffuser()))}
    winner = min(METHODS, key=lambda m: (rows[m]["cx"], rows[m]["depth"], rows[m]["gates"]))
    trials = []
    for seed in range(100, 105):
        for method in dict.fromkeys((METHODS[0], winner)):
            raw = subprocess.check_output([sys.executable, "-m", "research.tier06_extreme.profile",
                                           "--trial", method, str(seed)])
            trials.append(json.loads(raw))
    data = dict(qiskit=qiskit.__version__, components=components, reflections=rows,
                selected=winner, synthetic_trials=trials)
    (HERE / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({k:v for k,v in data.items() if k != "synthetic_trials"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", nargs=2)
    args = parser.parse_args()
    if args.trial:
        print(json.dumps(trial(args.trial[0], int(args.trial[1]))))
    else:
        main()
