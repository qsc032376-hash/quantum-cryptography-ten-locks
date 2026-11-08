"""Deterministic small-circuit evaluation; no Aer or protected input access.

python -m research.circuit_optimizer.run_benchmarks --out PATH
"""

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import qiskit
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from .gf2_synthesis import optimize
from .commutation_rules import cancel_inverses
from .qft_relabeling import inverse_qft, absorb_input_reversal, absorb_output_reversal
from .mcx_benchmark import survey, corrected_relative_toffoli
from .metrics import compile_metrics, metrics, BASIS


def pair(name, original, candidate, contract="exact unitary", right_permutation=None):
    before_compiled, before = compile_metrics(original)
    after_compiled, after = compile_metrics(candidate)
    reference = Operator(before_compiled).data
    if right_permutation is not None:
        reference = reference @ Operator(right_permutation).data
    error = float(np.max(np.abs(Operator(after_compiled).data - reference)))
    if error > 1e-10:
        raise AssertionError(f"Compiled equivalence failed: {name}")
    return {"case": name, "contract": contract, "max_amplitude_error": error,
            "logical_before": metrics(original), "logical_after": metrics(candidate),
            "before": before, "after": after}


def run():
    records = []
    rng = np.random.default_rng(144)
    linear = QuantumCircuit(6, global_phase=0.13)
    for _ in range(40):
        c, t = rng.choice(6, 2, replace=False)
        linear.cx(int(c), int(t))
    candidate, accepted = optimize(linear)
    records.append({**pair("gf2_seed144_6w_40cx", linear, candidate), "guard_accepted": accepted})

    commute = QuantumCircuit(4)
    commute.cx(0, 1); commute.rz(0.37, 0); commute.cx(0, 2); commute.x(3)
    commute.cx(0, 1); commute.h(3); commute.h(3)
    commute.p(0.23, 2); commute.p(-0.23, 2)
    candidate, removed = cancel_inverses(commute)
    records.append({**pair("commutable_inverse_window", commute, candidate), "removed": removed})

    prefix = QuantumCircuit(5)
    prefix.h(range(3)); prefix.ry(0.41, 3); prefix.h(4)
    for q in range(3):
        prefix.cp(0.23 * (2 ** q), q, 3)
    prefix.ccx(0, 3, 2)
    prefix.cx(2, 4)
    transform = QuantumCircuit(5)
    transform.compose(inverse_qft(3), range(3), inplace=True)
    original = prefix.compose(transform)
    plan = absorb_input_reversal(prefix, transform, (0, 1, 2))
    reversal = QuantumCircuit(5); reversal.swap(0, 2)
    records.append(pair("input_reversal_3count_2work", original, plan.circuit,
                        "candidate = original * R; equal on R-invariant input", reversal))

    original = inverse_qft(3).inverse()
    core, mapping = absorb_output_reversal(original, (0, 1, 2), {0: 0, 1: 1, 2: 2})
    before_compiled, before = compile_metrics(original)
    after_compiled, after = compile_metrics(core)
    reversal = QuantumCircuit(3); reversal.swap(0, 2)
    error = float(np.max(np.abs(Operator(before_compiled).data -
                               Operator(reversal).data @ Operator(after_compiled).data)))
    if error > 1e-10:
        raise AssertionError("Output permutation equivalence failed")
    records.append({"case": "output_reversal_3w", "contract": "original = R * core; remap readout",
                    "measurement_map": mapping, "max_amplitude_error": error,
                    "logical_before": metrics(original), "logical_after": metrics(core),
                    "before": before, "after": after})

    reference = QuantumCircuit(3); reference.ccx(0, 1, 2)
    records.append(pair("corrected_relative_toffoli", reference, corrected_relative_toffoli()))
    return {"research_only": True, "official_checker_run": False,
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "qiskit": qiskit.__version__, "numpy": np.__version__},
            "settings": {"basis_gates": BASIS, "coupling_map": None, "initial_layout": None,
                         "optimization_level": 1, "seed_transpiler": 12345},
            "pairs": records, "mcx": survey()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for row in result["pairs"]:
        print(row["case"], row["before"], "->", row["after"])
    for row in result["mcx"]:
        print("MCX", row)


if __name__ == "__main__":
    main()
