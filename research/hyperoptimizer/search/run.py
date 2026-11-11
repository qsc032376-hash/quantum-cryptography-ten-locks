"""Budget: 36 deterministic coordinates; three full screens, one finalist."""
import sys,json,time,random,hashlib,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from research.hyperoptimizer.synthesis.permutations import network,simplify,cost,linear
from research.hyperoptimizer.cost.official import score
from research.hyperoptimizer.experiments.tier08 import builder
from submissions.team3.tier08.modular import permutation_table
OUT=ROOT/'research/hyperoptimizer/results'
def main():
 checkpoint=OUT/'search-checkpoint.json';candidate_path=OUT/'tier08-candidate.json'
 if '--fresh' not in sys.argv and checkpoint.exists() and candidate_path.exists():
  saved=json.loads(checkpoint.read_text())
  if len(saved.get('configs',[]))==36 and saved.get('candidate_sha256')==hashlib.sha256(candidate_path.read_bytes()).hexdigest():
   print('Verified completed content-addressed checkpoint; use --fresh to regenerate');return
 start=time.perf_counter();rng=random.Random(20261112);selected={};seen=set();trials=[];screens=[];cache={}
 ds=sorted({pow(2,1<<j,35) for j in range(12)})
 for index in range(36):
  perm=list(range(6));rng.shuffle(perm);flip=rng.randrange(64)
  affine=[] if index<24 else [rng.sample(range(6),2) for _ in range(1+(index%2))]
  config={'index':index,'permutation':perm,'xor_mask':flip,'affine':affine}
  for d in ds:
   table=permutation_table(d,35,6)
   for inv,short in itertools.product((False,True),repeat=2):
    key=hashlib.sha256(json.dumps([table,config,inv,short],sort_keys=True).encode()).hexdigest()
    ops=simplify(network(table,6,perm,flip,inv,short,affine));candidate={'ops':ops,'affine':affine}
    fp=hashlib.sha256(json.dumps(candidate,sort_keys=True).encode()).hexdigest()
    if fp in seen:continue
    seen.add(fp)
    for x in range(64):
     y=linear(x,affine)
     for m,v,t in ops:
      if y&m==v:y^=1<<t
     assert linear(y,affine[::-1])==table[x]
    proxy=cost(ops)+2*len(affine);cache[key]={'fingerprint':fp,'proxy':proxy}
    if str(d) not in selected or proxy<selected[str(d)]['proxy']:selected[str(d)]={**candidate,'proxy':proxy,'configuration':config}
  trials.append(config)
  if index in (11,23,35):
   result={'prefix':index+1,**score(builder(selected))};screens.append(result);print(result,flush=True)
   if len(screens)==1 or result['metrics']['two_qubit_gates']<min(x['metrics']['two_qubit_gates'] for x in screens[:-1]):
    (OUT/'tier08-candidate.json').write_text(json.dumps({'blocks':selected,'screen':result},indent=2)+'\n')
  (OUT/'search-checkpoint.json').write_text(json.dumps({'seed':20261112,'configs':trials,'cache':cache,'screens':screens,'seconds':time.perf_counter()-start,'candidate_sha256':hashlib.sha256((OUT/'tier08-candidate.json').read_bytes()).hexdigest()},indent=2)+'\n')
if __name__=='__main__':main()
