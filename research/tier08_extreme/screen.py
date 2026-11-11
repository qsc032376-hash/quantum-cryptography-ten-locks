"""Bounded official-basis compilation screens (not execution validation)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from qiskit import transpile
from submissions.team3.tier08 import solution, modular
from tools.check_submission import compute_metrics, load_config
from research.tier08_extreme.emitter import build_from_operations, symbolic


def score(circuit):
    start = time.perf_counter()
    native = transpile(circuit, basis_gates=solution.BASIS_GATES,
                       optimization_level=1, seed_transpiler=12345, num_processes=1)
    native_seconds = time.perf_counter() - start
    cfg = load_config()
    scored = transpile(native, **{k: cfg[k] for k in
                       ('basis_gates', 'coupling_map', 'initial_layout', 'optimization_level', 'seed_transpiler')},
                       num_processes=1)
    return {'metrics': compute_metrics(scored), 'solve_transpile_seconds': native_seconds,
            'scoring_transpile_seconds': time.perf_counter()-start-native_seconds,
            'compile_seconds': time.perf_counter()-start}


def build(selected, **emission):
    def multiplier(d, p, w):
        operations = selected[str(d)]
        assert symbolic(operations, w) == modular.permutation_table(d, p, w)
        return build_from_operations(operations, w, **emission)
    with patch.object(solution, 'build_controlled_multiplier', multiplier):
        return solution.build_circuit()


def baseline():
    original = getattr(modular, '_validated_hybrid_multiplier', modular.build_controlled_multiplier)
    blocks = {str(d): score(original(d, 35, 6)) for d in (2, 4, 11, 16)}
    with patch.object(solution, 'build_controlled_multiplier', original):
        circuit = solution.build_circuit()
    return {'kind': 'baseline', 'source': 'c4455782ea9388d5897fc27270f42dd3786ed35d',
            'blocks': blocks, 'whole': score(circuit),
            'qft': score(solution._inverse_qft_core(12)),
            'powers': solution.count_modular_powers(circuit)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--selected')
    parser.add_argument('--mode', default='dirty', choices=('dirty', 'native'))
    parser.add_argument('--pivot', default='first', choices=('first', 'last'))
    parser.add_argument('--allocation', default='work_first', choices=('work_first', 'external_first'))
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.baseline:
        result = baseline()
    else:
        selected = json.loads(Path(args.selected).read_text())
        if 'selected' in selected:
            selected = selected['selected']
        emission = {'mode': args.mode, 'pivot': args.pivot, 'allocation': args.allocation}
        circuit = build(selected, **emission)
        result = {'kind': 'whole_candidate', 'source_operations_sha256': hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest(),
                  'emission': emission, 'whole': score(circuit),
                  'powers': solution.count_modular_powers(circuit)}
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result.get('whole', result)))


if __name__ == '__main__':
    main()
