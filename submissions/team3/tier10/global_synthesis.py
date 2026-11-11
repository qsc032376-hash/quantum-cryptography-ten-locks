"""Exact public mixed-polarity networks from the validated Tier 10 research cache.

No measured secrets are stored. The cached permutations include the full work
space, padding and control-off identity. No extra clean ancilla is assumed.
"""
import json
import itertools
from functools import lru_cache
from pathlib import Path
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

def grouped(ops):
    for (mask,val),run in itertools.groupby(ops,lambda o:o[:2]):
        targets=0
        for _,_,t in run:targets^=1<<t
        if targets:yield mask,val,targets

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

@lru_cache(maxsize=1)
def _operations():
    return json.loads(Path(__file__).with_name("public_operations.json").read_text())["operations"]

def fanout_multiplier(d, modulus, work_bits):
    if modulus != 83 or work_bits != 7:
        raise ValueError("Public cache is validated for modulus 83 and seven work bits")
    return emit(_operations()[str(d)], work_bits)
