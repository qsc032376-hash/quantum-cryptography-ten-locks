"""Execute the unchanged official CLI once, with external resource observation."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import psutil


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--official-root',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--private-log',type=Path,required=True)
    a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'checker').exists():raise RuntimeError('Refusing to overwrite previous Checker evidence')
    env=os.environ.copy();env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',QISKIT_PARALLEL='FALSE')
    command=[sys.executable,'-I','tools/check_submission.py','submissions/team3','--out',str(out/'checker')]
    packages={}
    for name in ('qiskit','qiskit-aer','numpy','pyyaml','psutil','matplotlib','pylatexenc','notebook','ipykernel'):
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    assert tuple(sys.version_info[:2])==(3,12)
    for name,version in {'qiskit':'2.6.1','qiskit-aer':'0.18.2','numpy':'2.5.4','pyyaml':'6.0.3'}.items():assert packages[name]==version
    start=time.monotonic();peak=0;state='ok';stamp=datetime.now(ZoneInfo('America/New_York')).isoformat()
    with a.private_log.open('wb') as log:
        proc=subprocess.Popen(command,cwd=a.official_root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        ps=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:
                family=[ps]+ps.children(recursive=True)
                memory=0
                for child in family:
                    try:memory+=child.memory_info().rss
                    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                peak=max(peak,memory)
            except psutil.NoSuchProcess:pass
            if peak>8*1024**3 or time.monotonic()-start>2700:
                state='external_memory_limit' if peak>8*1024**3 else 'external_wall_timeout'
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
                break
            time.sleep(.02)
        code=proc.wait()
    result={'started_at':stamp,'finished_at':datetime.now(ZoneInfo('America/New_York')).isoformat(),
            'command':command,'cwd':str(a.official_root.resolve()),'exit_code':code,'resource_state':state,
            'wall_seconds':time.monotonic()-start,'sampled_process_tree_peak_rss_bytes':peak,
            'sampled_process_tree_peak_rss_mib':peak/2**20,'sample_period_ms':20,
            'resource_note':'Sampled sum of process RSS can miss peaks or double-count shared pages.',
            'outer_wall_limit_seconds':2700,'outer_memory_limit_mib':8192,
            'official_solve_timeout_seconds':120,'official_transpile_timeout_seconds':120,
            'official_startup_grace_seconds':60,'official_limits_modified':False,
            'python':platform.python_version(),'executable':sys.executable,'platform':platform.platform(),
            'packages':packages,'thread_environment':{k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','QISKIT_PARALLEL')},
            'checker_patched':False,'submission_patched':False,'simulation_seed_overridden':False,
            'optional_notebook_plotting_components_required':False}
    (out/'execution.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('exit_code','resource_state','wall_seconds','sampled_process_tree_peak_rss_mib')}),flush=True)
    if code or state!='ok':raise SystemExit(1)

if __name__=='__main__':main()
