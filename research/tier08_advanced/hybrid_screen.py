"""Phase-sensitive full-domain comparison of exact mixed synthesis options."""
import json,sys
from pathlib import Path
from functools import lru_cache
import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Statevector
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'submissions'),str(Path(__file__).resolve().parent)]
from team3.tier08 import modular,solution
from tools.check_submission import compute_metrics
from global_screen import build
from verify import classical_execute, baseline, native

@lru_cache(None)
def cost(n):
    return native(modular._mcx_template(n)).count_ops().get('cx',0)

def weighted(c):
    total=0
    for item in c.data:
        if item.operation.name=='x':continue
        label=item.operation.label
        n=6 if label=='exact_mcx6_dirty' else int(label.removeprefix('exact_mcx_'))
        total+=cost(n)
    return total


def run():
    rng=np.random.default_rng(804); rows=[]
    def best(multiplier,modulus,width=6):
        original=modular.build_controlled_multiplier(multiplier,modulus,width)
        if (modulus,width)!=(35,6): return original
        alt=build(multiplier)
        return alt if weighted(alt)<weighted(original) else original
    for a in (2,4,11,16):
        original=baseline.build_controlled_multiplier(a,35)
        candidate=best(a,35)
        table=modular.permutation_table(a,35,6)
        for x in range(512):
            y=x
            for item in candidate.data:
                q=[candidate.find_bit(w).index for w in item.qubits]
                if item.operation.name=='x':y^=1<<q[0]
                else:
                    label=item.operation.label
                    n=6 if label=='exact_mcx6_dirty' else int(label.removeprefix('exact_mcx_'))
                    if all(y & (1<<i) for i in q[:n]):y^=1<<q[n]
            expected=(x & ~126) | ((table[(x>>1)&63] if x&1 else (x>>1)&63)<<1)
            assert y==expected
        v=rng.normal(size=512)+1j*rng.normal(size=512);v/=np.linalg.norm(v)
        err=float(np.max(np.abs(Statevector(v).evolve(original).data-Statevector(v).evolve(candidate).data)))
        assert err<1e-10
        rows.append({'a':a,'cost':weighted(candidate),'basis_branches':512,'max_error':err,'metrics':compute_metrics(native(native(candidate)))})
    solution.build_controlled_multiplier=best
    full=compute_metrics(native(native(solution.build_circuit(modulus=35))))
    data={'blocks':rows,'full':full};print(json.dumps(data,indent=2));(ROOT/'research/tier08_advanced/hybrid_screen.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':run()
