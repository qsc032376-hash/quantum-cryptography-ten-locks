"""Check exact full-domain predicates and phase-sensitive block simulations."""
import json,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import CXGate,CCXGate,MCXGate
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
from submissions.team3.tier10 import solution,shared_control
from predicate_screen import make_selector,guard_variant

for available in range(128):
    for row in range(available+1):
        for variant in range(16):
            mask=guard_variant(available,row,variant)
            assert mask & available == mask and mask >= row
            assert mask.bit_count()==min(i.bit_count() for i in range(available+1) if i&available==i and i>=row)
params=solution._public_parameters(); p,g,A=(params[k] for k in ('p','g','A'))
selector=make_selector(16);rng=np.random.default_rng(1701);rows=[]
with patch.object(shared_control,'select_operations',selector):
    for index,d in enumerate(pow(base,1<<j,p) for base in (g,A) for j in range(6)):
        circuit=shared_control.fanout_multiplier(d,p,7)
        dest=np.arange(256)
        for item in circuit.data:
            assert isinstance(item.operation,(CXGate,CCXGate,MCXGate))
            q=[circuit.find_bit(bit).index for bit in item.qubits]
            assert item.operation.ctrl_state==(1<<(len(q)-1))-1
            mask=sum(1<<qbit for qbit in q[:-1]);dest^=((dest&mask)==mask).astype(int)<<q[-1]
        x=np.arange(256);work=x>>1
        expected=(np.where(((x&1)==1)&(work<p),(d*work)%p,work)<<1)|(x&1)
        np.testing.assert_array_equal(dest,expected)
        assert len(set(dest.tolist()))==256
        v=rng.normal(size=256)+1j*rng.normal(size=256);v/=np.linalg.norm(v)
        actual=Statevector(v).evolve(circuit).data
        exp=np.zeros(256,dtype=complex);exp[expected]=v
        error=float(np.max(np.abs(actual-exp)));assert error<1e-10
        inverse=Statevector(actual).evolve(circuit.inverse()).data
        inv_error=float(np.max(np.abs(inverse-v)));assert inv_error<1e-10
        rows.append({'block':index,'basis_columns':256,'superposition_error':error,'inverse_error':inv_error})
    c=solution.build_circuit(); measurements=[(c.find_bit(i.qubits[0]).index,c.find_bit(i.clbits[0]).index) for i in c.data if i.operation.name=='measure']
    assert measurements==[(i,i) for i in range(12)]
result={'blocks':rows,'measurement_mapping_preserved':True,'guard_exhaustive_available_lt':128,'guard_variants':16}
print(json.dumps(result,indent=2));(ROOT/'research/tier10_structural_v3/equivalence.json').write_text(json.dumps(result,indent=2)+'\n')
