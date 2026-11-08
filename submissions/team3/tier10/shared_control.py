"""Experimental Tier 10 clean-ancilla shared-control implementation.

This is a separately selectable candidate, not used by the default solver.
"""
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate
from ..tier09.modular import _compiled_operations
from ..tier07.qpe import build_inverse_qft


def shared_multiplier(d, modulus, work_bits):
    ops = _compiled_operations(d, modulus, work_bits)
    qc = QuantumCircuit(work_bits + 2)
    anc = work_bits + 1
    i = 0
    while i < len(ops):
        mask, target = ops[i]
        targets = [target]
        j = i + 1
        while j < len(ops) and ops[j][0] == mask and ops[j][1] not in targets:
            targets.append(ops[j][1]); j += 1
        controls = [0] + [bit + 1 for bit in range(work_bits) if mask & (1 << bit)]
        if len(targets) >= 3:
            qc.append(MCXGate(len(controls)), [*controls, anc])
            for t in targets:
                qc.cx(anc, t + 1)
            qc.append(MCXGate(len(controls)), [*controls, anc])
        else:
            for t in targets:
                qc.append(MCXGate(len(controls)), [*controls, t + 1])
        i = j
    return qc


def shared_circuit(p, g, A, register_bits=6, work_bits=7):
    t, w = register_bits, work_bits
    qc = QuantumCircuit(2*t+w+1, 2*t)
    work = list(range(2*t, 2*t+w)); anc = 2*t+w
    qc.x(work[0]); qc.h(range(2*t))
    cache = {}
    for base, offset, prefix in ((g,0,'g'),(A,t,'A')):
        for j in range(t):
            d = pow(base, 1 << j, p)
            if d not in cache:
                cache[d] = shared_multiplier(d,p,w).to_gate()
            gate = cache[d].copy(name=f'tier10_controlled_{prefix}_power_{1 << j}')
            qc.append(gate, [offset+j, *work, anc])
    qft = build_inverse_qft(t).to_gate()
    qc.append(qft, range(t)); qc.append(qft, range(t, 2*t))
    qc.measure(range(2*t), range(2*t))
    return qc
