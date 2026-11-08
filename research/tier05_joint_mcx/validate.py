"""Isolated Tier 5 checker and bounded paired seed tests; safe summaries only."""
import argparse,importlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from research.real_circuits.experiments import snapshot,REF58
from research.real_circuits.validate_candidates import install_variant
ROOT=Path(__file__).resolve().parents[2]
PATCH='''
def build_circuit(*, ciphertext=None, iterations=ITERATIONS):
    from types import SimpleNamespace
    from research.tier05_joint_mcx.experiment import clean_circuit
    _validate_iterations(iterations)
    if iterations != ITERATIONS: raise ValueError("research prototype supports 25 iterations")
    if ciphertext is None: ciphertext, _ = _public_inputs()
    return clean_circuit(SimpleNamespace(oracle=oracle),ciphertext)[1]
'''

def prepare(d,name,candidate):
    team=snapshot(REF58,d,name); install_variant(team,'gf2')
    if candidate:
        with (team/'tier05/solution.py').open('a') as f: f.write(PATCH)
    return team

def worker(candidate,seed):
    from common import is_correct
    from qiskit_aer.backends.aerbackend import AerBackend
    seen=[]; original=AerBackend.run
    def run(self,circuits,*args,**kwargs):
        kwargs['seed_simulator']=seed
        seen.append({'forwarded_seed':kwargs['seed_simulator'],'shots':kwargs.get('shots'),'circuits':len(circuits) if isinstance(circuits,(tuple,list)) else 1})
        return original(self,circuits,*args,**kwargs)
    with tempfile.TemporaryDirectory(prefix='tier5-joint-pair-') as d:
        team=prepare(d,'pair_candidate' if candidate else 'pair_baseline',candidate)
        m=importlib.import_module(team.name+'.tier05.solution')
        started=time.monotonic()
        with patch.object(AerBackend,'run',run): answer=m.solve()
        seconds=time.monotonic()-started
        return {'seed':seed,'variant':'clean' if candidate else 'baseline','solve_seconds':round(seconds,4),
                'hash_ok':is_correct(5,answer),'runs':seen}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--worker',choices=('baseline','clean'));p.add_argument('--seed',type=int); args=p.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker=='clean',args.seed))); return
    env=dict(os.environ,PYTHONPATH=str(ROOT),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONHASHSEED='0')
    rows=[]
    for seed in (1000,2000):
        for variant in ('baseline','clean'):
            cmd=[sys.executable,'-B','-m','research.tier05_joint_mcx.validate','--worker',variant,'--seed',str(seed)]
            try:
                p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=120)
                if p.returncode: row={'seed':seed,'variant':variant,'status':'ERROR','exit_code':p.returncode}
                else:
                    row=json.loads(p.stdout.strip().splitlines()[-1]); row['status']='PASS' if row['hash_ok'] and row['runs']==[{'forwarded_seed':seed,'shots':128,'circuits':1}] else 'FAIL'
            except subprocess.TimeoutExpired: row={'seed':seed,'variant':variant,'status':'TIMEOUT'}
            rows.append(row);print(json.dumps(row),flush=True)
            (ROOT/'research/tier05_joint_mcx/paired_results.json').write_text(json.dumps(rows,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='tier05-joint-check-') as d:
        team=prepare(d,'jointcheck',True); out=Path(d)/'checker'
        try:
            p=subprocess.run([sys.executable,str(ROOT/'tools/check_submission.py'),str(team),'--out',str(out)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=240)
            file=out/'report.json'
            if not file.exists(): result={'status':'ERROR','process_returncode':p.returncode}
            else:
                report=json.loads(file.read_text()); assert set(report['tiers'])=={'5'}
                e=report['tiers']['5']; result={k:e.get(k) for k in ('status','hash_ok','metrics_status','metrics','flags','solve_seconds','circuits_executed')};result['process_returncode']=p.returncode
        except subprocess.TimeoutExpired: result={'status':'TIMEOUT'}
        print(json.dumps(result),flush=True)
        (ROOT/'research/tier05_joint_mcx/checker_result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__': main()
