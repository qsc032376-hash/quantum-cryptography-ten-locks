"""Paired local seeds and isolated official check, using the bounded harness."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
harness = ROOT.parent / 'Quantum-Cryptography-Benchmark-Harness'
sys.path.insert(0, str(harness))
from benchmarks.common import environment, run_worker
from benchmarks.cross_seed_regression import status


def main():
    baseline = ROOT.parent / 'Quantum-Cryptography-Tier05-Tier08-V2'
    assert os.popen(f'git -C "{baseline}" rev-parse HEAD').read().strip() == '0988ac44d88d08cc12258f2010afaf792dd53e7b'
    rows = []
    for seed in (801, 802):
        for variant, tree in (('baseline', baseline), ('candidate', ROOT)):
            result = run_worker('cross', tree, 8, seed, 120, 1536)
            rows.append({'variant': variant, 'seed': seed, 'status': status(result), 'result': result})
            print(variant, seed, rows[-1]['status'], flush=True)
    candidate = run_worker('official', ROOT, 8, None, 240, 1536)
    print('candidate official', candidate.get('status'), candidate.get('hash_ok'), candidate.get('metrics_status'), candidate.get('flags'), flush=True)
    output = {'environment': environment(), 'paired': rows, 'candidate_official': candidate}
    (ROOT / 'research/tier08_advanced/validation.json').write_text(json.dumps(output, indent=2)+'\n')

if __name__ == '__main__':
    main()
