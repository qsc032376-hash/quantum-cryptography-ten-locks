"""Targeted unchanged-baseline replay to investigate observed metric differences."""
import io,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.check_submission import check_tier,load_config
from common import load_hashes
BASE='c4455782ea9388d5897fc27270f42dd3786ed35d'
with tempfile.TemporaryDirectory(prefix='v61-baseline-diagnostic-') as tmp:
 with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',BASE],cwd=ROOT))) as ar:ar.extractall(tmp,filter='data')
 results={}
 for tier in (6,7):
  results[str(tier)]=check_tier(tier,Path(tmp)/f'submissions/team3/tier{tier:02d}/solution.py',load_config(),load_hashes()[tier],False)
  print('baseline diagnostic',tier,results[str(tier)]['metrics'],flush=True)
 (Path(__file__).parent/'baseline-diagnostics.json').write_text(json.dumps({'baseline':BASE,'tiers':results},indent=2)+'\n')
