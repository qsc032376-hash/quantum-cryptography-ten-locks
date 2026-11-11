"""Generic exact public-permutation compiler; adapted from pinned Tier 10 research."""
import itertools
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate
from submissions.team3.tier10 import synthesis

def linear(x,gates):
    for c,t in gates:
        if x>>c&1:x^=1<<t
    return x

def encode(x,perm,flip):
    return sum(((x>>p)&1)<<j for j,p in enumerate(perm))^flip

def network(table,w,perm,flip,inverse,short,affine=()):
    conjugated=[0]*len(table)
    for x,y in enumerate(table):conjugated[linear(x,affine)]=linear(y,affine)
    table=conjugated; enc=[encode(x,perm,flip) for x in range(1<<w)]
    mapped=[0]*len(table)
    for x,y in enumerate(table):mapped[enc[x]]=enc[y]
    if inverse:
        inv=[0]*len(table)
        for x,y in enumerate(mapped):inv[y]=x
        mapped=inv
    ops=synthesis._short_predicates(mapped,short)
    if inverse:ops=ops[::-1]
    # A cube is (positive-or-negative control mask, required-value mask, target).
    return [(sum(1<<perm[j] for j in range(w) if mask>>j&1),
             sum(1<<perm[j] for j in range(w) if mask>>j&1 and not flip>>j&1),perm[t]) for mask,t in ops]

def simplify(ops):
    # Adjacent same-target cubes XOR; complementary cubes merge (ESOP identity).
    out=[]
    for op in ops:
        if out and out[-1]==op:out.pop();continue
        if out and out[-1][0]==op[0] and out[-1][2]==op[2]:
            mask,val,t=op; diff=val^out[-1][1]
            if diff.bit_count()==1:
                out[-1]=(mask^diff,val&(mask^diff),t);continue
        out.append(op)
    return out

def grouped(ops):
    for (mask,val),run in itertools.groupby(ops,lambda o:o[:2]):
        targets=0
        for _,_,t in run:targets^=1<<t
        if targets:yield mask,val,targets

def cost(ops):
    total=0
    for m,v,ts in grouped(ops):
        n=1+m.bit_count(); total+=((1,6,14)[n-1] if n<=3 else 8*n-12)+2*(ts.bit_count()-1)
    return total

def verify(ops,table):
    for x in range(len(table)):
        y=x
        for m,v,t in ops:
            assert not m>>t&1 and v&m==v
            if y&m==v:y^=1<<t
        assert y==table[x]

def emit(ops,w=7,pivot_last=False):
    c=QuantumCircuit(w+1)
    for m,v,ts in grouped(ops):
        targets=[j+1 for j in range(w) if ts>>j&1]
        controls=[0]+[j+1 for j in range(w) if m>>j&1]
        neg=[j+1 for j in range(w) if (m^v)>>j&1]
        if pivot_last:targets.reverse()
        pivot,*other=targets
        for j in neg:c.x(j)
        for j in other:c.cx(pivot,j)
        c.append(MCXGate(len(controls)),controls+[pivot])
        for j in other[::-1]:c.cx(pivot,j)
        for j in neg:c.x(j)
    return c

def block(candidate,w,borrowed=0):
    qc=QuantumCircuit(w+1+borrowed)
    for c,t in candidate['affine']:qc.cx(c+1,t+1)
    qc.compose(emit(candidate['ops'],w),range(w+1),inplace=True)
    for c,t in reversed(candidate['affine']):qc.cx(c+1,t+1)
    return qc
