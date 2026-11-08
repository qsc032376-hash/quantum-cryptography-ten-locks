"""Run only the unmodified official Tier 5 checker on an isolated prototype."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from research.real_circuits.experiments import snapshot, REF58
from research.real_circuits.validate_candidates import install_variant

ROOT=Path(__file__).resolve().parents[2]
PATCH='''
# Research-only adapter in disposable submission copy.
def build_circuit(*, ciphertext=None, iterations=ITERATIONS):
    from types import SimpleNamespace
    from research.tier05_mask_fusion.experiment import build_fused_circuit
    _validate_iterations(iterations)
    if ciphertext is None: ciphertext, _ = _public_inputs()
    return build_fused_circuit(SimpleNamespace(oracle=oracle), ciphertext, iterations)
'''

def main():
    with tempfile.TemporaryDirectory(prefix='tier05-fusion-check-') as d:
        team=snapshot(REF58,d,'fusioncheck')
        install_variant(team,'gf2')
        p=team/'tier05/solution.py'
        with p.open('a') as f: f.write(PATCH)
        out=Path(d)/'report'
        env=dict(os.environ, PYTHONPATH=str(ROOT), OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='1')
        proc=subprocess.run([sys.executable,str(ROOT/'tools/check_submission.py'),str(team),'--out',str(out)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=240)
        file=out/'report.json'
        if not file.exists(): raise RuntimeError(f'Checker returned {proc.returncode} without a report')
        report=json.loads(file.read_text())
        assert set(report['tiers'])=={'5'}
        entry=report['tiers']['5']
        safe={key:entry.get(key) for key in ('status','hash_ok','metrics_status','metrics','flags','solve_seconds','circuits_executed')}
        safe['process_returncode']=proc.returncode
        assert safe['status']=='full' and safe['hash_ok'] is True and safe['metrics_status']=='ok' and not safe['flags']
        print(json.dumps(safe,indent=2))
        (ROOT/'research/tier05_mask_fusion/checker_result.json').write_text(json.dumps(safe,indent=2)+'\n')
if __name__=='__main__': main()
