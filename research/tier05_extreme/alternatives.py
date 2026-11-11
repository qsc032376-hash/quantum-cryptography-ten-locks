"""Bounded exact small-block SMT, phase-polynomial and component probes."""
import json,time,itertools
import numpy as np
from qiskit.quantum_info import Operator
from search import *

def phase_windows(circuit):
 out=circuit.copy_empty_like();pending=[];count=0;saved=0
 def flush():
  nonlocal count,saved
  if not pending:return
  wires=sorted({circuit.find_bit(q).index for i in pending for q in i.qubits});n=len(wires)
  if n>5:
   for i in pending:out.append(i)
   pending.clear();return
  rows=[1<<j for j in range(n)];angles={};block=QuantumCircuit(n)
  for i in pending:
   qs=[wires.index(circuit.find_bit(q).index) for q in i.qubits];block.append(i.operation,qs)
   if i.operation.name=='cx':rows[qs[1]]^=rows[qs[0]]
   else:angles[rows[qs[0]]]=angles.get(rows[qs[0]],0)+float(i.operation.params[0])
  alt=QuantumCircuit(n)
  for mask,angle in angles.items():
   if abs(angle)<1e-14:continue
   qs=[j for j in range(n) if mask>>j&1];pivot=qs[-1]
   for j in qs[:-1]:alt.cx(j,pivot)
   alt.rz(angle,pivot)
   for j in reversed(qs[:-1]):alt.cx(j,pivot)
  mat=np.array([[(r>>j)&1 for j in range(n)] for r in rows],dtype=np.uint8);alt.compose(gf2_synthesis.synthesize(mat),inplace=True)
  before=block.count_ops().get('cx',0);after=alt.count_ops().get('cx',0)
  if after<before:
   assert np.max(np.abs(Operator(block).data-Operator(alt).data))<1e-10
   count+=1;saved+=before-after;out.compose(alt,wires,inplace=True)
  else:
   for i in pending:out.append(i)
  pending.clear()
 for i in circuit.data:
  if i.operation.name in ('rz','cx'):pending.append(i)
  else:flush();out.append(i)
 flush();return out,{'accepted_windows':count,'cx_removed_before_rescoring':saved}

def smt_probe():
 import z3
 # Exact three-wire CNOT network, unrelated to key values. Repeated pattern
 # appears in linear compute/uncompute optimization; solver provides optimum.
 reference=QuantumCircuit(3);reference.cx(0,1);reference.cx(1,2);reference.cx(0,1);reference.cx(0,2)
 mat=gf2_synthesis.extract_matrix(reference);desired=[sum(int(v)<<j for j,v in enumerate(row)) for row in mat]
 trials=[];gates=list(itertools.permutations(range(3),2))
 for depth in range(4):
  solver=z3.Solver();solver.set(timeout=2000);choices=[z3.Int(f'g{k}') for k in range(depth)];rows=[z3.BitVecVal(1<<j,3) for j in range(3)]
  for choice in choices:
   solver.add(choice>=0,choice<6);new=[]
   for j in range(3):
    row=rows[j]
    for index,(control,target) in enumerate(gates):
     if target==j:row=z3.If(choice==index,rows[j]^rows[control],row)
    new.append(row)
   rows=new
  solver.add(*[row==value for row,value in zip(rows,desired)]);status=solver.check();trials.append({'length':depth,'status':str(status)})
  if status==z3.sat:
   model=solver.model();qc=QuantumCircuit(3)
   for choice in choices:qc.cx(*gates[model.eval(choice).as_long()])
   assert np.array_equal(gf2_synthesis.extract_matrix(qc),mat)
   return {'z3':z3.get_version_string(),'trials':trials,'original_cx':4,'optimal_cx':depth,'operator_error':float(np.max(np.abs(Operator(reference).data-Operator(qc).data))),'scope':'synthetic safe linear block only; not integrated or claimed as extra circuit savings'}
 return {'trials':trials}

def main():
 cfg=json.loads((OUT/'candidate.json').read_text());res,native=compile_actual(build_config(cfg),cfg);changed,stats=phase_windows(native)
 scored=transpile(changed,basis_gates=solution.BASIS_GATES,optimization_level=1,seed_transpiler=12345,num_processes=1)
 ciphertext,_=solution._public_inputs();parts={}
 for name,c in [('baseline_oracle',oracle.build_phase_oracle(ciphertext)),('candidate_oracle',fused_oracle(ciphertext,cfg.get('order',0),cfg.get('pivot_last',False))),('diffuser',oracle.build_diffuser())]:
  compiled=transpile(c,basis_gates=solution.BASIS_GATES,optimization_level=1,seed_transpiler=12345,num_processes=1);parts[name]=compute_metrics(compiled)
 data={'component_costs_nonadditive':parts,'phase_polynomial_probe':{'stats':stats,'whole_metrics':compute_metrics(scored),'promotion':'not promoted; finalist remains selected search configuration'},'smt':smt_probe(),'ancillas':'19 total; 6 existing key wires borrowed dirty by relative comparator, restored; diffuser uses clean work only after oracle restoration'}
 (OUT/'alternatives.json').write_text(json.dumps(data,indent=2)+'\n');print(data,flush=True)
if __name__=='__main__':main()
