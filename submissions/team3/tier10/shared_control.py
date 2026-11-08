"""Exact Tier 10 shared-predicate synthesis with and without clean ancilla.

The default solver uses the no-ancilla fanout with QFT relabeling.
"""
from itertools import groupby
from operator import itemgetter

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


def fanout_multiplier(d, modulus, work_bits):
    """Exact no-ancilla pivot fanout, independently applied to Tier 10 powers."""
    ops = _compiled_operations(d, modulus, work_bits)
    qc = QuantumCircuit(work_bits + 1)
    for mask, group in groupby(ops, key=itemgetter(0)):
        parity = 0
        for _, target in group:
            parity ^= 1 << target
        targets = [j + 1 for j in range(work_bits) if parity & (1 << j)]
        if not targets:
            continue
        controls = [0] + [j + 1 for j in range(work_bits) if mask & (1 << j)]
        pivot, *others = targets
        for target in others:
            qc.cx(pivot, target)
        qc.append(MCXGate(len(controls)), [*controls, pivot])
        for target in reversed(others):
            qc.cx(pivot, target)
    return qc


def _build_circuit(p, g, A, register_bits, work_bits, *, fanout, relabel):
    t, w = register_bits, work_bits
    qc = QuantumCircuit(2*t+w+(0 if fanout else 1), 2*t)
    work = list(range(2*t, 2*t+w)); anc = 2*t+w
    qc.x(work[0]); qc.h(range(2*t))
    cache = {}
    for base, offset, prefix in ((g,0,'g'),(A,t,'A')):
        for j in range(t):
            d = pow(base, 1 << j, p)
            if d not in cache:
                compiler = fanout_multiplier if fanout else shared_multiplier
                cache[d] = compiler(d,p,w).to_gate()
            gate = cache[d].copy(name=f'tier10_controlled_{prefix}_power_{1 << j}')
            control = offset + (t-1-j if relabel else j)
            qc.append(gate, [control, *work] if fanout else [control, *work, anc])
    qft = build_inverse_qft(t)
    if relabel:
        body = QuantumCircuit(t)
        for item in qft.data:
            if item.operation.name != 'swap':
                body.append(item.operation, [qft.find_bit(q).index for q in item.qubits])
        qft = body
    qft = qft.to_gate()
    qc.append(qft, range(t)); qc.append(qft, range(t, 2*t))
    qc.measure(range(2*t), range(2*t))
    return qc


def shared_circuit(p, g, A, register_bits=6, work_bits=7):
    return _build_circuit(p,g,A,register_bits,work_bits,fanout=False,relabel=False)


def combined_circuit(p, g, A, register_bits=6, work_bits=7):
    return _build_circuit(p,g,A,register_bits,work_bits,fanout=False,relabel=True)


def fanout_circuit(p, g, A, register_bits=6, work_bits=7):
    return _build_circuit(p,g,A,register_bits,work_bits,fanout=True,relabel=False)


def fanout_qft_circuit(p, g, A, register_bits=6, work_bits=7):
    return _build_circuit(p,g,A,register_bits,work_bits,fanout=True,relabel=True)
