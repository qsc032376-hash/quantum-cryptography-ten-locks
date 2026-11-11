"""Phase-sensitive exact comparisons: controlled branches are not phase-fitted."""
import numpy as np
from qiskit.quantum_info import Operator
from research.hyperoptimizer.synthesis.permutations import block

def verify_block(candidate,table,w):
 c=block(candidate,w);dim=1<<(w+1);ideal=np.zeros((dim,dim),complex)
 for x in range(dim):
  dest=(table[x>>1]<<1)|1 if x&1 else x
  ideal[dest,x]=1
 actual=Operator(c).data;inverse=Operator(c.inverse()).data
 error=float(np.max(np.abs(actual-ideal)));inv=float(np.max(np.abs(inverse-ideal.T)))
 if max(error,inv)>1e-10:raise ValueError('controlled operator/phase mismatch')
 return {'columns':dim,'forward_error':error,'inverse_error':inv,'global_phase_fitted':False}
