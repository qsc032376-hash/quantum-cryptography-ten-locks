"""Isolated official Checker and ten matched seeds, with bounded memory/time."""
import json,sys,tempfile,subprocess,hashlib,shutil,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'research/hyperoptimizer/results'
HARNESS=ROOT.parent/'Quantum-Cryptography-Benchmark-Harness'
sys.path.insert(0,str(HARNESS))
from benchmarks.common import snapshot,run_worker,environment
from benchmarks.cross_seed_regression import status
PATCH='''
_original_multiplier = build_controlled_multiplier

def build_controlled_multiplier(d, modulus, work_bits):
    import json
    from pathlib import Path
    from research.hyperoptimizer.synthesis.permutations import block
    if modulus != 35 or work_bits != 6:
        raise ValueError("Validated Tier 8 public instance required")
    path = Path(__file__).resolve().parents[3] / "research/hyperoptimizer/results/tier08-candidate.json"
    selected = json.loads(path.read_text())["blocks"]
    return block(selected[str(d)], work_bits, borrowed=dirty_qubit_count(work_bits))
'''

def main():
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    harness_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HARNESS,text=True).strip()
    assert harness_sha=='ab9676749e00da904d0b8076811a2407d3b7205f'
    result={'source_commit':source,'baseline_commit':'c4455782ea9388d5897fc27270f42dd3786ed35d','harness_commit':harness_sha,'environment':environment(),'candidate_sha256':hashlib.sha256((OUT/'tier08-candidate.json').read_bytes()).hexdigest(),'wrapper_sha256':hashlib.sha256(PATCH.encode()).hexdigest(),'official':{},'paired':[]}
    def save():(OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='hyper-tier08-') as tmp:
        base=Path(tmp)/'base';cand=Path(tmp)/'candidate';base.mkdir();cand.mkdir()
        # Harness repository shares Git objects with these worktrees.
        snapshot(result['baseline_commit'],base);snapshot(source,cand)
        with (cand/'submissions/team3/tier08/solution.py').open('a') as f:f.write(PATCH)
        for label,tree in [('baseline',base),('candidate',cand)]:
            entry=run_worker('official',tree,8,None,370,2048)
            result['official'][label]=entry;save()
            print('official',label,entry.get('status'),entry.get('metrics'),flush=True)
            if entry.get('status')!='full':return
        for seed in range(8100,8105):
            for label,tree in [('baseline',base),('candidate',cand)]:
                entry=run_worker('cross',tree,8,seed,120,2048)
                result['paired'].append({'variant':label,'seed':seed,'status':status(entry),'result':entry});save()
                print(label,seed,status(entry),entry.get('solve_seconds'),flush=True)
    dims=('two_qubit_gates','depth','total_gates','active_qubits')
    for label in ('baseline','candidate'):
        rows=[r['result'] for r in result['paired'] if r['variant']==label]
        result.setdefault('summary',{})[label]={'passed':sum(r['status']=='PASS' for r in result['paired'] if r['variant']==label),'mean_solve_seconds':statistics.mean(r['solve_seconds'] for r in rows),'mean_sampled_peak_rss_mib':statistics.mean(r['resource']['peak_rss_bytes_sampled']/2**20 for r in rows)}
    save()
if __name__=='__main__':main()
