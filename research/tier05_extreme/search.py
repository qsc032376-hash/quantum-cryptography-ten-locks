"""Bounded phase-safe Grover resynthesis. No classical key search."""
import hashlib,itertools,json,sys,time,io
from qiskit import qpy
from pathlib import Path
from unittest.mock import patch
from qiskit import QuantumCircuit,transpile
from qiskit.circuit.library import RCCXGate
from qiskit.synthesis import synth_mcx_n_dirty_i15
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));OUT=Path(__file__).parent
from submissions.team3.tier05 import oracle,solution,gf2_synthesis
from common.toy_cipher import inverse_permute,inverse_sbox_layer
from tools.check_submission import compute_metrics,load_config

def mask(index,relative):
 c=oracle._build_mask_transform(index)
 if not relative:return c
 result=c.copy_empty_like()
 for item in c.data:
  result.append(RCCXGate() if item.operation.name=='ccx' else item.operation,[c.find_bit(q).index for q in item.qubits])
 return result

def phase_oracle(ciphertext,relative_mask=True,relative_compare=True):
 targets=tuple(ciphertext[i]^((oracle.helper.ROUND_CONSTANT*i)%256)^inverse_sbox_layer(inverse_permute(b)) for i,b in enumerate(b'QC'))
 u=mask(0,relative_mask);v=mask(1,relative_mask)
 exact,wires=oracle._dirty_comparison_gate()
 if relative_compare:
  template=synth_mcx_n_dirty_i15(8,relative_phase=True,action_only=False)
  dirty=template.num_qubits-9
  first_gate=template.to_gate();first_wires=oracle.WORK_QUBITS+(oracle.FLAG_QUBIT,)+oracle.KEY_QUBITS[:dirty]
 else:first_gate,first_wires=exact,wires
 first=QuantumCircuit(19);first.compose(u,inplace=True);oracle._comparison_x(first,targets[0]);first.append(first_gate,first_wires);oracle._comparison_x(first,targets[0]);first.compose(u.inverse(),inplace=True)
 result=QuantumCircuit(19,name=oracle.ORACLE_NAME);result.compose(first,inplace=True);result.compose(v,inplace=True);oracle._comparison_x(result,targets[1]);result.h(18);result.append(exact,wires);result.h(18);oracle._comparison_x(result,targets[1]);result.compose(v.inverse(),inplace=True);result.compose(first.inverse(),inplace=True)
 return result

def build(config):
 with patch.object(oracle,'build_phase_oracle',lambda c:phase_oracle(c,config['relative_mask'],config['relative_compare'])):return solution.build_circuit()

_SCORE_CACHE = {}

