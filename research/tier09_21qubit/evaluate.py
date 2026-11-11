"""Bounded Tier 9 21-qubit vs 22-qubit resource evaluation.

Builds the public controlled-modular-multiplication circuit with and without the
clean synthesis workspace, compiles both under the official scoring basis, and
prints only aggregate metrics. No key, order, factor or plaintext is read.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit, transpile

from submissions.team3.tier07.qpe import build_inverse_qft
from submissions.team3.tier09.shared_controls import build_controlled_multiplier

BASE = 2
MODULUS = 77
PHASE_BITS = 14
WORK_BITS = 7
OFFICIAL = {
    "basis_gates": ["rz", "sx", "x", "cx"],
    "optimization_level": 1,
    "seed_transpiler": 12345,
}


def build_21(*, modulus=MODULUS, base=BASE, phase_bits=PHASE_BITS, work_bits=WORK_BITS):
    """Controlled modular exponentiation with no clean synthesis workspace."""
    circuit = QuantumCircuit(phase_bits + work_bits, phase_bits, name="tier09_21q")
    work = list(range(phase_bits, phase_bits + work_bits))
    circuit.x(work[0])
    circuit.h(range(phase_bits))
    cache = {}
    for control in range(phase_bits):
        multiplier = pow(base, 1 << control, modulus)
        if multiplier not in cache:
            cache[multiplier] = build_controlled_multiplier(
                multiplier, modulus, work_bits
            ).to_gate()
        powered = cache[multiplier].copy(
            name=f"tier09_controlled_modmul_power_{1 << control}"
        )
        circuit.append(powered, [control, *work])
    circuit.append(build_inverse_qft(phase_bits).to_gate(), range(phase_bits))
    circuit.measure(range(phase_bits), range(phase_bits))
    return circuit


def metrics(circuit):
    from tools.check_submission import compute_metrics

    compiled = transpile(circuit, **OFFICIAL)
    return compute_metrics(compiled)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=str, default="")
    args = parser.parse_args()

    from submissions.team3.tier09.solution import build_circuit as build_22

    results = {}
    for name, builder in (("21q", build_21), ("22q", build_22)):
        started = time.perf_counter()
        circuit = builder()
        metrics_result = metrics(circuit)
        results[name] = {
            "metrics": metrics_result,
            "qubits": circuit.num_qubits,
            "compile_seconds": round(time.perf_counter() - started, 3),
        }
        print(name, json.dumps(results[name], sort_keys=True), flush=True)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2, sort_keys=True)


if __name__ == "__main__":
    sys.exit(main())
