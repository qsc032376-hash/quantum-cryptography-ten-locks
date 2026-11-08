"""Official single-tier checks and timed Aer on disposable candidate copies."""
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from qiskit_aer import AerSimulator
from common import is_correct
from research.real_circuits import experiments
from research.real_circuits.experiments import ROOT, REF58, snapshot

OUT = ROOT/'research/real_circuits/results'


def install_variant(team, variant):
    if variant not in ('baseline', 'gf2', 'combined', 'mcx_only'):
        raise ValueError('Unknown variant')
    if variant in ('gf2', 'combined'):
        path = team/'tier05/solution.py'
        text = path.read_text()
        needle = '    result = simulator.run(compiled, shots=shots).result()'
        assert text.count(needle) == 1
        text = text.replace(needle, '    from research.real_circuits.experiments import gf2_runs\n'
                            '    compiled, _, _ = gf2_runs(compiled)\n' + needle)
        path.write_text(text)
    if variant in ('combined', 'mcx_only'):
        path = team/'tier05/oracle.py'
        text = path.read_text()
        needle = 'from qiskit.synthesis import synth_mcx_n_clean_m15, synth_mcx_n_dirty_m15'
        assert text.count(needle) == 1
        text = text.replace(needle, 'from qiskit.synthesis import synth_mcx_2_clean_kg24 as synth_mcx_n_clean_m15\n'
                            'from qiskit.synthesis import synth_mcx_n_dirty_m15')
        path.write_text(text)
    # Only a Tier 5 solve may be discovered by the unmodified Checker.
    for path in team.glob('tier*/solution.py'):
        if path.parent.name != 'tier05':
            path.unlink()


def profile(module):
    calls, compilations, passes = [], [], []
    original_run = AerSimulator.run
    original_compile = module.transpile
    original_pass = experiments.gf2_runs
    def timed_compile(*args, **kwargs):
        start = time.perf_counter()
        value = original_compile(*args, **kwargs)
        compilations.append(time.perf_counter()-start)
        return value
    def timed_pass(*args, **kwargs):
        start = time.perf_counter()
        value = original_pass(*args, **kwargs)
        passes.append(time.perf_counter()-start)
        return value
    def timed_run(self, *args, **kwargs):
        kwargs['seed_simulator'] = 2026
        start = time.perf_counter()
        job = original_run(self, *args, **kwargs)
        original_result = job.result
        def result(*a, **k):
            outcome = original_result(*a, **k)
            calls.append({'seed_simulator': 2026, 'shots': kwargs.get('shots'),
                          'success': bool(outcome.success), 'aer_seconds': time.perf_counter()-start})
            return outcome
        job.result = result
        return job
    start = time.perf_counter()
    with patch.object(module, 'transpile', timed_compile), patch.object(AerSimulator, 'run', timed_run), \
         patch.object(experiments, 'gf2_runs', timed_pass):
        answer = module.solve()
    passed = is_correct(5, answer)
    assert passed and len(calls) == 1 and calls[0]['shots'] == 128 and calls[0]['success']
    return {'hash_ok': passed, 'solve_seconds': time.perf_counter()-start,
            'compilation_seconds': compilations, 'research_pass_seconds': passes, 'aer_calls': calls}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    profiles = {}
    with tempfile.TemporaryDirectory(prefix='real-candidate-check-') as folder:
        for variant in ('baseline', 'gf2', 'combined'):
            team = snapshot(REF58, folder, 'checked_'+variant)
            install_variant(team, variant)
            destination = OUT/(variant+'_official')
            run = subprocess.run([sys.executable, str(ROOT/'tools/check_submission.py'), str(team),
                                  '--out', str(destination)], capture_output=True, timeout=180, cwd=ROOT)
            if run.returncode:
                raise RuntimeError('Checker process failed; inspect local run')
            report = json.loads((destination/'report.json').read_text())
            assert set(report['tiers']) == {'5'}
            entry = report['tiers']['5']
            assert entry['status'] == 'full' and entry['hash_ok'] and not entry['flags']
            assert entry['metrics_status'] == 'ok'
            print(variant, 'official', entry['metrics'], 'full/hash/no_flags', flush=True)
            module = importlib.import_module(team.name+'.tier05.solution')
            profiles[variant] = profile(module)
            profiles[variant]['source_sha256'] = {str(p.relative_to(team)):
                hashlib.sha256(p.read_bytes()).hexdigest() for p in (team/'tier05').glob('*.py')}
            print(variant, 'profile', profiles[variant]['aer_calls'], flush=True)
            (OUT/'profiles.json').write_text(json.dumps(profiles, indent=2)+'\n')

if __name__ == '__main__':
    main()
