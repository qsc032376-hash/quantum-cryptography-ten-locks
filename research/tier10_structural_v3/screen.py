"""Screen dirty-MCX implementation of the exact executed Tier 10 circuit."""
import json,sys,time
from pathlib import Path
from collections import Counter
from qiskit import QuantumCircuit,transpile
from qiskit.synthesis import synth_mcx_n_dirty_m15
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from submissions.team3.tier10 import solution
from tools.check_submission import compute_metrics,load_config


def rewrite(circuit):
    """Borrow three count wires other than each block's external control."""
    out=circuit.copy_empty_like(); counts=Counter()
    for item in circuit.data:
        wires=[circuit.find_bit(q).index for q in item.qubits]
        cbits=[circuit.find_bit(c).index for c in item.clbits]
        if not item.operation.name.startswith('tier10_controlled_'):
            out.append(item.operation,wires,cbits); continue
        control=wires[0]; dirty=[i for i in range(12) if i!=control][:3]
        block=item.operation.definition
        alt=QuantumCircuit(block.num_qubits+3)
        for sub in block.data:
            idx=[block.find_bit(q).index for q in sub.qubits]
            n=getattr(sub.operation,'num_ctrl_qubits',0)
            if n>=4:
                template=synth_mcx_n_dirty_m15(n)
                needed=template.num_qubits-n-1
                assert needed <=3
                alt.compose(template,idx+list(range(block.num_qubits,block.num_qubits+needed)),inplace=True)
                counts[n]+=1
            else:alt.append(sub.operation,idx)
        out.append(alt.to_gate().copy(name=item.operation.name),wires+dirty)
    return out,dict(counts)


def score(c):
    sim=AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2)
    native=transpile(c,sim,optimization_level=1,seed_transpiler=12345,num_processes=1)
    cfg=load_config();settings={k:cfg[k] for k in ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')}
    return compute_metrics(transpile(native,**settings))

if __name__=='__main__':
    started=time.perf_counter(); original=solution.build_circuit(); changed,hist=rewrite(original)
    results={'baseline':score(original),'candidate':score(changed),'dirty_mcx_histogram':hist,'seconds':round(time.perf_counter()-started,3)}
    print(json.dumps(results,indent=2));(ROOT/'research/tier10_structural_v3/screen.json').write_text(json.dumps(results,indent=2)+'\n')
