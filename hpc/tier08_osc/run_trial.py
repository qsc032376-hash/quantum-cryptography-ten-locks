"""Isolated Tier 8 official checks with optional observed Aer seed; safe data only."""
import argparse, importlib.metadata, io, json, os, platform, signal, subprocess, sys, tarfile, tempfile, time
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parents[2]
REFS={'baseline':'0988ac44d88d08cc12258f2010afaf792dd53e7b',
      'candidate':'b92a17fae7cf14c880e6457bce4f3c339626fc94'}
PATCH='''
_osc_original_solve = solve

def solve():
    import os, json, hashlib
    from unittest.mock import patch
    from qiskit_aer.backends.aerbackend import AerBackend
    from common import load_hashes
    path=os.environ["T8_OBSERVATION_PATH"]
    seed=int(os.environ["T8_OBSERVATION_SEED"])
    observations=[]
    original=AerBackend.run
    def observe(self,circuits,*args,**kwargs):
        kwargs["seed_simulator"]=(seed+len(observations)) % (2**32)
        observations.append({"seed":kwargs["seed_simulator"],"shots":kwargs.get("shots"),"circuits":len(circuits) if isinstance(circuits,(list,tuple)) else 1,"method":self.options.method,"precision":self.options.precision})
        with open(path,"w") as f: json.dump({"calls":observations},f)
        return original(self,circuits,*args,**kwargs)
    with patch.object(AerBackend,"run",observe):
        answer=_osc_original_solve()
    good=hashlib.sha256(answer.encode("utf-8")).hexdigest()==load_hashes()[8]
    with open(path,"w") as f: json.dump({"calls":observations,"independent_hash_ok":good},f)
    return answer
'''


def prepare(ref, folder):
    data=subprocess.check_output(['git','archive',ref,'submissions/team3'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(folder,filter='data')
    team=Path(folder)/'submissions/team3'
    for path in team.glob('tier*/solution.py'):
        if path.parent.name!='tier08':path.unlink()
    return team


def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=REFS,required=True);p.add_argument('--seed',type=int);p.add_argument('--unseeded',action='store_true');p.add_argument('--preflight',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.unseeded == (a.seed is not None):p.error('use exactly one of --seed or --unseeded')
    if a.output.exists() or not a.output.parent.is_dir():p.error('output exists or parent missing')
    if not a.preflight and not os.environ.get('SLURM_JOB_ID'):p.error('Slurm allocation required')
    with tempfile.TemporaryDirectory(prefix='tier08_osc_',dir=os.environ.get('TMPDIR')) as d:
        team=prepare(REFS[a.variant],d)
        if not a.unseeded:
            with (team/'tier08/solution.py').open('a') as f:f.write(PATCH)
        compile((team/'tier08/solution.py').read_text(),str(team/'tier08/solution.py'),'exec')
        if a.preflight:
            print('preflight ok',a.variant,a.seed,'unseeded',a.unseeded);return
        obs=Path(d)/'safe_observation.json';out=Path(d)/'checker'
        env=dict(os.environ,T8_OBSERVATION_PATH=str(obs),T8_OBSERVATION_SEED=str(a.seed),PYTHONPATH=str(ROOT),PYTHONHASHSEED='0',QISKIT_PARALLEL='FALSE',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        cmd=[sys.executable,str(ROOT/'tools/check_submission.py'),str(team),'--out',str(out)]
        start=time.monotonic();process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        parent=psutil.Process(process.pid);peak=0;timeout=False
        while process.poll() is None:
            try:peak=max(peak,sum(x.memory_info().rss for x in [parent,*parent.children(recursive=True)] if x.is_running()))
            except psutil.Error:pass
            if time.monotonic()-start>370:
                timeout=True;os.killpg(process.pid,signal.SIGKILL);break
            time.sleep(.05)
        process.wait();wall=time.monotonic()-start
        info=json.loads(obs.read_text()) if obs.exists() else {}
        check={};report=out/'report.json'
        if report.exists():
            entry=json.loads(report.read_text())['tiers']['8']
            check={k:entry.get(k) for k in ('status','hash_ok','metrics','metrics_status','flags','solve_seconds','circuits_executed')}
        flags=check.get('flags') or []
        calls=info.get('calls') or []
        seed_ok=(a.unseeded or (info.get('independent_hash_ok') is True and 1<=len(calls)<=2 and all(c=={'seed':(a.seed+i)%(2**32),'shots':64,'circuits':1,'method':'statevector','precision':'double'} for i,c in enumerate(calls))))
        if timeout or check.get('status')=='timeout' or any('over solve_timeout' in s for s in flags):status='TIMEOUT'
        elif process.returncode or not check:status='ERROR'
        elif check.get('status')=='full' and check.get('hash_ok') is True and check.get('metrics_status')=='ok' and not flags and seed_ok:status='PASS'
        else:status='FAIL'
        cpu=Path('/proc/cpuinfo');models=sorted({l.split(':',1)[1].strip() for l in cpu.read_text().splitlines() if l.startswith('model name')}) if cpu.exists() else []
        versions={p:importlib.metadata.version(p) for p in ('qiskit','qiskit-aer','numpy','psutil')}
        result={'variant':a.variant,'source_commit':REFS[a.variant],'requested_seed':a.seed,'unseeded':a.unseeded,'status':status,'observed':info,'checker':check,'checker_wall_seconds':round(wall,4),'sampled_process_tree_peak_rss_bytes':peak,'exit_code':process.returncode,'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'node':os.environ.get('SLURMD_NODENAME'),'cpu_models':models,'platform':platform.platform(),'python':platform.python_version(),'versions':versions,'timeout_seconds_outer':370}
        with a.output.open('x') as f:json.dump(result,f,indent=2)
        print(a.variant,a.seed,status,flush=True)

if __name__=='__main__':main()
