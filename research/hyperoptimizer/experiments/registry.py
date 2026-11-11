"""Reuse immutable prior acceptance evidence; no duplicate quantum runs."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'research/hyperoptimizer/results'
SOURCES={5:('97fcc0c7d6dec3b7385dc237d47d89d4d6ffd15c','research/tier05_extreme/validation.json'),9:('d294a5a6f26b8abe96b1117928f8857e95750040','research/tier09_global/validation.json'),10:('7edfe872aec8651ca28e1721ef4e322ba942d113','research/tier10_global/validation.json')}
def main():
 rows={}
 for tier,(ref,path) in SOURCES.items():
  raw=subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT);data=json.loads(raw)
  entry=data['official_checker'] if tier==9 else data['official']['candidate']
  assert entry['status']=='full' and entry['hash_ok'] and entry['metrics_status']=='ok' and not entry['flags']
  if tier==9:
   pair=data['paired_seeds'];counts={k:sum(bool(r['ok']) for r in records) for k,records in pair.items()}
  else:counts={k:data['summary'][k].get('passes',data['summary'][k].get('passed')) for k in ('baseline','candidate')}
  rows[str(tier)]={'source':ref,'evidence':path,'evidence_sha256':hashlib.sha256(raw).hexdigest(),'metrics':entry['metrics'],'status':'RELIABILITY_VALIDATED','evidence_reused':True,'new_candidate':False,'paired_pass_counts':counts}
 (OUT/'prior-registry.json').write_text(json.dumps(rows,indent=2)+'\n');print('prior evidence verified',flush=True)
if __name__=='__main__':main()
