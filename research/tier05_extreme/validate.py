"""Official Tier 5 check then five paired seeds in disposable Git snapshots."""
import hashlib,json,sys,subprocess,tempfile,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
HARNESS=ROOT.parent/'Quantum-Cryptography-Benchmark-Harness';sys.path.insert(0,str(HARNESS))
from benchmarks.common import snapshot,run_worker,environment
from benchmarks.cross_seed_regression import status
PATCH='''
# Research-only wrapper in a disposable snapshot; production source is untouched.
_original_build = build_circuit
_original_transpile = transpile
_original_phase = oracle.build_phase_oracle
import json as _json
_config = _json.loads((Path(__file__).resolve().parents[3] / "research/tier05_extreme/candidate.json").read_text())
def build_circuit(*, ciphertext=None, iterations=ITERATIONS):
    from unittest.mock import patch
    from research.tier05_extreme.search import fused_oracle
    with patch.object(oracle, "build_phase_oracle", lambda c: fused_oracle(c, _config["order"], _config["pivot_last"])):
        return _original_build(ciphertext=ciphertext, iterations=iterations)
def transpile(*args, **kwargs):
    kwargs["optimization_level"] = _config["level"]
    return _original_transpile(*args, **kwargs)
'''


def main():
 source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();baseline='c4455782ea9388d5897fc27270f42dd3786ed35d'
 result={'source_commit':source,'baseline_commit':baseline,'harness_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=HARNESS,text=True).strip(),'candidate_sha256':hashlib.sha256((OUT/'candidate.json').read_bytes()).hexdigest(),'wrapper_sha256':hashlib.sha256(PATCH.encode()).hexdigest(),'environment':environment(),'official':{},'paired':[]}
 def save():(OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='tier05-extreme-') as tmp:
  base=Path(tmp)/'baseline';cand=Path(tmp)/'candidate';base.mkdir();cand.mkdir();snapshot(baseline,base);snapshot(source,cand)
  with (cand/'submissions/team3/tier05/solution.py').open('a') as f:f.write(PATCH)
  for label,tree in [('baseline',base),('candidate',cand)]:
   prior=OUT/'validation-attempt1.json'
   if label=='baseline' and prior.exists():
    result['official'][label]=json.loads(prior.read_text())['official']['baseline'];save();continue
   entry=run_worker('official',tree,5,None,370,2048);result['official'][label]=entry;save();print('official',label,entry.get('status'),entry.get('metrics'),flush=True)
   if entry.get('status')!='full':return
  for seed in range(5100,5105):
   for label,tree in [('baseline',base),('candidate',cand)]:
    entry=run_worker('cross',tree,5,seed,120,2048);result['paired'].append({'variant':label,'seed':seed,'status':status(entry),'result':entry});save();print(label,seed,status(entry),entry.get('solve_seconds'),flush=True)
 for label in ('baseline','candidate'):
  rows=[r['result'] for r in result['paired'] if r['variant']==label]
  result.setdefault('summary',{})[label]={'passes':sum(r['status']=='PASS' for r in result['paired'] if r['variant']==label),'mean_solve_seconds':statistics.mean(r['solve_seconds'] for r in rows),'mean_aer_job_seconds':statistics.mean(r['aer_timing']['aer_job_elapsed_seconds'] for r in rows),'mean_sampled_rss_mib':statistics.mean(r['resource']['peak_rss_bytes_sampled']/2**20 for r in rows)}
 save()
if __name__=='__main__':main()
