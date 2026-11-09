"""Screen Tier 8's Gray-path cycle anchors on representative Tier 10 blocks."""
import json,sys
from pathlib import Path
from qiskit import QuantumCircuit
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
from submissions.team3.tier08 import modular
from submissions.team3.tier10 import solution,shared_control
from screen import score


def cycle_block(d,p,w=7):
    table=modular.permutation_table(d,p,w);n=modular.dirty_qubit_count(w)
    c=QuantumCircuit(w+1+n);work=tuple(range(1,w+1));dirty=tuple(range(w+1,w+1+n));gate=modular._mcx_template(w).to_gate()
    seen=set()
    for x in range(len(table)):
        if x in seen:continue
        cycle=[];y=x
        while y not in seen:seen.add(y);cycle.append(y);y=table[y]
        assert y==x
        if len(cycle)<2:continue
        anchor=min(cycle,key=lambda a:(sum((a^b).bit_count() for b in cycle),a))
        ix=cycle.index(anchor);order=cycle[ix:]+cycle[:ix]
        for y in order[1:]:modular._append_basis_transposition(c,anchor,y,work,dirty,gate)
    return c

if __name__=='__main__':
    a=solution._public_parameters();p,g=a['p'],a['g'];rows=[]
    for j in range(3):
        d=pow(g,1<<j,p);b=cycle_block(d,p)
        rows.append({'index':j,'cycle':score(b),'existing':score(shared_control.fanout_multiplier(d,p,7))})
    print(json.dumps(rows,indent=2));(ROOT/'research/tier10_structural_v3/cycle_screen.json').write_text(json.dumps(rows,indent=2)+'\n')
