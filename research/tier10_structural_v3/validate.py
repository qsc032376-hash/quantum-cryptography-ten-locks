"""Run a candidate only in isolated temporary snapshots; save safe aggregates."""
import json,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HARNESS=ROOT.parent/'Quantum-Cryptography-Benchmark-Harness'
sys.path.insert(0,str(HARNESS))
from benchmarks.common import snapshot,run_worker,environment
from benchmarks.cross_seed_regression import status

REF='be78cc11d6e5e778c2ecfd2d0efa79fe740b3274'
PATCH='''
_original_research_builder = build_circuit

def build_circuit(*, parameters=None):
    import importlib
    from unittest.mock import patch
    from research.tier10_structural_v3.predicate_screen import make_selector
    mod = importlib.import_module(__package__ + ".shared_control")
    with patch.object(mod, "select_operations", make_selector(16)):
        return _original_research_builder(parameters=parameters)
'''

def main():
    with tempfile.TemporaryDirectory(prefix='tier10v3_') as t:
        base=Path(t)/'base';cand=Path(t)/'candidate';base.mkdir();cand.mkdir()
        snapshot(REF,base);snapshot(REF,cand)
        target=cand/'research/tier10_structural_v3';target.mkdir(parents=True)
        for name in ('screen.py','predicate_screen.py'):shutil.copy(ROOT/'research/tier10_structural_v3'/name,target/name)
        with (cand/'submissions/team3/tier10/solution.py').open('a') as f:f.write(PATCH)
        rows=[]
        for seed in (1000,1001,1002):
            for label,tree in (('baseline',base),('candidate',cand)):
                r=run_worker('cross',tree,10,seed,120,1536)
                rows.append({'variant':label,'seed':seed,'status':status(r),'result':r})
                print(label,seed,rows[-1]['status'],flush=True)
        check=run_worker('official',cand,10,None,240,1536)
        print('official',check.get('status'),check.get('hash_ok'),check.get('metrics_status'),check.get('flags'),flush=True)
        output={'baseline_commit':REF,'environment':environment(),'paired':rows,'candidate_official':check}
        (ROOT/'research/tier10_structural_v3/validation.json').write_text(json.dumps(output,indent=2)+'\n')
if __name__=='__main__':main()
