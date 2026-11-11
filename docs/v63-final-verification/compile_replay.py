"""Bounded diagnostic of fixed production compilation, never running Aer.

Tier 5 reproduces its sole circuit pipeline. Tier 6's measured iteration
selection and Tier 7's measured-phase check cannot be replayed without
measurements; those limitations are explicit, not bypassed with hidden data.
No circuit, parameter, count string, phase, key or plaintext is saved.
"""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def worker(root, tier):
    sys.path.insert(0,str(root))
    from qiskit import qpy, transpile
    from qiskit_aer import AerSimulator
    from tools.check_submission import compute_metrics,load_config
    path=root/f'submissions/team3/tier{tier:02d}/solution.py'
    spec=importlib.util.spec_from_file_location(f'audit_tier{tier}',path)
    solution=importlib.util.module_from_spec(spec);sys.modules[spec.name]=solution;spec.loader.exec_module(solution)
    if tier==5:
        circuits=[('sole_Grover_circuit',solution.build_circuit())]
        scope='FULL_COMPILATION_PIPELINE: sole real solver circuit, without Aer execution'
    elif tier==6:
        circuits=[('actual_calibration_builder',solution.build_calibration_circuit()),
                  ('nominal_12_round_search_builder',solution.build_circuit())]
        scope='PARTIAL: search uses documented nominal 12 rounds, not a recovered calibration outcome; cannot certify actual scored-winner identity'
    else:
        circuits=[('actual_first_QPE_builder',solution.build_circuit())]
        scope='PARTIAL: first real QPE circuit only; second phase-check depends on measured private k and is intentionally skipped'
    cfg=load_config();rows=[]
    for label,circuit in circuits:
        started=time.monotonic();original=circuit.copy();original.name='audit_input';original.metadata={}
        buf=io.BytesIO();qpy.dump(original,buf)
        # Used transiently by parent only to compare repeated inputs; not saved.
        private_digest=hashlib.sha256(buf.getvalue()).hexdigest()
        if tier==5:
            backend=AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2)
            native=transpile(circuit,backend,basis_gates=solution.BASIS_GATES,
                             optimization_level=2,seed_transpiler=solution.SEED_TRANSPILER,num_processes=1)
            native,_,_=solution.gf2_synthesis.gf2_runs(native)
        else:
            native=transpile(circuit,basis_gates=solution.BASIS_GATES,
                             optimization_level=solution.PRE_OPTIMIZATION_LEVEL,
                             seed_transpiler=solution.SEED_TRANSPILER,num_processes=1)
        pre_seconds=time.monotonic()-started
        native_metrics=compute_metrics(native);native_ops={k:int(v) for k,v in native.count_ops().items()}
        # Match official recorder's canonicalization and QPY transport.
        native.name='scored';native.metadata={};buf=io.BytesIO();qpy.dump(native,buf);buf.seek(0)
        recorded=qpy.load(buf)[0];start=time.monotonic()
        scored=transpile(recorded,**{k:cfg[k] for k in ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')})
        rows.append({'circuit':label,'scope':scope,'private_input_digest':private_digest,
                     'precompile_metrics':native_metrics,'precompile_count_ops':native_ops,
                     'official_basis_metrics':compute_metrics(scored),
                     'official_basis_count_ops':{k:int(v) for k,v in scored.count_ops().items()},
                     'precompile_seconds':pre_seconds,'scoring_compile_seconds':time.monotonic()-start})
    return {'tier':tier,'rows':rows,'aer_run_calls':0,'scope':scope}


def main():
    p=argparse.ArgumentParser();p.add_argument('--official-root',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--worker',type=int);a=p.parse_args()
    if a.worker:
        print(json.dumps(worker(a.official_root,a.worker)));return
    assert a.output and not a.output.exists()
    env=os.environ.copy();env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',QISKIT_PARALLEL='FALSE',PYTHONHASHSEED='0')
    result={'purpose':'Read-only compile diagnostic after actual fresh Checker metric differences',
            'environment':{'python':sys.version.split()[0],'qiskit':importlib.metadata.version('qiskit'),'qiskit_aer':importlib.metadata.version('qiskit-aer'),'numpy':importlib.metadata.version('numpy')},
            'thread_and_hash_environment':{k:env.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','QISKIT_PARALLEL','PYTHONHASHSEED','RAYON_NUM_THREADS')},
            'rayon_changed':False,'transpiler_seed':12345,'precompile_optimization_level':2,
            'official_scoring_optimization_level':1,'replays_per_tier':2,'worker_timeout_seconds':30,
            'actual_aer_run_calls':0,'submission_or_checker_modified':False,'circuits_or_private_parameters_saved':False,
            'results':[],'paired_comparison':{},
            'compiler_sensitivity_note':'The installed Optimize1qGatesDecomposition documents Rayon threading; OneQubitEulerDecomposer uses an angle simplification tolerance. These are possible diagnostic mechanisms, NOT an established cause.',
            'input_identity_note':'QPY byte inequality is not a proof of different unitary action; this diagnostic does not inspect or normalize opaque gate internals/identifiers. Where input_qpy_bytes_identical is false, do not claim identical serialized inputs or establish compiler nondeterminism.'}
    private={};failed=False
    for tier in (5,6,7):
        for run in (1,2):
            command=[sys.executable,str(Path(__file__).resolve()),'--official-root',str(a.official_root),'--worker',str(tier)]
            try:
                proc=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30)
                if proc.returncode:
                    result['results'].append({'tier':tier,'replay':run,'status':'FAILED','exception_text_saved':False});failed=True;break
                row=json.loads(proc.stdout);row['replay']=run;row['status']='PASS'
                for item in row['rows']:private[tier,run,item['circuit']]=item.pop('private_input_digest')
                result['results'].append(row)
            except subprocess.TimeoutExpired:
                result['results'].append({'tier':tier,'replay':run,'status':'TIMEOUT'});failed=True;break
            a.output.write_text(json.dumps(result,indent=2)+'\n')
        if failed:break
        pair=[x for x in result['results'] if x['tier']==tier]
        result['paired_comparison'][str(tier)]={}
        for one,two in zip(pair[0]['rows'],pair[1]['rows']):
            label=one['circuit'];result['paired_comparison'][str(tier)][label]={
                'input_qpy_bytes_identical':private[tier,1,label]==private[tier,2,label],
                'precompile_metrics_identical':one['precompile_metrics']==two['precompile_metrics'],
                'scored_metrics_identical':one['official_basis_metrics']==two['official_basis_metrics'],
                'scored_count_ops_identical':one['official_basis_count_ops']==two['official_basis_count_ops']}
    result['status']='DIAGNOSTIC_COMPLETE' if not failed else 'DIAGNOSTIC_INCOMPLETE'
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'paired_comparison':result['paired_comparison']}))

if __name__=='__main__':main()
