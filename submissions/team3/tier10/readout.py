"""Thin measured-readout adapter for the documented Tier 10 wiring.

Counts are one register, printed Z high bits followed by X low bits. Both
registers use the full inverse QFT. The circuit computes g**x * A**z, so the
rounded frequencies give the candidate equation u*a = v and pair (-v mod r, u).
Finite-grid outliers are expected; a rounded equation is not automatically true.
This module neither evaluates the public exponent relation nor decrypts data.
"""

from math import gcd

from .. import dh_classical


class InconsistentSample(ValueError):
    """One measured equation has no solution; no other sample is discarded."""


def _positive_integer(value, name):
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def round_frequency(raw, order, register_bits=6) -> int:
    """Round order*raw/2**m half-up, then wrap modulo order; never use round()."""
    _positive_integer(order, "order")
    _positive_integer(register_bits, "register_bits")
    if type(raw) is not int:
        raise TypeError("A raw register reading must be an integer")
    size = 1 << register_bits
    if not 0 <= raw < size:
        raise ValueError("A raw register reading must fit register_bits")
    return dh_classical.frequency_from_register(raw, order, register_bits)


def measurement_from_counts(bitstring, order, register_bits=6, layout="xz") -> tuple[int, int]:
    """Convert one fixed-width counts key to (k1=-v mod order, k2=u).

    Only the confirmed layout is accepted: X_j -> c_j, Z_j -> c_(m+j).
    The left half of the displayed string is therefore Z, not X. Neither
    half is reversed, and whitespace or missing leading zeroes is rejected.
    """
    _positive_integer(order, "order")
    _positive_integer(register_bits, "register_bits")
    if layout != "xz":
        raise ValueError("Only the confirmed xz wiring (printed Z then X) is supported")
    if not isinstance(bitstring, str):
        raise TypeError("A counts key must be a binary string")
    if len(bitstring) != 2 * register_bits or set(bitstring) - {"0", "1"}:
        raise ValueError("A counts key must contain exactly 2*register_bits binary digits")
    return dh_classical.measurement_from_counts(bitstring, order, register_bits, layout)


def _equation_from_pair(pair, order):
    """Reduce one congruence; never enumerate its remaining residue class."""
    k1, k2 = pair
    right_hand_side = (-k1) % order
    if k2 == 0:
        if right_hand_side == 0:
            return None
        raise InconsistentSample("A zero coefficient has a nonzero right-hand side")
    common = gcd(k2, order)
    if right_hand_side % common:
        raise InconsistentSample("The measured congruence fails the gcd divisibility condition")
    modulus = order // common
    if modulus == 1:
        return None
    inverse = pow(k2 // common, -1, modulus)
    residue = (right_hand_side // common * inverse) % modulus
    return residue, modulus


def equation_from_counts(bitstring, order, register_bits=6, layout="xz"):
    """Return (residue, modulus), None for no information, or InconsistentSample.

    A modulus smaller than order describes a partial equation, not a unique
    exponent. Resolving such an equation requires more quantum evidence.
    """
    pair = measurement_from_counts(bitstring, order, register_bits, layout)
    return _equation_from_pair(pair, order)


def candidate_evidence(counts, order, register_bits=6) -> tuple[dict, dict, dict]:
    """Aggregate fully determined candidates without merging different samples.

    Candidate weights and one actual observed pair per candidate stay private
    in the first two return values. Diagnostics contain aggregates only. The
    four shot categories are disjoint and sum to total_shots; partial equations
    are counted separately and never expanded into possible exponents.
    """
    _positive_integer(order, "order")
    _positive_integer(register_bits, "register_bits")
    if not isinstance(counts, dict):
        raise TypeError("counts must be a dictionary of binary keys and frequencies")
    weights = {}
    witnesses = {}
    diagnostics = {
        "total_shots": 0,
        "distinct_outcomes": 0,
        "informative_shots": 0,
        "uninformative_shots": 0,
        "inconsistent_shots": 0,
        "partial_equation_shots": 0,
    }
    for bitstring, frequency in counts.items():
        pair = measurement_from_counts(bitstring, order, register_bits)
        if type(frequency) is not int:
            raise TypeError("Measurement frequencies must be integers")
        if frequency < 0:
            raise ValueError("Measurement frequencies must be nonnegative")
        if frequency == 0:
            continue
        diagnostics["total_shots"] += frequency
        diagnostics["distinct_outcomes"] += 1
        try:
            equation = _equation_from_pair(pair, order)
        except InconsistentSample:
            diagnostics["inconsistent_shots"] += frequency
            continue
        if equation is None:
            diagnostics["uninformative_shots"] += frequency
            continue
        residue, modulus = equation
        if modulus != order:
            diagnostics["partial_equation_shots"] += frequency
            continue
        diagnostics["informative_shots"] += frequency
        weights[residue] = weights.get(residue, 0) + frequency
        witnesses.setdefault(residue, pair)
    return dict(sorted(weights.items())), dict(sorted(witnesses.items())), diagnostics
