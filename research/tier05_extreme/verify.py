"""Clean-subspace phase, restoration, arbitrary-work oracle and Grover checks."""
import json,time
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit.quantum_info import Operator
from qiskit.circuit.library import RCCXGate
from qiskit_aer import AerSimulator
from search import *
from common.toy_cipher import mask as classical_mask,ToyCipher

def evolve(c,vector):
 sim=AerSimulator(method='statevector',max_memory_mb=1024,max_parallel_threads=2)
 native=transpile(c,sim,optimization_level=1,seed_transpiler=12345,num_processes=1)
 phase=float(native.global_phase);native.global_phase=0
 qc=QuantumCircuit(19);qc.set_statevector(vector);qc.compose(native,inplace=True);qc.save_statevector()
 # Aer applies circuit-global phase before set_statevector, which overwrites it.
 # Strip metadata before simulation and restore the known phase, never fit it.
 return np.exp(1j*phase)*np.asarray(sim.run(qc).result().get_statevector())

def main():
 started=time.perf_counter();cfg=json.loads((OUT/'candidate.json').read_text());ciphertext,_=solution._public_inputs();rng=np.random.default_rng(20261111)
 # Exhaustive Boolean check of fused mask transition without keeping key values.
 for key in range(1024):
  c=transition(cfg.get('order',0),cfg.get('pivot_last',False));x=key
  for ins in c.data:
   wires=[c.find_bit(q).index for q in ins.qubits]
   assert ins.operation.name in ('cx','rccx')
   if all(x>>j&1 for j in wires[:-1]):x^=1<<wires[-1]
  expect=classical_mask(key,0,10)^classical_mask(key,1,10)^oracle.helper.ROUND_CONSTANT
  assert x==key|(expect<<10)
 # The primitive is an exact monomial with the classical Toffoli permutation.
 op=Operator(RCCXGate()).data;perm=np.arange(8);perm[3],perm[7]=7,3
 assert np.max(np.abs(np.abs(op)-np.eye(8)[perm]))<1e-12
 base=oracle.build_phase_oracle(ciphertext)
 candidate=fused_oracle(ciphertext,cfg.get('order',0),cfg.get('pivot_last',False)) if cfg.get('fused') else phase_oracle(ciphertext,cfg['relative_mask'],cfg['relative_compare'])
 v=np.zeros(1<<19,complex);v[:1024]=rng.normal(size=1024)+1j*rng.normal(size=1024);v/=np.linalg.norm(v)
 # All key inputs have nonzero amplitudes; expected phases use public cipher definition.
 expect=v.copy()
 for key in range(1024):
  if ToyCipher(key,10).decrypt(ciphertext[:2])==b'QC':expect[key]*=-1
 actual=evolve(candidate,v);phase_error=float(np.max(np.abs(actual-expect)));leak=float(np.sum(np.abs(actual[1024:])**2));assert phase_error<1e-10 and leak<1e-15
 random=rng.normal(size=1<<19)+1j*rng.normal(size=1<<19);random/=np.linalg.norm(random)
 arbitrary_error=float(np.max(np.abs(evolve(base,random)-evolve(candidate,random))));assert arbitrary_error<1e-10
 b=solution.build_circuit();c=build_config(cfg);assert solution.count_oracle_calls(c)==25
 assert [(c.find_bit(i.qubits[0]).index,c.find_bit(i.clbits[0]).index) for i in c.data if i.operation.name=='measure']==[(i,i) for i in range(10)]
 init=np.zeros(1<<19,complex);init[0]=1
 bnative=compile_actual(b,{'level':1,'gf2':True})[1].remove_final_measurements(inplace=False)
 cnative=compile_actual(c,cfg)[1].remove_final_measurements(inplace=False)
 grover_error=float(np.max(np.abs(evolve(bnative,init)-evolve(cnative,init))));print('compiled full-state raw error',grover_error,flush=True)
 out={'boolean_keys_checked':1024,'relative_toffoli_complex_operator_checked':True,'clean_subspace_phase_max_error':phase_error,'workspace_leak_probability':leak,'arbitrary_workspace_oracle_state_error':arbitrary_error,'full_25_iteration_compiled_state_error':grover_error,'phase_fitting':False,'iterations':25,'measurement_mapping_preserved':True,'seconds':time.perf_counter()-started,'limitation':'Finite statevectors plus monomial/conjugation argument; not full 19-qubit dense operator proof. Boolean expected phases used only in tests, never solver.'}
 (OUT/'equivalence.json').write_text(json.dumps(out,indent=2)+'\n');print(out,flush=True);assert grover_error<1e-9
if __name__=='__main__':main()
