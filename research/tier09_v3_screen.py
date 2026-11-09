"""Bounded public-permutation synthesis screening; no secret outputs."""
import sys, json
from collections import Counter
from itertools import groupby
from operator import itemgetter
from qiskit.circuit.library import MCXGate
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from submissions.team3.tier09 import solution, shared_controls
from submissions.team3.tier08.modular import permutation_table
from tools.check_submission import compute_metrics

original = shared_controls._compiled_operations

def commute(a,b):
    am,at=a; bm,bt=b
    return at==bt or not ((am >> bt)&1 or (bm >> at)&1)

def cancel(ops):
    result=[]
    for op in ops:
        for i in range(len(result)-1,-1,-1):
            if result[i]==op:
                result.pop(i); break
            if not commute(op,result[i]):
                result.append(op); break
        else: result.append(op)
    return tuple(result)

def build_baseline(m,n,w=7):
    c=QuantumCircuit(w+1)
    for mask,group in groupby(shared_controls._compiled_operations(m,n,w),key=itemgetter(0)):
        flips=0
        for _,t in group: flips ^= 1<<t
        targets=[j+1 for j in range(w) if flips>>j&1]
        if not targets: continue
        controls=[0]+[j+1 for j in range(w) if mask>>j&1]
        if len(controls)==1:
            for t in targets: c.cx(0,t)
            continue
        pivot,*others=targets
        for t in others: c.cx(pivot,t)
        c.append(MCXGate(len(controls)),controls+[pivot])
        for t in reversed(others): c.cx(pivot,t)
    return c

def build_anchor(m,n,w):
    table=permutation_table(m,n,w); seen=set(); c=QuantumCircuit(w+1)
    for start in range(len(table)):
        if start in seen: continue
        cycle=[]; x=start
        while x not in seen:
            seen.add(x); cycle.append(x); x=table[x]
        if len(cycle)<2: continue
        anchor=min(cycle,key=lambda x:(sum((x^y).bit_count() for y in cycle),x))
        k=cycle.index(anchor); cycle=cycle[k:]+cycle[:k]
        for end in cycle[1:]:
            path=[anchor]
            for b in range(w):
                if (anchor^end)>>b&1: path.append(path[-1]^(1<<b))
            edges=list(zip(path,path[1:])); edges+=list(reversed(edges[:-1]))
            for a,b in edges:
                t=(a^b).bit_length()-1
                zeros=[j+1 for j in range(w) if j!=t and not (a>>j&1)]
                for z in zeros:c.x(z)
                c.mcx([0]+[j+1 for j in range(w) if j!=t],t+1)
                for z in zeros:c.x(z)
    return c

def score(qc):
    native=transpile(qc,AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2),optimization_level=1,seed_transpiler=12345,num_processes=1)
    basis=transpile(native,basis_gates=['rz','sx','x','cx'],coupling_map=None,initial_layout=None,optimization_level=1,seed_transpiler=12345,num_processes=1)
    return compute_metrics(basis),dict(native.count_ops())

if __name__=='__main__':
    multipliers=sorted({pow(2,1<<j,77) for j in range(14)})
    print('multipliers',multipliers,flush=True)
    for m in multipliers:
        orig=original(m,77,7); new=cancel(orig)
        print('operations',m,len(orig),len(new),dict(Counter(mask.bit_count()+1 for mask,t in orig)),flush=True)
        for name,builder in [('fixed',lambda: build_baseline(m,77,7)),('anchor',lambda: build_anchor(m,77,7))]:
            q=QuantumCircuit(9); q.compose(builder(),range(8),inplace=True)
            metrics,_=score(q); print('component',m,name,json.dumps(metrics),flush=True)
    solution.build_controlled_multiplier=build_baseline
    for name,fn in [('baseline',original),('commutation',lambda m,n,w:cancel(original(m,n,w)))]:
        shared_controls._compiled_operations=fn
        qc=solution.build_circuit(modulus=77)
        metrics,ops=score(qc)
        print('whole',name,json.dumps(metrics),json.dumps(ops),flush=True)
