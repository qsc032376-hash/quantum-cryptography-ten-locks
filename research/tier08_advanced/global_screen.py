"""Bounded screen of fixed-mask elimination with exact dirty MCX templates."""
import sys
from pathlib import Path
from qiskit import QuantumCircuit, transpile
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'submissions')]
from team3.tier08 import modular
from tools.check_submission import compute_metrics


def build(multiplier):
    table=modular.permutation_table(multiplier,35,6)
    values=list(table); ops=[]
    def apply(mask,t):
        assert not mask & (1<<t)
        ops.append((mask,t))
        for i,x in enumerate(values):
            if x & mask == mask: values[i]=x^(1<<t)
    for row in range(64):
        initial=values[row]
        for bit in range(6):
            if row & ~initial & (1<<bit): apply(initial,bit)
        surplus=values[row] & ~row
        for bit in range(6):
            if surplus & (1<<bit): apply(row,bit)
    assert values==list(range(64))
    c=QuantumCircuit(9)
    for mask,t in reversed(ops):
        controls=[0]+[i+1 for i in range(6) if mask & (1<<i)]
        target=t+1
        temp=modular._mcx_template(len(controls))
        needed=temp.num_qubits-len(controls)-1
        available=[i for i in range(1,9) if i!=target and i not in controls]
        if len(available)<needed: raise ValueError((len(controls),needed,len(available)))
        c.append(temp.to_gate(label=f"exact_mcx_{len(controls)}"),controls+[target]+available[:needed])
    return c

if __name__ == '__main__':
    for multiplier in (2,4,11,16):
        c=build(multiplier)
        native=transpile(c,basis_gates=['rz','sx','x','cx'],optimization_level=1,seed_transpiler=12345,num_processes=1)
        scored=transpile(native,basis_gates=['rz','sx','x','cx'],optimization_level=1,seed_transpiler=12345,num_processes=1)
        print(multiplier,compute_metrics(scored),flush=True)
