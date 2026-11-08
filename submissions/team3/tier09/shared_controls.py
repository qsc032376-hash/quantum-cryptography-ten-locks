"""Exact fan-out synthesis for consecutive rows of the public Tier 9 permutation."""
from itertools import groupby
from operator import itemgetter

from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

from .global_permutation import _compiled_operations


def build_controlled_multiplier(multiplier, modulus, work_bits=7):
    operations = _compiled_operations(multiplier, modulus, work_bits)
    circuit = QuantumCircuit(1 + work_bits, name="tier09_controlled_modular_multiply")
    for mask, group in groupby(operations, key=itemgetter(0)):
        # Same-condition flips commute; matching pairs cancel exactly.
        flips = 0
        for _, target in group:
            flips ^= 1 << target
        targets = [bit + 1 for bit in range(work_bits) if flips & (1 << bit)]
        if not targets:
            continue
        controls = [0] + [bit + 1 for bit in range(work_bits) if mask & (1 << bit)]
        gate = MCXGate(len(controls))
        if len(controls) == 1:
            for target in targets:
                circuit.cx(0, target)
            continue
        # F X_p F also flips all secondary targets. F uses only work targets,
        # so it commutes with the condition and cancels on the disabled branch.
        pivot, *others = targets
        for target in others:
            circuit.cx(pivot, target)
        circuit.append(gate, [*controls, pivot])
        for target in reversed(others):
            circuit.cx(pivot, target)
    return circuit
