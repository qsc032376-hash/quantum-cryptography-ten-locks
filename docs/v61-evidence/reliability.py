"""Focused paired Aer-seed validation, safe aggregate output only."""
import argparse,hashlib,importlib,json,os,platform,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
BASE='c4455782ea9388d5897fc27270f42dd3786ed35d'

def worker(tree,tier,seed):
 sys.path.insert(0,tree)
 import qiskit,qiskit_aer
 from qiskit_aer.backends.aerbackend import AerBackend
 from common import is_correct
 mod=importlib.import_module(f'submissions.team3.tier{tier:02d}.solution')
 original=mod.transpile;backend_run=AerBackend.run;seen=[];compile_seconds=0.0
 def timed(*a,**kw):
  nonlocal compile_seconds
  t=time.perf_counter()
  try:return original(*a,**kw)
  finally:compile_seconds+=time.perf_counter()-t
 def seeded(self,*a,**kw):
  actual=seed+len(seen);kw['seed_simulator']=actual
  seen.append({'seed':actual,'shots':kw.get('shots')})
  return backend_run(self,*a,**kw)
 mod.transpile=timed;AerBackend.run=seeded
 t=time.perf_counter();error=None;ok=False
 try:ok=bool(is_correct(tier,mod.solve()))
 except Exception as e:error=type(e).__name__
 elapsed=time.perf_counter()-t
 print(json.dumps({'hash_ok':ok,'solve_seconds':elapsed,'compilation_seconds':compile_seconds,'actual_forwarded_calls':seen,'exception_class':error,'python':platform.python_version(),'qiskit':qiskit.__version__,'aer':qiskit_aer.__version__}))

def trial(tree,tier,seed):
 import psutil
 env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='2',QISKIT_PARALLEL='FALSE',PYTHONHASHSEED='0')
 start=time.perf_counter();peak=0;state='ok'
 with tempfile.TemporaryFile() as output:
  proc=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(tree),str(tier),str(seed)],cwd=tree,env=env,stdout=output,stderr=subprocess.DEVNULL)
  parent=psutil.Process(proc.pid)
  while proc.poll() is None:
   try:
    children=[parent,*parent.children(recursive=True)];rss=sum(p.memory_info().rss for p in children if p.is_running());peak=max(peak,rss)
    if time.perf_counter()-start>120 or rss>2*1024**3:
     state='timeout' if time.perf_counter()-start>120 else 'memory_limit'
     for p in reversed(children):
      try:p.kill()
      except psutil.Error:pass
     break
   except psutil.Error:pass
   time.sleep(.02)
  proc.wait();output.seek(0)
  try:result=json.load(output)
  except Exception:result={'exception_class':'MissingWorkerResult'}
 result.update(resource_state=state,wall_seconds=time.perf_counter()-start,sampled_peak_rss_mib=peak/1024**2)
 calls=result.get('actual_forwarded_calls',[])
 passed=state=='ok' and proc.returncode==0 and result.get('hash_ok') and not result.get('exception_class') and result.get('solve_seconds',121)<120 and calls and [c['seed'] for c in calls]==list(range(seed,seed+len(calls)))
 result['status']='PASS' if passed else 'FAIL';return result

def main():
 report=json.loads((OUT/'full-checker/report.json').read_text())
 assert len(report['tiers'])==10 and all(t['status']=='full' and t['hash_ok'] and t['circuit_executed'] and t['metrics_status']=='ok' and not t['flags'] for t in report['tiers'].values())
 audit=json.loads((OUT/'source-audit.json').read_text())
 for path,digest in audit['submission_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
 result={'baseline':BASE,'candidate_submission_tree':report['sha'],'source_manifest':'source-audit.json','pairs':[],'sampling':'20 ms summed process-tree RSS','environment':{'python':platform.python_version(),'platform':platform.platform()}}
 with tempfile.TemporaryDirectory(prefix='v61-focused-') as tmp:
  import tarfile,io
  base=Path(tmp)/'baseline';base.mkdir()
  data=subprocess.check_output(['git','archive',BASE],cwd=ROOT)
  with tarfile.open(fileobj=io.BytesIO(data)) as archive:archive.extractall(base,filter='data')
  candidate=Path(tmp)/'candidate';shutil.copytree(base,candidate)
  shutil.rmtree(candidate/'submissions/team3');shutil.copytree(ROOT/'submissions/team3',candidate/'submissions/team3',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  # Neither run can depend on a research source tree.
  for tree in (base,candidate):shutil.rmtree(tree/'research',ignore_errors=True)
  for tier,seeds in ((7,range(7100,7103)),(10,range(10100,10105))):
   for seed in seeds:
    for label,tree in (('baseline',base),('candidate',candidate)):
     entry=trial(tree,tier,seed);result['pairs'].append({'tier':tier,'seed':seed,'variant':label,**entry})
     (OUT/'reliability.json').write_text(json.dumps(result,indent=2)+'\n');print(tier,seed,label,entry['status'],flush=True)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--worker':worker(sys.argv[2],int(sys.argv[3]),int(sys.argv[4]))
 else:main()
