import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from research.hyperoptimizer.verification.operators import verify_block
from research.hyperoptimizer.experiments.tier08 import builder
from submissions.team3.tier08 import solution
from submissions.team3.tier08.modular import permutation_table
OUT=ROOT/'research/hyperoptimizer/results'
def main():
 selected=json.loads((OUT/'tier08-candidate.json').read_text())['blocks'];records=[]
 for d,candidate in selected.items():records.append({'multiplier':int(d),**verify_block(candidate,permutation_table(int(d),35,6),6)})
 c=builder(selected);assert c.num_qubits==18
 assert [(c.find_bit(i.qubits[0]).index,c.find_bit(i.clbits[0]).index) for i in c.data if i.operation.name=='measure']==[(i,i) for i in range(12)]
 sim=AerSimulator(method='statevector',max_parallel_threads=2,max_memory_mb=512);states=[]
 for circ in (solution.build_circuit(),c):
  circ=circ.remove_final_measurements(inplace=False);circ.save_statevector();native=transpile(circ,sim,optimization_level=1,seed_transpiler=12345,num_processes=1);states.append(np.asarray(sim.run(native).result().get_statevector()))
 error=float(np.max(np.abs(states[0]-states[1])));assert error<1e-10
 data={'blocks':records,'prepared_18qubit_state_error':error,'phase_fitted':False,'borrowed_wires':'two declared idle wires are untouched by the source block; compiler exact MCX contracts apply','measurement_mapping_preserved':True}
 (OUT/'tier08-equivalence.json').write_text(json.dumps(data,indent=2)+'\n');print(data,flush=True)
if __name__=='__main__':main()
