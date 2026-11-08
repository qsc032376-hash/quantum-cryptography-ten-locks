"""Conservative exact cancellations; no phase-modulo or opaque-gate inference."""

import math
from qiskit.circuit.library import (
    XGate, YGate, ZGate, HGate, SGate, SdgGate, TGate, TdgGate,
    RXGate, RYGate, RZGate, PhaseGate, CXGate, CZGate, SwapGate,
)

SELF_INVERSE = {XGate, YGate, ZGate, HGate, CXGate, CZGate, SwapGate}
ROTATIONS = {RXGate, RYGate, RZGate, PhaseGate}
DIAGONAL = {ZGate, SGate, SdgGate, TGate, TdgGate, RZGate, PhaseGate, CZGate}
PAIRS = {SGate: SdgGate, SdgGate: SGate, TGate: TdgGate, TdgGate: TGate}
KNOWN = SELF_INVERSE | ROTATIONS | set(PAIRS)


def kind(item):
    op = item.operation
    cls = op.base_class
    if cls not in KNOWN or item.clbits:
        return None
    if cls in (CXGate, CZGate) and op.ctrl_state != 1:
        return None
    if cls in ROTATIONS:
        try:
            if not math.isfinite(float(op.params[0])):
                return None
        except (TypeError, ValueError):
            return None
    return cls


def inverse_pair(first, second):
    a, b = kind(first), kind(second)
    if a is None or b is None or first.qubits != second.qubits:
        return False
    if a in SELF_INVERSE:
        return a is b
    if a in PAIRS:
        return PAIRS[a] is b
    # Deliberately no mod 2*pi rule: RX(2*pi) is -I, not I.
    return a is b and float(first.operation.params[0]) == -float(second.operation.params[0])


def commute(first, second):
    a, b = kind(first), kind(second)
    if a is None or b is None:
        return False
    if set(first.qubits).isdisjoint(second.qubits):
        return True
    if a in DIAGONAL and b in DIAGONAL:
        return True
    if a is CXGate and b is CXGate:
        c, t = first.qubits
        d, u = second.qubits
        return c != u and d != t
    if b is CXGate and len(first.qubits) == 1:
        if a in (XGate, RXGate):
            return first.qubits[0] == second.qubits[1]
        if a in DIAGONAL:
            return first.qubits[0] == second.qubits[0]
    if a is CXGate and len(second.qubits) == 1:
        return commute(second, first)
    return False


def cancel_inverses(circuit):
    """Move a gate left only through proven commuters to cancel its inverse.

    Measurements, reset, barriers, custom gates, symbols and control flow
    are hard boundaries. Global phase and all quantum/classical wire labels
    are retained. No clean or dirty ancilla assumption is made.
    """
    remaining = []
    removed = 0
    for item in circuit.data:
        for index in range(len(remaining) - 1, -1, -1):
            previous = remaining[index]
            if inverse_pair(previous, item):
                remaining.pop(index)
                removed += 2
                break
            if not commute(previous, item):
                remaining.append(item)
                break
        else:
            remaining.append(item)
    result = circuit.copy_empty_like()
    for item in remaining:
        result.append(item)
    return result, removed