def compile_actual(c,config):
 buffer=io.BytesIO();qpy.dump(c,buffer)
 fingerprint=hashlib.sha256(buffer.getvalue()+json.dumps(config,sort_keys=True).encode()).hexdigest()
 if fingerprint in _SCORE_CACHE:return _SCORE_CACHE[fingerprint]
 t=time.perf_counter();sim=AerSimulator(method='statevector',max_parallel_threads=2,max_memory_mb=512)
 native=transpile(c,sim,basis_gates=solution.BASIS_GATES,optimization_level=config.get('level',1),seed_transpiler=12345,num_processes=1)
 stats={}
 if config.get('gf2',True):native,stats,_=gf2_synthesis.gf2_runs(native)
 native_seconds=time.perf_counter()-t
 cfg=load_config();scored=transpile(native,**{k:cfg[k] for k in ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')},num_processes=1)
 result=({'fingerprint':fingerprint,'metrics':compute_metrics(scored),'compile_seconds':time.perf_counter()-t,'native_compile_seconds':native_seconds,'gf2':stats},native)
 _SCORE_CACHE[fingerprint]=result
 return result

def main():
 rows=[];configs=[];seen=set()
 # Eight fundamental configurations, plus GF(2)-disabled screens of the best shape.
 for rm,rc,level in itertools.product((False,True),(False,True),(1,2)):
  config={'relative_mask':rm,'relative_compare':rc,'level':level,'gf2':True};c=build(config)
  metrics,native=compile_actual(c,config)
  row={'config':config,**metrics};rows.append(row);print(config,metrics['metrics'],flush=True)
 best=min(rows,key=lambda r:r['metrics']['two_qubit_gates'])
 for level,gf2 in ((3,True),(1,False),(2,False)):
  cfg={**best['config'],'level':level,'gf2':gf2};metrics,native=compile_actual(build(cfg),cfg);rows.append({'config':cfg,**metrics});print(cfg,metrics['metrics'],flush=True)
 best=min(rows,key=lambda r:r['metrics']['two_qubit_gates'])
 (OUT/'candidate.json').write_text(json.dumps(best['config'],indent=2)+'\n')
 (OUT/'search.json').write_text(json.dumps({'baseline_commit':'c4455782ea9388d5897fc27270f42dd3786ed35d','seed_transpiler':12345,'iterations':25,'shots':128,'screens':rows,'selected':best},indent=2)+'\n')

# Exact Boolean coordinate map of mask0 XOR mask1, emitted as a relative-phase
# monomial ONLY inside A; diagonal marking is followed by the actual A inverse.
def transition(order=0,pivot_last=False):
 terms={}
 for index in (0,1):
  shift=3*index
  for op,*idx in oracle.helper.mask_gates(10):
   controls=tuple(sorted((j-shift)%10 for j in idx[:-1]));target=10+idx[-1]
   terms[controls]=terms.get(controls,0)^(1<<target)
 groups=[(cs,[j for j in range(10,18) if bits>>j&1]) for cs,bits in terms.items() if bits]
 groups.sort(key=lambda pair:(len(pair[0]),pair[0]),reverse=bool(order))
 c=QuantumCircuit(19)
 for controls,targets in groups:
  if pivot_last:targets.reverse()
  p,*others=targets
  for t in others:c.cx(p,t)
  if len(controls)==1:c.cx(controls[0],p)
  else:c.append(RCCXGate(),[*controls,p])
  for t in reversed(others):c.cx(p,t)
 return c

def fused_oracle(ciphertext,order=0,pivot_last=False):
 targets=tuple(ciphertext[i]^((oracle.helper.ROUND_CONSTANT*i)%256)^inverse_sbox_layer(inverse_permute(b)) for i,b in enumerate(b'QC'))
 a=mask(0,True);oracle._comparison_x(a,targets[0])
 rel=synth_mcx_n_dirty_i15(8,relative_phase=True,action_only=False)
 a.append(rel.to_gate(),oracle.WORK_QUBITS+(18,)+oracle.KEY_QUBITS[:rel.num_qubits-9]);oracle._comparison_x(a,targets[0]);a.compose(transition(order,pivot_last),inplace=True);oracle._comparison_x(a,targets[1])
 exact,wires=oracle._dirty_comparison_gate();c=QuantumCircuit(19,name=oracle.ORACLE_NAME);c.compose(a,inplace=True);c.h(18);c.append(exact,wires);c.h(18);c.compose(a.inverse(),inplace=True);return c

def build_config(config):
 fn=(lambda c:fused_oracle(c,config.get('order',0),config.get('pivot_last',False))) if config.get('fused') else (lambda c:phase_oracle(c,config['relative_mask'],config['relative_compare']))
 with patch.object(oracle,'build_phase_oracle',fn):return solution.build_circuit()

def fused_search():
 data=json.loads((OUT/'search.json').read_text())
 for order,last in itertools.product((0,1),(False,True)):
  config={'fused':True,'order':order,'pivot_last':last,'level':2,'gf2':True}
  result,_=compile_actual(build_config(config),config);data['screens'].append({'config':config,**result});print(config,result['metrics'],flush=True)
 data['selected']=min(data['screens'],key=lambda r:(r['metrics']['two_qubit_gates'],r['metrics']['depth'],r['metrics']['total_gates']))
 (OUT/'candidate.json').write_text(json.dumps(data['selected']['config'],indent=2)+'\n');(OUT/'search.json').write_text(json.dumps(data,indent=2)+'\n')

if __name__=="__main__":
 main()
 fused_search()
