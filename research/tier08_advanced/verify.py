"""Reproduce bounded Tier 8 anchor-synthesis checks without secret output."""
import importlib.util
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'submissions'))
sys.path.insert(0, str(ROOT))
from team3.tier08 import modular, solution
from tools.check_submission import compute_metrics

source = subprocess.check_output(['git', 'show', '0988ac44d88d08cc12258f2010afaf792dd53e7b:submissions/team3/tier08/modular.py'], cwd=ROOT, text=True)
baseline = importlib.util.module_from_spec(importlib.util.spec_from_loader('baseline_modular', loader=None))
exec(compile(source, 'baseline_modular.py', 'exec'), baseline.__dict__)
BASIS = ['rz', 'sx', 'x', 'cx']


def native(c):
    return transpile(c, basis_gates=BASIS, optimization_level=1, seed_transpiler=12345, num_processes=1)


def classical_execute(c, x):
    for item in c.data:
        q = [c.find_bit(w).index for w in item.qubits]
        if item.operation.name == 'x':
            x ^= 1 << q[0]
        else:
            label = item.operation.label
            controls = 6 if label == 'exact_mcx6_dirty' else int(label.removeprefix('exact_mcx_'))
            assert len(q) >= controls + 1
            if all(x & (1 << i) for i in q[:controls]):
                x ^= 1 << q[controls]
    return x


def run():
    rng = np.random.default_rng(804)
    rows = []
    multipliers = sorted({pow(2, 1 << j, 35) for j in range(12)})
    for multiplier in multipliers:
        old = baseline.build_controlled_multiplier(multiplier, 35)
        new = modular.build_controlled_multiplier(multiplier, 35)
        table = modular.permutation_table(multiplier, 35, 6)
        for x in range(512):
            control = x & 1
            work = (x >> 1) & 63
            expected = (x & ~126) | ((table[work] if control else work) << 1)
            assert classical_execute(old, x) == classical_execute(new, x) == expected
        v = rng.normal(size=512) + 1j*rng.normal(size=512)
        v /= np.linalg.norm(v)
        v0 = Statevector(v).evolve(old).data
        v1 = Statevector(v).evolve(new).data
        err = float(np.max(np.abs(v0-v1)))
        assert err < 1e-10
        a = compute_metrics(native(native(old)))
        b = compute_metrics(native(native(new)))
        rows.append({'multiplier': multiplier, 'basis_branches': 512, 'max_superposition_error': err,
                     'baseline': a, 'candidate': b,
                     'old_exact_mcx6': sum(op.operation.name != 'x' for op in old.data),
                     'new_controlled_x_calls': sum(op.operation.name != 'x' for op in new.data)})
    full = {}
    for label, builder in [('baseline', baseline.build_controlled_multiplier), ('candidate', modular.build_controlled_multiplier)]:
        started = time.perf_counter()
        solution.build_controlled_multiplier = builder
        logical = solution.build_circuit(modulus=35)
        scored = native(native(logical))
        full[label] = {**compute_metrics(scored), 'build_and_score_seconds': time.perf_counter()-started}
    qft = compute_metrics(native(solution._inverse_qft_core(12)))
    result = {'basis': BASIS, 'optimization_level': 1, 'seed_transpiler': 12345,
              'multipliers': rows, 'full': full, 'inverse_qft_isolated': qft}
    print(json.dumps(result, indent=2))
    (ROOT / 'research/tier08_advanced/verification.json').write_text(json.dumps(result, indent=2)+'\n')

if __name__ == '__main__':
    run()
