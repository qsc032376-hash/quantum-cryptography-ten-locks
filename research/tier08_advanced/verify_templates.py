"""Exhaustive complex operators for all actual exact dirty MCX templates."""
import json,sys
from pathlib import Path
import numpy as np
from qiskit.quantum_info import Operator
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'submissions'))
from team3.tier08 import modular
rows=[]
for n in range(1,7):
    c=modular._mcx_template(n)
    u=Operator(c).data
    N=len(u); expected=np.zeros_like(u)
    for x in range(N):
        y=x^((1<<n) if x&((1<<n)-1)==(1<<n)-1 else 0)
        expected[y,x]=1
    error=float(np.max(np.abs(u-expected)))
    assert error < 1e-10
    rows.append({'controls':n,'total_qubits':c.num_qubits,'basis_columns':N,'max_complex_error':error})
print(json.dumps(rows,indent=2))
(ROOT/'research/tier08_advanced/templates.json').write_text(json.dumps(rows,indent=2)+'\n')
