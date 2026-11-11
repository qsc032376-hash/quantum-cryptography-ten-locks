"""Full-domain phase checks and 19-qubit statevectors; outputs aggregates only."""
import json,time
import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator
from search import OUT,solution,emit,builder,permutation_table

def main():
    t=time.perf_counter();selected=json.loads((OUT/'candidate.json').read_text())['operations']
    par=solution._public_parameters(); rows=[]
    for index,(d,ops) in enumerate(selected.items()):
        c=emit(ops);mat=Operator(c).data
        dest=np.arange(256);work=dest>>1
        expected=(np.where(((dest&1)==1)&(work<par['p']),(int(d)*work)%par['p'],work)<<1)|(dest&1)
        ideal=np.zeros((256,256),complex);ideal[expected,np.arange(256)]=1
        err=float(np.max(np.abs(mat-ideal)));inv=float(np.max(np.abs(Operator(c.inverse()).data-ideal.T)))
        assert err<1e-10 and inv<1e-10
        rows.append({'block_index':index,'basis_columns':256,'complex_operator_error':err,'inverse_error':inv})
    base=solution.build_circuit();cand=builder(selected)
    assert [(cand.find_bit(i.qubits[0]).index,cand.find_bit(i.clbits[0]).index) for i in cand.data if i.operation.name=='measure']==[(i,i) for i in range(12)]
    sim=AerSimulator(method='statevector',max_parallel_threads=2,max_memory_mb=1024)
    errors=[]
    for label in ('prepared','random_input'):
        vectors=[];rng=np.random.default_rng(20261111)
        random=rng.normal(size=1<<19)+1j*rng.normal(size=1<<19);random/=np.linalg.norm(random)
        for circuit in (base,cand):
            c=circuit.remove_final_measurements(inplace=False)
            if label=='random_input':
                from qiskit import QuantumCircuit
                pre=QuantumCircuit(19);pre.set_statevector(random);pre.compose(c,inplace=True);c=pre
            c.save_statevector();native=transpile(c,sim,optimization_level=1,seed_transpiler=12345,num_processes=1)
            vectors.append(np.asarray(sim.run(native).result().get_statevector()))
        err=float(np.max(np.abs(vectors[0]-vectors[1])));assert err<1e-10
        errors.append({'input':label,'absolute_amplitude_error':err,'phase_fitting':False})
    (OUT/'equivalence.json').write_text(json.dumps({'controlled_modules':rows,'full_19_qubit_statevectors':errors,'measurement_mapping_preserved':True,'seconds':time.perf_counter()-t},indent=2)+'\n')
    print('equivalence PASS',errors,flush=True)
if __name__=='__main__':main()
