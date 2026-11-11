"""Bounded exact conjugated-permutation synthesis; never reads secret data."""
import sys,json,time,random,hashlib,itertools,platform,subprocess
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit.circuit.library import MCXGate
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from submissions.team3.tier10 import solution,shared_control,synthesis
from submissions.team3.tier08.modular import permutation_table
from tools.check_submission import compute_metrics,load_config
OUT=Path(__file__).parent

def encode(x,perm,flip):
    return sum(((x>>p)&1)<<j for j,p in enumerate(perm))^flip

def network(d,p,w,perm,flip,inverse,short):
    table=permutation_table(d,p,w); enc=[encode(x,perm,flip) for x in range(1<<w)]
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
    # All gates are exact X controlled by a Boolean cube: no conditional phase.

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

def builder(selected,last=False):
    def multiplier(d,p,w):return emit(selected[str(d)],w,last)
    with patch.object(shared_control,'fanout_multiplier',multiplier):return solution.build_circuit()

def score(c,level=1):
    t=time.perf_counter();sim=AerSimulator(method='statevector',max_parallel_threads=2)
    native=transpile(c,sim,optimization_level=level,seed_transpiler=12345,num_processes=1)
    cfg=load_config();opts={k:cfg[k] for k in ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')}
    scored=transpile(native,**opts,num_processes=1)
    return {'metrics':compute_metrics(scored),'compilation_seconds':time.perf_counter()-t,'native_ops':dict(native.count_ops())}

def main():
    started=time.perf_counter();par=solution._public_parameters();p=par['p'];w=7
    ds=sorted({pow(base,1<<j,p) for base in (par['g'],par['A']) for j in range(6)})
    selected={str(d):[(m,m,t) for m,t in synthesis.select_operations(d,p,w)] for d in ds}
    original=solution.build_circuit(); rows=[{'name':'baseline','config':{},**score(original)}]
    print('baseline',rows[-1]['metrics'],flush=True)
    rng=random.Random(20261111); configs=[(list(range(w)),0)]
    for k in range(95):
        perm=list(range(w));rng.shuffle(perm);configs.append((perm,0 if k<47 else rng.randrange(128)))
    fingerprints=set(); trials=[]; bests=[]
    for index,(perm,flip) in enumerate(configs):
        for d in ds:
            for inv,short in itertools.product((False,True),repeat=2):
                ops=simplify(network(d,p,w,perm,flip,inv,short));verify(ops,permutation_table(d,p,w))
                fp=hashlib.sha256(repr(ops).encode()).hexdigest()
                if fp in fingerprints:continue
                fingerprints.add(fp)
                value=cost(ops)
                if value<cost(selected[str(d)]):selected[str(d)]=ops
        trials.append({'index':index,'permutation':perm,'xor_mask':flip,'aggregate_proxy':sum(cost(v) for v in selected.values())})
        if index in (0,7,15,31,47,63,95):
            name=f'prefix_{index+1}';snap=json.loads(json.dumps(selected));bests.append((name,snap))
            row={'name':name,'config':{'prefix':index+1},**score(builder(snap))};rows.append(row)
            print(name,row['metrics'],flush=True)
    best=min(rows[1:],key=lambda r:r['metrics']['two_qubit_gates']);chosen=dict(bests)[best['name']]
    for last in (True,):
        row={'name':'last_pivot','config':{'pivot_last':last},**score(builder(chosen,last))};rows.append(row)
        print(row['name'],row['metrics'],flush=True)
    # Compare native compilation optimization while official scorer stays at level 1.
    # Only level 1 candidates are eligible for the unchanged-solver validation path.
    best=min(rows[1:-1],key=lambda r:r['metrics']['two_qubit_gates']);chosen=dict(bests)[best['name']]
    (OUT/'candidate.json').write_text(json.dumps({'name':best['name'],'operations':chosen},indent=2)+'\n')
    dims=('two_qubit_gates','depth','total_gates','active_qubits')
    frontier=[r['name'] for r in rows if not any(all(s['metrics'][k]<=r['metrics'][k] for k in dims) and s['compilation_seconds']<=r['compilation_seconds'] and (any(s['metrics'][k]<r['metrics'][k] for k in dims) or s['compilation_seconds']<r['compilation_seconds']) for s in rows if s is not r)]
    hist=Counter()
    for item in original.data:
        if item.operation.name.startswith('tier10_controlled'):
            for gate in item.operation.definition.data:hist[(gate.operation.name,getattr(gate.operation,'num_ctrl_qubits',0))]+=1
    (OUT/'search.json').write_text(json.dumps({'baseline_commit':'c4455782ea9388d5897fc27270f42dd3786ed35d','seed':20261111,'python':platform.python_version(),'configurations':trials,'unique_networks':len(fingerprints),'screens':rows,'resource_compile_frontier':frontier,'logical_cost_histogram':{str(k):v for k,v in hist.items()},'seconds':time.perf_counter()-started},indent=2)+'\n')

if __name__=='__main__':main()
