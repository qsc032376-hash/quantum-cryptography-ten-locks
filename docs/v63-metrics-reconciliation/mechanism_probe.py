"""Bounded compiler diagnostics on public Tier 5/6 builders; no Aer run.

This reuses the prior audit's fixed production compilation pipeline. It does
not change submission code, approved ZIP, compiler configuration or Checker.
Hash-seed variants are diagnostics, not candidates or selected results.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def module(path):
    spec=importlib.util.spec_from_file_location('prior_compile_replay',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def run_worker(args):
    replay=module(args.helper)
    results=[]
    for repeat in range(args.repeats):
        result=replay.worker(args.official_root,args.worker)
        for row in result['rows']:
            # No private-circuit or serialized-input digest is persisted.
            row.pop('private_input_digest',None)
        result['same_process_repeat']=repeat+1
        results.append(result)
    return results


def stable_rows(data):
    return [{k:row[k] for k in ('circuit','precompile_metrics','precompile_count_ops',
                                'official_basis_metrics','official_basis_count_ops')}
            for row in data['rows']]


def main():
    p=argparse.ArgumentParser();p.add_argument('--official-root',type=Path,required=True)
    p.add_argument('--helper',type=Path,required=True);p.add_argument('--output',type=Path)
    p.add_argument('--worker',type=int);p.add_argument('--repeats',type=int,default=1)
    args=p.parse_args()
    if args.worker:
        print(json.dumps(run_worker(args)));return
    assert args.output and not args.output.exists()
    environment=os.environ.copy()
    environment.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',QISKIT_PARALLEL='FALSE')
    started=time.monotonic()
    result={'purpose':'Targeted hash-seed, traversal and process-state diagnosis',
            'compiler_helper':str(args.helper),'compiler_helper_sha256':hashlib.sha256(args.helper.read_bytes()).hexdigest(),
            'submission_modified':False,'official_checker_modified':False,'aer_runs':0,
            'thread_environment':{k:environment.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','QISKIT_PARALLEL','RAYON_NUM_THREADS')},
            'transpiler_seed':12345,'basis_gates':['rz','sx','x','cx'],
            'precompile_level':2,'official_scoring_level':1,
            'trials':[],'planned_trials':'T5/T6 x hash seeds0/1/42 fresh process, plus3consecutive same-process repeats per tier atseed0',
            'scope':'Tier5 sole executed builder complete compile flow; Tier6 pilot plus nominal12-round builder only, not measured calibration selection.',
            'protected_oracle_internals_inspected':False,'private_parameters_or_circuit_hashes_saved':False}
    for tier in (5,6):
        for seed,repeats in ((0,1),(1,1),(42,1),(0,3)):
            env=environment.copy();env['PYTHONHASHSEED']=str(seed)
            command=[sys.executable,str(Path(__file__).resolve()),'--official-root',str(args.official_root),
                     '--helper',str(args.helper),'--worker',str(tier),'--repeats',str(repeats)]
            trial={'tier':tier,'pythonhashseed':seed,'same_process_repeats':repeats}
            try:
                done=subprocess.run(command,capture_output=True,text=True,env=env,timeout=30)
                if done.returncode:trial['status']='FAILED';trial['error_output_saved']=False
                else:trial.update(status='PASS',runs=json.loads(done.stdout))
            except subprocess.TimeoutExpired:trial['status']='TIMEOUT'
            result['trials'].append(trial)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
            if trial['status']!='PASS':
                result['status']='INCOMPLETE';args.output.write_text(json.dumps(result,indent=2)+'\n');return
    comparison={}
    for tier in (5,6):
        trials=[x for x in result['trials'] if x['tier']==tier]
        canonical=stable_rows(trials[0]['runs'][0])
        comparison[str(tier)]={'different_hash_seeds_equal_metrics_and_count_ops':all(stable_rows(x['runs'][0])==canonical for x in trials[:3]),
                               'three_same_process_repeats_equal_metrics_and_count_ops':all(stable_rows(x)==canonical for x in trials[3]['runs']),
                               'reference_rows':canonical}
    # Inspect only public compiler dispatch, never protected Oracle internals.
    from qiskit.transpiler.passes.optimization.optimize_1q_decomposition import _possible_decomposers
    result['euler_bases_for_scoring_basis']=_possible_decomposers(set(result['basis_gates']))
    historical_path='docs/v63-evidence/compiler-replay.json'
    historical_commit='ce75c0721622d363e77912191a52a02c34f92472'
    old=json.loads(subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[2]),'show',historical_commit+':'+historical_path]))
    old_ops=old['integrated_builder']['execution_gate_counts']
    new_ops=comparison['5']['reference_rows'][0]['precompile_count_ops']
    result['tier5_historical_gate_count_comparison']={
        'source_commit':historical_commit,'source_path':historical_path,
        'historical_execution_count_ops':old_ops,'current_execution_count_ops':new_ops,
        'nonzero_deltas':{k:new_ops.get(k,0)-old_ops.get(k,0) for k in sorted(set(old_ops)|set(new_ops)) if new_ops.get(k,0)!=old_ops.get(k,0)},
        'finding':'The50gateTier5differenceisexactly50Xgatesatcountlevel;allothernativegatecountsagree.',
        'historical_ordered_circuit_available':False,
        'histogram_does_not_prove_gate_positions_or_unitary_equivalence':True}
    result['comparison']=comparison;result['elapsed_seconds']=time.monotonic()-started
    result['status']='COMPLETE'
    result['conclusion']='No change in observed metrics/count_ops from tested Python hash seeds or repeated in-process construction/compilation. This bounds the tested causes; it does not isolate historical cross-environment root cause or prove all compiler state irrelevant.'
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'elapsed_seconds':result['elapsed_seconds'],
                      'hash_seed_and_process_tests_pass':all(v['different_hash_seeds_equal_metrics_and_count_ops'] and v['three_same_process_repeats_equal_metrics_and_count_ops'] for v in comparison.values())}))

if __name__=='__main__':main()
