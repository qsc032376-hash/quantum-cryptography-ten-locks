"""One bounded, unchanged official Checker run on the exact v6.3.1 archive."""
import argparse, hashlib, importlib.metadata, io, json, os, platform, signal, stat, subprocess, sys, time, zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo
import psutil
APPROVED='2fe40b2d096d87875244d5ccbb8a76ef979ac499'
OLD='ce75c0721622d363e77912191a52a02c34f92472'
UPSTREAM='340e1ce18cafa69f4cea906f88f93741738dc0fa'
ZIP_SHA='4f1b2de8c7b554bed75319ab7f965937bad85906aa11a26172f5573dc24dfb52'
ZIP_PATH='drafts/ten-locks-team3-v6.3.1-docs.zip'
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(p):return sha(p.read_bytes())
def stamp():return datetime.now(ZoneInfo('America/New_York')).isoformat()
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args])
def main():
 p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);a=p.parse_args();root=a.repository.resolve();private=a.private_root.resolve();out=root/'docs/v631-independent-audit';result=out/'independent-checker.json'
 assert not result.exists();private.mkdir(parents=True,mode=0o700,exist_ok=False)
 archive=root/ZIP_PATH;raw=archive.read_bytes();assert sha(raw)==ZIP_SHA and raw==git(root,'show',APPROVED+':'+ZIP_PATH)
 old=git(root,'show',OLD+':drafts/ten-locks-team3-v6.3-rc.zip')
 with zipfile.ZipFile(io.BytesIO(old)) as z:expected_names=z.namelist()
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  names=z.namelist();assert z.testzip() is None and len(names)==len(set(names))==37 and names==expected_names
  for info in z.infolist():
   q=PurePosixPath(info.filename);assert not q.is_absolute() and q.parts[0]=='team3' and '..' not in q.parts and '\\' not in info.filename and ':' not in info.filename and not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16)
  manifest={n:sha(z.read(n)) for n in names};assert all(z.read(n)==git(root,'show',APPROVED+':submissions/'+n) for n in names)
 fresh=private/'official';fresh.mkdir();proc=subprocess.Popen(['git','-C',str(root),'archive',UPSTREAM],stdout=subprocess.PIPE);subprocess.run(['tar','-x','-C',str(fresh)],stdin=proc.stdout,check=True);proc.stdout.close();assert proc.wait()==0
 protected={name:digest(fresh/name) for name in git(root,'ls-tree','-r','--name-only',UPSTREAM).decode().splitlines()};assert not (fresh/'submissions/team3').exists()
 with zipfile.ZipFile(archive) as z:z.extractall(fresh/'submissions')
 assert all(digest(fresh/'submissions'/name)==h for name,h in manifest.items())
 env=dict(os.environ,PYTHONHASHSEED='0',QISKIT_PARALLEL='FALSE',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()};assert importlib.metadata.version('qiskit')=='2.6.1' and importlib.metadata.version('qiskit-aer')=='0.18.2'
 command=[sys.executable,'-I','tools/check_submission.py','submissions/team3','--out',str(out/'checker')]
 data={'candidate_commit':APPROVED,'official_upstream_commit':UPSTREAM,'zip_path':ZIP_PATH,'zip_sha256':ZIP_SHA,'started_at':stamp(),'planned_runs':1,'retry_policy':'One scheduled complete run; no retry, no replacement or selection.','command':command,'cwd':str(fresh),'environment':{'python':platform.python_version(),'python_build':platform.python_build(),'platform':platform.platform(),'packages':dict(sorted(packages.items())),'python_executable_sha256':digest(Path(sys.executable).resolve()),'variables':{k:env.get(k) for k in ('PYTHONHASHSEED','QISKIT_PARALLEL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','RAYON_NUM_THREADS')}},'checker_sha256':protected['tools/check_submission.py'],'scoring_config_sha256':protected['tools/scoring_config.yaml'],'official_files_before':protected,'archive_member_hashes':manifest,'worker_observations':{},'official_checker_or_production_patched':False,'aer_seed_overridden':False}
 def save():result.write_text(json.dumps(data,indent=2)+'\n')
 save();started=time.monotonic();peak=0;stop=None
 with (private/'checker.log').open('wb') as log:
  proc=subprocess.Popen(command,cwd=fresh,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);parent=psutil.Process(proc.pid)
  while proc.poll() is None:
   rss=0
   try:family=[parent]+parent.children(recursive=True)
   except psutil.NoSuchProcess:family=[]
   for child in family:
    try:
     rss+=child.memory_info().rss;argv=child.cmdline()
     for phase in ('--_solve','--_transpile'):
      if phase in argv:
       key=f'{child.pid}:{phase}'
       if key not in data['worker_observations']:
        variables=child.environ();data['worker_observations'][key]={'phase':phase,'python_hash_seed':variables.get('PYTHONHASHSEED'),'qiskit_parallel':variables.get('QISKIT_PARALLEL'),'isolated_flag_present':'-I' in argv}
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
   peak=max(peak,rss)
   if peak>8*1024**3 or time.monotonic()-started>1800:
    stop='rss_limit' if peak>8*1024**3 else 'outer_timeout';os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
    break
   time.sleep(.02)
  code=proc.wait()
 data.update(finished_at=stamp(),exit_code=code,stop_reason=stop,wall_seconds=time.monotonic()-started,sampled_peak_process_tree_rss_mib=peak/2**20,sample_period_ms=20,official_files_after={name:digest(fresh/name) for name in protected},member_hashes_after={name:digest(fresh/'submissions'/name) for name in manifest},zip_sha256_after=digest(archive))
 data['official_files_unchanged']=data['official_files_after']==protected;data['all_37_extracted_members_unchanged']=data['member_hashes_after']==manifest;data['zip_unchanged']=data['zip_sha256_after']==ZIP_SHA
 report=out/'checker/report.json'
 if report.exists():
  official=json.loads(report.read_text());tiers=official['tiers'];data['official_report_sha256']=digest(report);data['tiers']=tiers;data['totals']={k:sum((v.get('metrics') or {}).get(k,0) for v in tiers.values()) for k in ('two_qubit_gates','depth','total_gates')};data['all_required_checks_pass']=len(tiers)==10 and all(v['status']=='full' and v['hash_ok'] and v['circuit_executed'] and v['metrics_status']=='ok' and not v['flags'] for v in tiers.values())
 else:data['all_required_checks_pass']=False
 data['passed']=data['all_required_checks_pass'] and code==0 and stop is None and data['official_files_unchanged'] and data['all_37_extracted_members_unchanged'] and data['zip_unchanged'];save();print(json.dumps({k:data[k] for k in ('passed','exit_code','stop_reason','wall_seconds','sampled_peak_process_tree_rss_mib','totals')}),flush=True)
 return 0 if data['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
