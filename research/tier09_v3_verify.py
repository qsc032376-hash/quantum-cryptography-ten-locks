"""Exhaustive exact complex operator and inverse checks of public blocks."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from qiskit.quantum_info import Operator
from submissions.team3.tier09.shared_controls import build_controlled_multiplier
from submissions.team3.tier08.modular import permutation_table

for m in sorted({pow(2,1<<j,77) for j in range(14)}):
    table=permutation_table(m,77,7)
    dest=[((table[x>>1]<<1)|1) if x&1 else x for x in range(256)]
    expected=np.zeros((256,256),complex); expected[dest,np.arange(256)]=1
    block=build_controlled_multiplier(m,77,7)
    actual=Operator(block).data
    inv=Operator(block.inverse()).data
    assert np.allclose(actual,expected,atol=1e-12,rtol=0)
    assert np.allclose(inv,expected.conj().T,atol=1e-12,rtol=0)
    print('multiplier',m,'all 256 controlled inputs and inverse exact; max error',float(np.max(np.abs(actual-expected))),flush=True)
