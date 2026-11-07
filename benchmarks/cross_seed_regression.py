#!/usr/bin/env python3
"""Run bounded, isolated measurement-seed trials without saving secrets."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.common import environment, resolve, snapshot, run_worker, write_json


def status(result):
    if result.get('resource', {}).get('state') != 'ok': return 'FAIL'
    if result.get('not_implemented'): return 'SKIP'
    if result.get('exception_class') or not result.get('hash_ok') or result.get('solve_seconds', 121) > 120: return 'FAIL'
    metadata = result.get('seed_metadata', {})
    observed = metadata.get('actual_forwarded_simulator_seeds') or []
    requested = metadata.get('requested_simulator_seed')
    if (not isinstance(requested, int) or not observed or
        observed != [(requested + i) % (2**32) for i in range(len(observed))] or
        len(observed) != result.get('aer_calls') or not result.get('circuits_executed')):
        return 'UNCONTROLLED'
    if result.get('aer_timing', {}).get('jobs_finished') != len(observed): return 'UNCONTROLLED'
    if result.get('aer_circuits_observed') != result.get('circuits_executed'): return 'UNCONTROLLED'
    return 'PASS'


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tiers', type=int, nargs='+', required=True, choices=range(1,11))
    p.add_argument('--seeds', type=int, nargs='+', required=True)
    p.add_argument('--ref', default='release/ten-locks-v1')
    p.add_argument('--output', required=True)
    p.add_argument('--timeout', type=float, default=120, help='per run, at most 120 seconds')
    p.add_argument('--memory-mb', type=int, default=1024)
    p.add_argument('--total-seconds', type=float, default=300)
    return p


def main(argv=None):
    p=parser(); args=p.parse_args(argv)
    if (len(set(args.seeds)) != len(args.seeds) or any(s < 0 or s >= 2**32 for s in args.seeds)
        or len(set(args.tiers)) != len(args.tiers) or len(args.seeds)*len(args.tiers)>100
        or not 0 < args.timeout <= 120 or not 0 < args.total_seconds <= 3600 or not 128 <= args.memory_mb <= 16384):
        p.error('invalid or duplicate seeds/tiers, or resource budget outside bounds')
    commit=resolve(args.ref)
    report={'schema_version': 1, 'kind':'cross_seed_regression', 'commit':commit,
            'runs':[], 'environment':environment(), 'limits':{'per_run_seconds':args.timeout,'total_seconds':args.total_seconds,'memory_mb':args.memory_mb},
            'seed_policy':'AerBackend.run injected requested seed plus call index modulo 2^32; application RNG and transpiler untouched'}
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='qbench_tree_') as tmp:
        snapshot(commit,tmp)
        for tier in args.tiers:
            for seed in args.seeds:
                remaining=args.total_seconds-(time.monotonic()-started)
                if remaining <= 0:
                    report['runs'].append({'tier':tier,'seed':seed,'status':'SKIP','reason':'total_budget'})
                    continue
                result=run_worker('cross',tmp,tier,seed,min(args.timeout,remaining),args.memory_mb)
                result.update(tier=tier,seed=seed)
                state=result['resource']['state']
                if state != 'ok':
                    result.setdefault('exception_class', {'timeout':'TimeoutError','memory_limit':'MemoryLimitExceeded','worker_error':'WorkerError'}.get(state, 'WorkerError'))
                    result.setdefault('shots_total', None)
                    result.setdefault('seed_metadata', {'requested_simulator_seed':seed, 'actual_forwarded_simulator_seeds':None})
                result['status']=status(result)
                report['runs'].append(result)
                print(f"Tier {tier:02d} seed {seed}: {result['status']}",flush=True)
    write_json(args.output,report)
    return 0 if all(r['status']=='PASS' for r in report['runs']) else 1

if __name__ == '__main__': sys.exit(main())
