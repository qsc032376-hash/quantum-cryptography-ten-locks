"""Reproduce approved public networks and audit the isolated integration tree."""
import ast,hashlib,itertools,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
BASE='c4455782ea9388d5897fc27270f42dd3786ed35d';RESEARCH='7edfe872aec8651ca28e1721ef4e322ba942d113'
def blob(ref,path):return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)
def main():
 from submissions.team3.tier10 import synthesis,solution,global_synthesis
 from submissions.team3.tier08.modular import permutation_table
 from qiskit import QuantumCircuit
 from qiskit.circuit.library import MCXGate
 allow={'submissions/team3/tier07/solution.py','submissions/team3/tier10/shared_control.py'}
 files=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
 changed=[p for p in files if (ROOT/p).read_bytes()!=blob(BASE,p)]
 assert set(changed)==allow,changed
 expected7=blob('556dd7dfc0d080aceec1a519302ba34c5f436eee','submissions/team3/tier07/solution.py')
 assert (ROOT/'submissions/team3/tier07/solution.py').read_bytes()==expected7
 cache=(ROOT/'submissions/team3/tier10/public_operations.json').read_bytes()
 assert cache==blob(RESEARCH,'research/tier10_global/candidate.json')
 source=blob(RESEARCH,'research/tier10_global/search.py').decode();tree=ast.parse(source)
 ns={'synthesis':synthesis,'permutation_table':permutation_table,'itertools':itertools,'QuantumCircuit':QuantumCircuit,'MCXGate':MCXGate}
 names={'encode','network','simplify','grouped','cost','verify','emit'}
 for n in tree.body:
  if isinstance(n,ast.FunctionDef) and n.name in names:exec(compile(ast.Module(body=[n],type_ignores=[]),'approved_research','exec'),ns)
 data=json.loads(cache);par=solution._public_parameters();p=par['p'];w=7
 ds=sorted(map(int,data['operations']))
 selected={str(d):[(m,m,t) for m,t in synthesis.select_operations(d,p,w)] for d in ds}
 search=json.loads(blob(RESEARCH,'research/tier10_global/search.json'));seen=set()
 for config in search['configurations']:
  for d in ds:
   for inv,short in itertools.product((False,True),repeat=2):
    ops=ns['simplify'](ns['network'](d,p,w,config['permutation'],config['xor_mask'],inv,short))
    ns['verify'](ops,permutation_table(d,p,w));fp=hashlib.sha256(repr(ops).encode()).hexdigest()
    if fp in seen:continue
    seen.add(fp)
    if ns['cost'](ops)<ns['cost'](selected[str(d)]):selected[str(d)]=ops
 assert json.loads(json.dumps(selected))==data['operations']
 for d in ds:
  assert global_synthesis.fanout_multiplier(d,p,w)==ns['emit'](data['operations'][str(d)],w)
 hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'submissions/team3').rglob('*')) if f.is_file() and f.suffix in ('.py','.json')}
 result={'baseline':BASE,'tier07_source':'556dd7dfc0d080aceec1a519302ba34c5f436eee','tier10_source':RESEARCH,'changed_existing_files':changed,'all_other_tracked_files_identical':True,'cache_sha256':hashlib.sha256(cache).hexdigest(),'deterministic_regeneration_matches':True,'emitted_circuit_equality':True,'submission_sha256':hashes}
 (Path(__file__).parent/'source-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('source/cache/emitter audit PASS',flush=True)
if __name__=='__main__':main()
