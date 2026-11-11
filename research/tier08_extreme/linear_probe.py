"""Last full-circuit experiment: reuse accepted exact Tier 5 CX-window code.

The team-owned generic linear pass is read unchanged. No official oracle is
expanded or altered; these are our explicit compiled reversible operations.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from qiskit import transpile
import numpy as np
from submissions.team3.tier05.gf2_synthesis import gf2_runs, extract_matrix
from submissions.team3.tier08 import solution
from research.tier08_extreme.screen import build
from tools.check_submission import compute_metrics, load_config
HERE = Path(__file__).resolve().parent


def main():
    path = HERE/'whole_candidates.json'
    record = json.loads(path.read_text())
    assert len(record['results']) < 12, 'whole-circuit budget exhausted'
    selected = json.loads((HERE/'third_selected.json').read_text())
    started = time.perf_counter()
    circuit = build(selected, mode='native')
    native = transpile(circuit, basis_gates=solution.BASIS_GATES,
                       optimization_level=1, seed_transpiler=12345, num_processes=1)
    native_time = time.perf_counter()-started
    rewritten, stats, certificates = gf2_runs(native)
    assert native.global_phase == rewritten.global_phase
    assert all(np.array_equal(extract_matrix(a),extract_matrix(b)) for a,b in certificates)
    cfg = load_config()
    scored = transpile(rewritten, **{k: cfg[k] for k in
                       ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')},
                       num_processes=1)
    result = {'label':'boolean_third_native_linear','selected_file':'third_selected.json',
              'source_operations_sha256':hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest(),
              'emission':{'mode':'native','pivot':'first','allocation':'work_first'},
              'linear_stats':stats,'all_linear_certificates_exact':True,
              'linear_source_sha256':hashlib.sha256((ROOT/'submissions/team3/tier05/gf2_synthesis.py').read_bytes()).hexdigest(),
              'whole':{'metrics':compute_metrics(scored),'compile_seconds':time.perf_counter()-started,
                       'solve_transpile_seconds':native_time,'scoring_and_linear_seconds':time.perf_counter()-started-native_time},
              'powers':solution.count_modular_powers(circuit)}
    record['results'].append(result);record['evaluated']=len(record['results'])
    path.write_text(json.dumps(record,indent=2)+'\n')
    (HERE/'linear_probe.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['whole']['metrics'],stats,flush=True)


if __name__ == '__main__':
    main()
