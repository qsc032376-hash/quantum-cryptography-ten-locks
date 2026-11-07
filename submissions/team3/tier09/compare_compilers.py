"""Static public-parameter comparison; no simulation or order finding.

Both compiler implementations are reused unchanged. Gate statistics are
weighted over the fourteen public repeated-square multipliers. A cached
compilation is reused whenever the public multiplier repeats. No permutation
cycle is traversed here and no cycle length is used as a period.
"""

from collections import Counter
import json
from pathlib import Path

from submissions.team3.tier08 import modular as baseline
from submissions.team3.tier09 import modular as current


MODULUS = 77
BASE = 2
WORK_BITS = 7
PHASE_BITS = 14
REPORT_PATH = Path(__file__).with_name("compilation_comparison.json")


def _baseline_stats(multiplier):
    circuit = baseline.build_controlled_multiplier(multiplier, MODULUS, WORK_BITS)
    return {
        "mcx7_blocks": sum(
            instruction.operation.label == "exact_mcx7_dirty"
            for instruction in circuit.data
        ),
        "normalizing_x_count": int(circuit.count_ops().get("x", 0)),
    }


def _static_memory(layout, qubits):
    byte_count = 16 * (1 << qubits)
    return {
        "layout": layout,
        "qubits": qubits,
        "raw_double_precision_statevector_bytes": byte_count,
        "raw_statevector_mib": byte_count // (1 << 20),
        "includes_simulator_or_compiler_overhead": False,
        "benchmark_executed": False,
    }


def comparison_report():
    cache = {}
    new_native_gates = new_normalizing_x = old_mcx7 = old_normalizing_x = 0
    controls = Counter()
    for j in range(PHASE_BITS):
        multiplier = pow(BASE, 1 << j, MODULUS)
        if multiplier not in cache:
            cache[multiplier] = (
                current.public_compilation_stats(multiplier, MODULUS, WORK_BITS),
                _baseline_stats(multiplier),
            )
        new_stats, old_stats = cache[multiplier]
        new_native_gates += new_stats["gate_count"]
        new_normalizing_x += new_stats["normalizing_x_count"]
        controls.update(new_stats["control_count_histogram"])
        old_mcx7 += old_stats["mcx7_blocks"]
        old_normalizing_x += old_stats["normalizing_x_count"]

    if sum(controls.values()) != new_native_gates:
        raise RuntimeError("The public control histogram does not match its gate count")

    # Standard 14-bit IQFT: 91 CP gates at 2 CX each, plus 7 SWAPs at 3 CX each.
    iqft_cx = 2 * (PHASE_BITS * (PHASE_BITS - 1) // 2) + 3 * (PHASE_BITS // 2)
    return {
        "comparison_kind": "public static compiler counts, not an official measured score",
        "parameters": {
            "modulus": MODULUS,
            "base": BASE,
            "work_bits": WORK_BITS,
            "phase_bits": PHASE_BITS,
            "controlled_multiplier_blocks": PHASE_BITS,
        },
        "cached_by_public_multiplier": True,
        "quantum_circuits_executed": 0,
        "hidden_data_read": False,
        "order_or_factors_computed": False,
        "current_compiler": {
            "native_controlled_x_blocks": new_native_gates,
            "control_count_histogram": {
                str(count): frequency for count, frequency in sorted(controls.items())
            },
            "histogram_includes_external_control": True,
            "normalizing_x_count": new_normalizing_x,
            "cx_estimate": None,
            "basis_gate_score_source": "Use the real validator; no current-compiler CX estimate is made here",
        },
        "baseline_gray_path_compiler": {
            "mcx7_blocks": old_mcx7,
            "normalizing_x_count": old_normalizing_x,
            "assumed_cx_upper_bound_per_exact_mcx7_dirty": 50,
            "standard_iqft_cx_contribution": iqft_cx,
            "static_cx_upper_bound_including_iqft": 50 * old_mcx7 + iqft_cx,
            "cx_bound_formula": "50 * mcx7_blocks + 203",
            "actual_quantum_circuit_executed": False,
            "official_transpiled_score_measured": False,
            "cross_block_optimizations_included": False,
        },
        "native_block_comparison": {
            "fewer_current_controlled_x_blocks": old_mcx7 - new_native_gates,
            "fraction_fewer": (old_mcx7 - new_native_gates) / old_mcx7,
            "is_basis_gate_or_runtime_comparison": False,
            "note": "Current blocks have mixed control counts; baseline blocks all have seven controls",
        },
        "static_statevector_memory_comparison": [
            _static_memory("14 counting + 7 work; no dedicated ancilla", 21),
            _static_memory("Same layout plus 3 clean ancillas", 24),
            _static_memory("Arithmetic route with 7-bit output buffer; excludes carry/comparison ancillas", 28),
        ],
        "resource_comparison_limit": "Raw statevector sizes only; this static comparison runs no benchmarks. Chosen 21-qubit real measurements are in quantum_validation.json. Arithmetic may require more qubits",
    }


def main():
    report = comparison_report()
    encoded = json.dumps(report, indent=2) + "\n"
    REPORT_PATH.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
