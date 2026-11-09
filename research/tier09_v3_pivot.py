"""Screen exact alternate fan-out pivots and standalone components."""
import sys,json
from pathlib import Path
from itertools import groupby
from operator import itemgetter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate
from submissions.team3.tier09 import solution,shared_controls
from submissions.team3.tier07.qpe import build_inverse_qft
from research.tier09_v3_screen import score, build_baseline

def builder(m,n,w=7):
    c=QuantumCircuit(w+1)
    for mask,group in groupby(shared_controls._compiled_operations(m,n,w),key=itemgetter(0)):
        flips=0
        for _,t in group: flips^=1<<t
        targets=[j+1 for j in range(w) if flips>>j&1]
        if not targets: continue
        controls=[0]+[j+1 for j in range(w) if mask>>j&1]
        if len(controls)==1:
            for t in targets:c.cx(0,t)
            continue
        pivot=targets[-1]; others=targets[:-1]
        for t in others:c.cx(pivot,t)
        c.append(MCXGate(len(controls)),controls+[pivot])
        for t in reversed(others):c.cx(pivot,t)
    return c

if __name__=='__main__':
    for m in sorted({pow(2,1<<j,77) for j in range(14)}):
        for name,fn in [('baseline',build_baseline),('last_pivot',builder)]:
            q=QuantumCircuit(9); q.compose(fn(m,77,7),range(8),inplace=True)
            print('component',m,name,json.dumps(score(q)[0]),flush=True)
    solution.build_controlled_multiplier=builder
    print('whole last_pivot',json.dumps(score(solution.build_circuit(modulus=77))[0]),flush=True)
    q=QuantumCircuit(22,14);q.append(build_inverse_qft(14).to_gate(),range(14));q.measure(range(14),range(14))
    print('inverse_qft',json.dumps(score(q)[0]),flush=True)
