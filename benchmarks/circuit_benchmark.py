#!/usr/bin/env python3
"""Compare executed solve() circuits in isolated committed Git snapshots."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.common import ROOT, environment, resolve, run_worker, snapshot, write_json

METRICS=('two_qubit_gates','depth','total_gates','active_qubits')


def protected_tree(commit):
    paths=['tools/check_submission.py','tools/scoring_config.yaml','hashes.txt','common'] + [f'tier{i:02d}' for i in range(1,11)]
    result={}
    for path in paths:
        result[path]=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',f'{commit}:{path}'],text=True).strip()
    return result


def cross_evidence(path, commit, tier):
    if not path: return None
    data=json.loads(Path(path).read_text())
    if data.get('kind')!='cross_seed_regression' or data.get('commit')!=commit: return None
    rows=[r for r in data.get('runs',[]) if r.get('tier')==tier]
    seeds=[r.get('seed') for r in rows]
    if len(rows)<10 or len(set(seeds))!=len(seeds) or any(r.get('status')!='PASS' or r.get('hash_ok') is not True for r in rows): return None
    forwarded=[seed for row in rows for seed in (row.get('seed_metadata',{}).get('actual_forwarded_simulator_seeds') or [])]
    if len(forwarded) < len(rows) or len(set(forwarded)) != len(forwarded): return None
    return sorted(seeds)


def compare(baseline,candidate,target='two_qubit_gates', rules_reviewed=False, reliability=False, reliability_reviewed=False):
    """Conservative recommendation: no inferred rule compliance or statistical proof."""
    changes={}
    for metric in METRICS:
        a=(baseline.get('metrics') or {}).get(metric); b=(candidate.get('metrics') or {}).get(metric)
        changes[metric]=None if a is None or b is None else b-a
    checks=[baseline.get('official'),candidate.get('official')]
    if any(x and (x.get('status') not in ('full',None) or x.get('hash_ok') is False) for x in checks):
        decision='REJECT'
    elif (not rules_reviewed or not reliability or not reliability_reviewed or any(not x or x.get('status')!='full' or x.get('hash_ok') is not True or x.get('flags') or x.get('metrics_status')!='ok' for x in checks)
          or any(changes[m] is None for m in METRICS)
          or any(x.get('resource',{}).get('state')!='ok' or not x.get('resource',{}).get('peak_rss_bytes_sampled')
                 or x.get('official',{}).get('resource',{}).get('state')!='ok'
                 or not x.get('official',{}).get('resource',{}).get('peak_rss_bytes_sampled') for x in (baseline,candidate))
          or any(x.get('profile_hash_ok') is not True or not x.get('instrumentation_verified') for x in (baseline,candidate))
          or baseline.get('native_transpilation_calls') != candidate.get('native_transpilation_calls')
          or baseline.get('application_rng_seed') != candidate.get('application_rng_seed')
          or any(x.get('official',{}).get('metrics') != x.get('metrics') for x in (baseline,candidate))):
        decision='INCONCLUSIVE'
    elif changes[target] >= 0:
        decision='REJECT'
    else:
        decision='ACCEPT'
    return {'changes':changes,'recommendation':decision,'target_metric':target,
            'rules_reviewed':rules_reviewed,'paired_multiseed_evidence':reliability,
            'reliability_reviewed':reliability_reviewed}


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',required=True); p.add_argument('--candidate',required=True)
    p.add_argument('--tier',type=int,choices=range(1,11),required=True); p.add_argument('--output',required=True)
    p.add_argument('--target',choices=METRICS,default='two_qubit_gates')
    p.add_argument('--official',action='store_true',help='also run the unmodified official check_tier for each ref')
    p.add_argument('--seed',type=int,default=2026,help='common simulator seed for profiling')
    p.add_argument('--timeout',type=float,default=120); p.add_argument('--memory-mb',type=int,default=1024)
    p.add_argument('--rules-reviewed',action='store_true',help='attest manual review of tier rules and recovery method')
    p.add_argument('--reliability-reviewed', action='store_true', help='attest human review of finite-sample reliability and regressions')
    p.add_argument('--baseline-regression'); p.add_argument('--candidate-regression')
    return p


def main(argv=None):
    p=parser(); args=p.parse_args(argv)
    if not 0 < args.timeout <= 120 or not 128<=args.memory_mb<=16384 or not 0<=args.seed<2**32: p.error('invalid resource budget')
    a,b=resolve(args.baseline),resolve(args.candidate)
    if protected_tree(a)!=protected_tree(b): p.error('official checker, challenge inputs, helpers, hashes or scoring config differ')
    report={'schema_version':1,'kind':'circuit_comparison','tier':args.tier,
            'scoring_config_git_blob':protected_tree(a)['tools/scoring_config.yaml'],
            'profile_simulator_seed':args.seed,'environment':environment(),'refs':{}}
    with tempfile.TemporaryDirectory(prefix='qbench_compare_') as tmp:
        for name,commit in [('baseline',a),('candidate',b)]:
            path=Path(tmp)/name; path.mkdir(); snapshot(commit,path)
            prof=run_worker('profile',path,args.tier,args.seed,args.timeout,args.memory_mb)
            score=prof.get('scoring',{})
            metrics=score.get('metrics') if score.get('seconds',121)<=120 else None
            item={'commit':commit,'metrics':metrics,'profile_hash_ok':prof.get('hash_ok'),
                  'solve_seconds':prof.get('solve_seconds'),'aer_timing':prof.get('aer_timing'),
                  'shots_total':prof.get('shots_total'),'scoring_transpile_seconds':score.get('seconds'),
                  'resource':prof.get('resource'),'exception_class':prof.get('exception_class'),
                  'native_transpilation_calls':prof.get('native_transpilation_calls'),
                  'application_rng_seed':prof.get('seed_metadata',{}).get('application_rng_seed'),
                  'instrumentation_verified': bool(prof.get('native_transpilation_calls')) and
                    'NONSTANDARD' not in json.dumps(prof.get('native_transpilation_calls')) and
                    prof.get('aer_circuits_observed') == prof.get('circuits_executed') and
                    prof.get('aer_calls',0) > 0 and prof.get('aer_timing',{}).get('jobs_finished') == prof.get('aer_calls') and
                    prof.get('seed_metadata',{}).get('actual_forwarded_simulator_seeds') == [(args.seed+i) % (2**32) for i in range(prof.get('aer_calls',0))],
                  'official':None}
            if args.official:
                item['official']=run_worker('official',path,args.tier,None,2*(args.timeout+60)+10,args.memory_mb)
            report['refs'][name]=item
            print(f'{name}: profile {prof.get("resource",{}).get("state")}',flush=True)
    seeds_a=cross_evidence(args.baseline_regression,a,args.tier)
    seeds_b=cross_evidence(args.candidate_regression,b,args.tier)
    reliability=bool(seeds_a and seeds_a==seeds_b)
    report['comparison']=compare(report['refs']['baseline'],report['refs']['candidate'],args.target,args.rules_reviewed,reliability,args.reliability_reviewed)
    print(f'\nTier {args.tier:02d} Optimization Comparison')
    print(f'{"Metric":24} {"Baseline":>14} {"Candidate":>14} {"Change":>14}')
    for m in METRICS:
        left=(report['refs']['baseline']['metrics'] or {}).get(m,'NOT MEASURED')
        right=(report['refs']['candidate']['metrics'] or {}).get(m,'NOT MEASURED')
        delta=report['comparison']['changes'][m]
        print(f'{m:24} {str(left):>14} {str(right):>14} {str(delta if delta is not None else "NOT MEASURED"):>14}')
    for name in ('baseline','candidate'):
        item=report['refs'][name]
        timing=item.get('aer_timing') or {}
        aer=timing.get('aer_job_elapsed_seconds') if timing.get('jobs_finished') else 'NOT MEASURED'
        memory=(item.get('resource') or {}).get('peak_rss_bytes_sampled') or 'NOT MEASURED'
        print(f'{name} Aer job elapsed (s): {aer}; peak sampled process-tree RSS (bytes): {memory}')
        o=report['refs'][name]['official'] or {}
        print(f"{name} Checker: {str(o.get('status','NOT MEASURED')).upper()}, SHA-256: { {True:'MATCH',False:'NO MATCH'}.get(o.get('hash_ok'),'NOT MEASURED') }")
    print('Recommendation:',report['comparison']['recommendation'])
    write_json(args.output,report)
    return 0 if report['comparison']['recommendation']=='ACCEPT' else 1

if __name__ == '__main__': sys.exit(main())
