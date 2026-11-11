"""Ten bounded isolated exact-MCX comparisons; no Tier 8 execution.

Extra local wires are dirty, never assumed zero. Complete operator tests are
required before recommending an alternative that reduces isolated CX count.
These local template costs are diagnostic, not complete scored-circuit costs.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import MCXGate
from qiskit.quantum_info import Operator
from qiskit.synthesis import (
    synth_mcx_n_dirty_m15, synth_mcx_n_dirty_i15,
    synth_mcx_1_dirty_kg24, synth_mcx_2_dirty_kg24,
    synth_mcx_noaux_v24,
)
from tools.check_submission import compute_metrics, load_config


def native(n):
    circuit = QuantumCircuit(n + 1)
    circuit.append(MCXGate(n), list(range(n + 1)))
    return circuit


def operator_error(circuit, controls):
    """All complex columns, including all dirty assignments; no phase fit."""
    actual = Operator(circuit).data
    expected = np.zeros_like(actual)
    mask = (1 << controls) - 1
    for x in range(len(actual)):
        y = x ^ (1 << controls) if x & mask == mask else x
        expected[y, x] = 1
    difference = float(np.max(np.abs(actual - expected)))
    return {"dimension": len(actual), "maximum_complex_error": difference,
            "all_dirty_assignments": True, "global_phase_fitted": False,
            "pass": difference < 1e-11}


def main():
    start = time.perf_counter()
    config = load_config()
    options = {k: config[k] for k in (
        'basis_gates', 'coupling_map', 'initial_layout',
        'optimization_level', 'seed_transpiler')}
    factories = {
        'm15_dirty': synth_mcx_n_dirty_m15,
        'iten_dirty': lambda n: synth_mcx_n_dirty_i15(n, relative_phase=False, action_only=False),
        'kg24_one_dirty': synth_mcx_1_dirty_kg24,
        'kg24_two_dirty': synth_mcx_2_dirty_kg24,
        'v24_noaux': synth_mcx_noaux_v24,
        'native_mcx': native,
    }
    # Two baseline endpoints, followed by eight representative alternatives.
    trials = [('m15_dirty', 4), ('m15_dirty', 6),
              ('iten_dirty', 4), ('iten_dirty', 6),
              ('kg24_one_dirty', 4), ('kg24_one_dirty', 6),
              ('kg24_two_dirty', 6), ('v24_noaux', 4),
              ('v24_noaux', 6), ('native_mcx', 6)]
    results = []
    baseline_cost = {}
    for family, controls in trials:
        before = time.perf_counter()
        circuit = factories[family](controls)
        # Mirrors Tier 8's native basis compilation followed by scoring.
        native_compiled = transpile(circuit, **options, num_processes=1)
        scored = transpile(native_compiled, **options, num_processes=1)
        metrics = compute_metrics(scored)
        item = {"family": family, "controls": controls,
                "local_qubits": circuit.num_qubits,
                "dirty_ancillas": circuit.num_qubits-controls-1,
                "metrics": metrics, "compile_seconds": time.perf_counter()-before}
        if family == 'm15_dirty':
            baseline_cost[controls] = metrics['two_qubit_gates']
            item['role'] = 'existing_exact_template_baseline'
        else:
            item['cx_change_against_m15'] = metrics['two_qubit_gates']-baseline_cost[controls]
            item['role'] = 'alternative'
            if item['cx_change_against_m15'] < 0:
                item['operator_verification'] = operator_error(circuit, controls)
                item['recommendation'] = ('candidate_for_whole_circuit_screen'
                    if item['operator_verification']['pass'] else 'reject_phase_or_dirty_failure')
            else:
                item['recommendation'] = 'do_not_promote_no_isolated_cx_improvement'
        results.append(item)
        print(family, controls, metrics, flush=True)
    payload = {
        "qiskit": qiskit.__version__, "scoring_options": options,
        "primitive_compilation_budget": 10, "compiled_templates": len(results),
        "existing_small_cases": {"1": "CX; 1 CX", "2": "CCX; 6 CX", "3": "exact Iten; 14 CX"},
        "small_cases_note": "Inherited measured costs from Stage A; not recompiled here.",
        "results": results, "elapsed_seconds": time.perf_counter()-start,
        "scope": "isolated exact templates; not full circuits, no Aer jobs or secret data",
        "borrowed_wire_contract": "All extra wires are dirty. They may be entangled and must be restored.",
        "clean_alternatives_excluded": "Counting wires are not known-zero workspace; no extra logical qubits allowed.",
        "fanout_note": "F; MCX; F^-1 is exact for arbitrary pivot/target states. Pivot choice affects local compiler cancellation; whole-circuit screens decide.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    Path(__file__).with_suffix('.json').write_text(json.dumps(payload, indent=2)+'\n')


if __name__ == '__main__':
    main()
