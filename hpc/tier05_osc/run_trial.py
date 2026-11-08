"""One seeded, isolated Tier 5 official check; output only safe aggregates."""
import argparse,hashlib,json,os,platform,signal,subprocess,sys,tempfile,time
from pathlib import Path
import psutil
from research.tier05_joint_mcx.validate import prepare

ROOT=Path(__file__).resolve().parents[2]
PATCH='''
_original_research_solve = solve

def solve():
    import os, json, hashlib
    from unittest.mock import patch
    from qiskit_aer.backends.aerbackend import AerBackend
    from common import load_hashes
    metadata_path=os.environ["T5_OBSERVATION_PATH"]
    seed=int(os.environ["T5_OBSERVATION_SEED"])
    observations=[]
    original=AerBackend.run
    def observe(self, circuits, *args, **kwargs):
        kwargs["seed_simulator"]=seed
        observations.append({"seed":kwargs["seed_simulator"],"shots":kwargs.get("shots"),"circuits":len(circuits) if isinstance(circuits,(list,tuple)) else 1})
        with open(metadata_path,"w") as f: json.dump({"calls":observations},f)
        return original(self,circuits,*args,**kwargs)
    with patch.object(AerBackend,"run",observe):
        answer=_original_research_solve()
    good=hashlib.sha256(answer.encode("utf-8")).hexdigest()==load_hashes()[5]
    with open(metadata_path,"w") as f: json.dump({"calls":observations,"independent_hash_ok":good},f)
    return answer
'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',required=True,choices=('baseline','clean'));p.add_argument('--seed',required=True,type=int,choices=range(1000,10001,1000));p.add_argument('--output',required=True,type=Path);p.add_argument('--preflight',action='store_true');a=p.parse_args()
    if a.output.exists():p.error('result already exists')
    if not a.output.parent.is_dir():p.error('output directory missing')
    if not a.preflight and not os.environ.get('SLURM_JOB_ID'):p.error('must run in a Slurm allocation')
    with tempfile.TemporaryDirectory(prefix='tier05_osc_',dir=os.environ.get('TMPDIR')) as d:
        team=prepare(d,'seedcheck',a.variant=='clean')
        with (team/'tier05/solution.py').open('a') as f:f.write(PATCH)
        if a.preflight:
            compile((team/'tier05/solution.py').read_text(),str(team/'tier05/solution.py'),'exec')
            print('preflight ok',a.variant,a.seed);return
        obs=Path(d)/'safe_observation.json'; out=Path(d)/'checker'; env=dict(os.environ,T5_OBSERVATION_PATH=str(obs),T5_OBSERVATION_SEED=str(a.seed),PYTHONPATH=str(ROOT),PYTHONHASHSEED='0',QISKIT_PARALLEL='FALSE',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        cmd=[sys.executable,str(ROOT/'tools/check_submission.py'),str(team),'--out',str(out)]
        start=time.monotonic(); process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        parent=psutil.Process(process.pid);peak=0;timeout=False
        while process.poll() is None:
            try:peak=max(peak,sum(x.memory_info().rss for x in [parent,*parent.children(recursive=True)] if x.is_running()))
            except psutil.Error:pass
            if time.monotonic()-start>370:
                timeout=True;os.killpg(process.pid,signal.SIGKILL);break
            time.sleep(.05)
        process.wait();wall=time.monotonic()-start
        info={}
        if obs.exists():info=json.loads(obs.read_text())
        check={};file=out/'report.json'
        if file.exists():
            report=json.loads(file.read_text()); entry=report['tiers']['5']
            check={k:entry.get(k) for k in ('status','hash_ok','metrics','metrics_status','flags','solve_seconds','circuits_executed')}
        flags=check.get('flags') or []
        if timeout or check.get('status')=='timeout' or any('over solve_timeout' in x for x in flags): status='TIMEOUT'
        elif process.returncode or not check:status='ERROR'
        elif check.get('status')=='full' and check.get('hash_ok') is True and check.get('metrics_status')=='ok' and not flags and info.get('independent_hash_ok') is True and info.get('calls')==[{'seed':a.seed,'shots':128,'circuits':1}]:status='PASS'
        else:status='FAIL'
        cpu=Path('/proc/cpuinfo');models=sorted({l.split(':',1)[1].strip() for l in cpu.read_text().splitlines() if l.startswith('model name')}) if cpu.exists() else []
        result={'variant':a.variant,'requested_seed':a.seed,'status':status,'observed':info,'checker':check,'checker_wall_seconds':round(wall,4),'sampled_process_tree_peak_rss_bytes':peak,'exit_code':process.returncode,'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'node':os.environ.get('SLURMD_NODENAME'),'cpu_models':models,'platform':platform.platform(),'python':platform.python_version(),'timeout_seconds_outer':370}
        with a.output.open('x') as f:json.dump(result,f,indent=2)
        print(a.variant,a.seed,status,flush=True)

if __name__=='__main__':main()
