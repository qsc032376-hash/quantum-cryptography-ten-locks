"""Three uncensored unchanged official Checker runs, external read-only observation.

Private circuit payloads are retained temporarily outside the repository for
same-environment comparisons. They are never committed or included in reports.
The official program and submission files are never patched or regenerated.
"""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
import psutil

APPROVED='ce75c0721622d363e77912191a52a02c34f92472'
UPSTREAM='340e1ce18cafa69f4cea906f88f93741738dc0fa'
ZIP_SHA='64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94'


def stamp():return datetime.now(ZoneInfo('America/New_York')).isoformat()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args])


def main():
    p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--evidence',type=Path);a=p.parse_args()
    root=a.repository.resolve();out=(a.evidence or root/'docs/v63-metrics-reconciliation').resolve();out.mkdir(parents=True,exist_ok=True);private=a.private_root.resolve()
    private.mkdir(mode=0o700,parents=True,exist_ok=False)
    report_path=out/'three-runs.json';assert not report_path.exists()
    archive=root/'drafts/ten-locks-team3-v6.3-rc.zip';assert digest(archive)==ZIP_SHA
    manifest=json.loads(git(root,'show',APPROVED+':docs/v63-evidence/zip-manifest.json'))
    env=os.environ.copy();env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',QISKIT_PARALLEL='FALSE',PYTHONHASHSEED='0')
    packages={}
    for name in ('qiskit','qiskit-aer','numpy','pyyaml','scipy','rustworkx','dill','stevedore','psutil'):
        packages[name]=importlib.metadata.version(name)
    assert packages['qiskit']=='2.6.1' and packages['qiskit-aer']=='0.18.2'
    fingerprint={'python':platform.python_version(),'platform':platform.platform(),'machine':platform.machine(),'packages':packages,
                 'environment':{k:env.get(k) for k in ('PYTHONHASHSEED','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','QISKIT_PARALLEL','RAYON_NUM_THREADS')},
                 'python_executable':sys.executable,'python_executable_sha256':digest(Path(sys.executable).resolve()),
                 'checker_sha256':hashlib.sha256(git(root,'show',UPSTREAM+':tools/check_submission.py')).hexdigest(),
                 'config_sha256':hashlib.sha256(git(root,'show',UPSTREAM+':tools/scoring_config.yaml')).hexdigest()}
    report={'approved_commit':APPROVED,'official_commit':UPSTREAM,'zip_sha256':ZIP_SHA,'started_at':stamp(),
            'planned_runs':3,'retry_policy':'Exactly three sequential scheduled runs; all results retained, no retry or replacement.',
            'fixed_environment':fingerprint,'checker_or_submission_patched':False,'simulator_seed_overridden':False,
            'circuit_capture':'External observer copies completed official input files seen in actual --_transpile worker argv; does not patch the Checker.',
            'capture_targets':[5,6,7],'private_payloads_committed':False,'runs':[]}
    def save():report_path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for run in range(1,4):
        target=out/f'run-{run}';target.mkdir();fresh=private/f'official-{run}';fresh.mkdir()
        # New official tree from original upstream Git object, no team workspace reused.
        archive_proc=subprocess.Popen(['git','-C',str(root),'archive',UPSTREAM],stdout=subprocess.PIPE)
        extracted=subprocess.run(['tar','-x','-C',str(fresh)],stdin=archive_proc.stdout,check=True)
        archive_proc.stdout.close();assert archive_proc.wait()==0
        assert not (fresh/'submissions/team3').exists()
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None and set(z.namelist())==set(manifest['contents'])
            z.extractall(fresh/'submissions')
        assert all(digest(fresh/'submissions'/name)==h for name,h in manifest['contents'].items())
        capture=private/f'captured-{run}';capture.mkdir(mode=0o700)
        command=[sys.executable,'-I','tools/check_submission.py','submissions/team3','--out',str(target/'checker')]
        entry={'run':run,'started_at':stamp(),'command':command,'cwd':str(fresh),'captured_tiers':{},'same_environment':True}
        report['runs'].append(entry);save();print('START run',run,flush=True)
        started=time.monotonic();peak=0;resource_state='ok';observed_argv={}
        with (private/f'run-{run}.log').open('wb') as log:
            proc=subprocess.Popen(command,cwd=fresh,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            parent=psutil.Process(proc.pid)
            while proc.poll() is None:
                try:family=[parent]+parent.children(recursive=True)
                except psutil.NoSuchProcess:family=[]
                memory=0
                for child in family:
                    try:
                        memory+=child.memory_info().rss;argv=child.cmdline()
                        if '--_transpile' not in argv:continue
                        idx=argv.index('--_transpile');source=Path(argv[idx+1]);tier=int(source.stem.replace('tier',''))
                        if tier not in (5,6,7) or str(tier) in entry['captured_tiers']:continue
                        payload=source.read_bytes();head,body=payload.split(b'\n',1);sizes=json.loads(head)
                        if len(body)!=sum(sizes):continue
                        (capture/f'tier{tier:02d}.circuits').write_bytes(payload)
                        os.chmod(capture/f'tier{tier:02d}.circuits',0o600)
                        # Only safe process metadata persists; no private QPY digests or bytes.
                        entry['captured_tiers'][str(tier)]={'captured':True,'unique_records':len(sizes),
                            'origin':'actual official scoring worker input','complete_framing':True,
                            'worker_python_hash_seed':child.environ().get('PYTHONHASHSEED'),
                            'worker_qiskit_parallel':child.environ().get('QISKIT_PARALLEL'),
                            'worker_isolated_flag_present':'-I' in argv,'private_payload_persisted_in_git':False}
                        save()
                    except (psutil.NoSuchProcess,psutil.AccessDenied,FileNotFoundError,ValueError,IndexError):continue
                peak=max(peak,memory)
                if peak>8*1024**3 or time.monotonic()-started>1800:
                    resource_state='memory_limit' if peak>8*1024**3 else 'outer_timeout'
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
                    break
                time.sleep(.01)
            code=proc.wait()
        entry.update({'finished_at':stamp(),'exit_code':code,'resource_state':resource_state,
                      'wall_seconds':time.monotonic()-started,'sampled_peak_process_tree_rss_mib':peak/2**20,
                      'sample_period_ms':10,'official_solve_timeout_s':120,'official_transpile_timeout_s':120,
                      'submission_bytes_unchanged':all(digest(fresh/'submissions'/name)==h for name,h in manifest['contents'].items()),
                      'checker_unchanged':digest(fresh/'tools/check_submission.py')==fingerprint['checker_sha256'],
                      'scoring_config_unchanged':digest(fresh/'tools/scoring_config.yaml')==fingerprint['config_sha256'],
                      'archive_unchanged':digest(archive)==ZIP_SHA})
        official=target/'checker/report.json'
        if official.exists():
            data=json.loads(official.read_text());entry['official_report_sha256']=digest(official)
            entry['tiers']=data['tiers'];entry['totals']={k:sum((v.get('metrics') or {}).get(k,0) for v in data['tiers'].values()) for k in ('two_qubit_gates','depth','total_gates')}
            entry['all_required_checks_pass']=len(data['tiers'])==10 and all(v['status']=='full' and v['hash_ok'] and v['circuit_executed'] and v['metrics_status']=='ok' and not v['flags'] for v in data['tiers'].values())
        else:entry['all_required_checks_pass']=False
        save();print('FINISH run',run,'pass',entry['all_required_checks_pass'],'totals',entry.get('totals'),flush=True)
        if resource_state!='ok':
            report['stopped_reason']='Resource failure; no retry and no additional large runs';save();return 1
    report['finished_at']=stamp();report['completed_runs']=len(report['runs']);save()
    return 0 if all(x['all_required_checks_pass'] for x in report['runs']) else 1

if __name__=='__main__':raise SystemExit(main())
