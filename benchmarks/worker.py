"""Isolated subprocess: never print answers, counts, raw errors or challenge inputs."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

mode, tree, raw_tier, seed_arg, prefix = sys.argv[1:]
tree, tier = Path(tree).resolve(), int(raw_tier)
sys.path.insert(0, str(tree))
os.chdir(tree)
spec = importlib.util.spec_from_file_location('official_checker', tree / 'tools/check_submission.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
config = checker.load_config()
solution = tree / 'submissions/team3' / f'tier{tier:02d}' / 'solution.py'
out = {}

if mode == 'official':
    from common import load_hashes
    entry = checker.check_tier(tier, solution, config, load_hashes()[tier], False)
    # The official tool's exception message can contain secrets; keep class only.
    error = entry.pop('error', None)
    if error: entry['exception_class'] = error.split(':', 1)[0]
    out = entry
elif mode in ('cross', 'profile'):
    from qiskit_aer.backends.aerbackend import AerBackend
    import inspect
    import qiskit
    import qiskit.compiler
    from qiskit_aer.jobs.aerjob import AerJob
    original_run, original_result = AerBackend.run, AerJob.result
    original_transpile, original_compiler_transpile = qiskit.transpile, qiskit.compiler.transpile
    transpile_calls = []
    if mode == 'profile':
        def controlled_transpile(*args, **kwargs):
            bound = inspect.signature(original_transpile).bind_partial(*args, **kwargs)
            bound.arguments['seed_transpiler'] = config['seed_transpiler']
            def public_config(value):
                if value is None or isinstance(value, (str, int, float, bool)): return value
                if isinstance(value, (list, tuple)): return [public_config(x) for x in value]
                return 'NONSTANDARD'
            backend = bound.arguments.get('backend')
            transpile_calls.append({'seed_transpiler': bound.arguments['seed_transpiler'],
                                    'optimization_level': bound.arguments.get('optimization_level'),
                                    'basis_gates': public_config(bound.arguments.get('basis_gates')),
                                    'coupling_map': public_config(bound.arguments.get('coupling_map')),
                                    'target': public_config(bound.arguments.get('target')),
                                    'backend_class': type(backend).__name__ if backend is not None else None})
            return original_transpile(*bound.args, **bound.kwargs)
        qiskit.transpile = qiskit.compiler.transpile = controlled_transpile
    observed, job_starts, solution_seeds = [], {}, {}
    original_loader = checker.load_solution
    tier10_aggregate, tier05_aggregate = {}, {}
    def load_with_metadata(path):
        module = original_loader(path)
        for name in ('SEED_TRANSPILER', 'SEED_SIMULATOR', 'BASIS_SEED'):
            value = getattr(module, name, None)
            if isinstance(value, int): solution_seeds[name] = value
        if mode == 'cross' and tier == 10 and callable(getattr(module, 'recover_exponent_with_diagnostics', None)):
            original_recovery = module.recover_exponent_with_diagnostics
            def observe_recovery():
                recovery = original_recovery()
                diagnostics = recovery.diagnostics
                evidence = diagnostics.get('readout_evidence', {})
                # Whitelist only aggregate integer counters; never retain outcomes or candidates.
                for key in ('total_shots', 'distinct_outcomes', 'informative_shots',
                            'uninformative_shots', 'inconsistent_shots', 'partial_equation_shots'):
                    value = evidence.get(key)
                    if type(value) is int and value >= 0: tier10_aggregate[key] = value
                value = diagnostics.get('verified_informative_support_shots')
                if type(value) is int and value >= 0:
                    tier10_aggregate['verified_support_shots'] = value
                return recovery
            module.recover_exponent_with_diagnostics = observe_recovery
        if mode == 'cross' and tier == 5 and callable(getattr(module, 'recover_key_with_diagnostics', None)):
            original_recovery = module.recover_key_with_diagnostics
            def observe_tier05():
                result = original_recovery()
                diagnostics = result[1]
                # Store aggregate counts only; the measured key is never recorded.
                for key in ('shots', 'distinct_measured_candidates', 'prefix_valid_candidates', 'prefix_success_shots'):
                    value = diagnostics.get(key)
                    if type(value) is int and value >= 0: tier05_aggregate[key] = value
                return result
            module.recover_key_with_diagnostics = observe_tier05
        return module
    checker.load_solution = load_with_metadata
    timing = {'result_wait_seconds': 0.0, 'aer_job_elapsed_seconds': 0.0, 'jobs_finished': 0}
    seed = None if seed_arg == '-' else int(seed_arg)
    def run(self, circuits, *args, **kwargs):
        if seed is not None:
            kwargs['seed_simulator'] = (seed + len(observed)) % (2**32)
        shots = kwargs.get('shots', self.options.shots)
        number = len(circuits) if isinstance(circuits, (tuple, list)) else 1
        started = time.perf_counter()
        job = original_run(self, circuits, *args, **kwargs)
        job_starts[id(job)] = started
        observed.append({'injected_seed': kwargs.get('seed_simulator') if seed is not None else None,
                         'shots_per_circuit': shots, 'circuits': number})
        return job
    def result(self, *args, **kwargs):
        start = time.perf_counter()
        try: return original_result(self, *args, **kwargs)
        finally:
            end = time.perf_counter()
            timing['result_wait_seconds'] += end-start
            if id(self) in job_starts:
                timing['aer_job_elapsed_seconds'] += end-job_starts.pop(id(self))
                timing['jobs_finished'] += 1
    AerBackend.run, AerJob.result = run, result
    checker.worker_solve(tier, solution, prefix)
    qiskit.transpile, qiskit.compiler.transpile = original_transpile, original_compiler_transpile
    raw = json.loads(Path(prefix + '.json').read_text())
    from common import load_hashes
    error = raw.get('error')
    if error: out['exception_class'] = error.split(':', 1)[0]
    out.update({'hash_ok': raw.get('answer_hash') == load_hashes()[tier],
                'solve_seconds': raw.get('solve_seconds'),
                'circuits_executed': raw.get('circuits_executed'),
                'unique_circuits': raw.get('unique_circuits'),
                'not_implemented': raw.get('not_implemented'),
                'shots_total': (sum(x['shots_per_circuit'] * x['circuits'] for x in observed)
                                if all(isinstance(x['shots_per_circuit'], int) for x in observed) else None),
                'aer_circuits_observed': sum(x['circuits'] for x in observed),
                'shots_known': all(isinstance(x['shots_per_circuit'], int) for x in observed),
                'aer_calls': len(observed), 'aer_timing': timing,
                'native_transpilation_calls': transpile_calls if mode == 'profile' else None,
                'seed_metadata': {'requested_simulator_seed': seed,
                                  'actual_forwarded_simulator_seeds': [x['injected_seed'] for x in observed] if seed is not None else None,
                                  'solution_declared_seeds': solution_seeds,
                                  'transpiler_seed': solution_seeds.get('SEED_TRANSPILER', 'solution default (not injected)'),
                                  'application_rng_seed': solution_seeds.get('BASIS_SEED', 'solution default (not injected)')}})
    if tier10_aggregate: out['tier10_readout_aggregate'] = tier10_aggregate
    if tier05_aggregate: out['tier05_readout_aggregate'] = tier05_aggregate
    if mode == 'profile' and raw.get('unique_circuits') and not raw.get('serialize_error'):
        metrics_file = prefix + '.metrics.json'
        checker.worker_transpile(prefix + '.circuits', metrics_file)
        out['scoring'] = json.loads(Path(metrics_file).read_text())
    if raw.get('serialize_error'): out['serialize_error_class'] = raw['serialize_error'].split(':', 1)[0]
    if tier == 2: out['repeat_measurements'] = raw.get('repeat_measurements')
else:
    raise ValueError('Invalid mode')
Path(prefix + '.safe.json').write_text(json.dumps(out), encoding='utf-8')
