"""Independent, phase-sensitive audit of the four complete 9-wire blocks."""
import json, sys, time
from pathlib import Path
import numpy as np
from qiskit.quantum_info import Operator
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'submissions'))
from team3.tier08.modular import build_controlled_multiplier

rows=[]
for multiplier in (2,4,11,16):
    started=time.monotonic()
    actual=Operator(build_controlled_multiplier(multiplier,35,6)).data
    # Bit 0 is control, bits 1..6 work, bits 7..8 dirty.
    dest=[]
    for x in range(512):
        control=x&1; value=(x>>1)&63
        result=(multiplier*value)%35 if control and value<35 else value
        dest.append((x & ~126) | (result<<1))
    assert len(set(dest))==512
    expected=np.zeros((512,512),dtype=complex)
    expected[dest,np.arange(512)]=1
    error=float(np.max(np.abs(actual-expected)))
    inverse_error=float(np.max(np.abs(actual.conj().T-expected.T)))
    assert error<1e-9 and inverse_error<1e-9
    rows.append({'multiplier':multiplier,'columns':512,'complete_complex_operator_error':error,'inverse_error':inverse_error,'seconds':round(time.monotonic()-started,3)})
    print(json.dumps(rows[-1]),flush=True)
(ROOT/'research/tier08_osc/audit.json').write_text(json.dumps(rows,indent=2)+'\n')
