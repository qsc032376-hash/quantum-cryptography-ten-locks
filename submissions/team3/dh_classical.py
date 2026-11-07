"""Classical post-processing for tier 10 (Diffie-Hellman / discrete log).

The official lock (``tier10/README.md``) is Diffie-Hellman in a small group:
``A = g**a mod p``, ``B = g**b mod p``, and the shared secret is ``B**a mod p``.
The line is masked with ``keystream(format(secret, f"0{key_width_bits}b"))``.

The quantum period search behind this tier measures a pair ``(k1, k2)`` that
satisfies the linear congruence

    k1 + a * k2 = 0  (mod order)

so the classical job is to solve modular linear equations -- not RSA.  Several
measurements may be needed; they are combined with the CRT, including the cases
where ``k2`` is not invertible (coefficient not coprime with the order).

This module returns plaintext only; the recovered exponent and secret stay
local, so they cannot leak through logs.  Hashing and XOR are reused from
:mod:`classical_keystream`; the modular inverse is reused from
:mod:`rsa_classical`.
"""

import sys
from math import gcd
from pathlib import Path

_TEAM_DIR = Path(__file__).resolve().parent
if str(_TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(_TEAM_DIR))

from classical_keystream import (  # noqa: E402
    CiphertextError,
    DecodeError,
    KeyBitsError,
    decrypt_key_bits,
    key_bits_from_int,
)
from rsa_classical import RSAError, mod_inverse  # noqa: E402

PARAMETER_NAMES = ("p", "g", "order", "A", "B", "key_width_bits")

__all__ = [
    "AmbiguousError",
    "CiphertextError",
    "DecodeError",
    "DLError",
    "EquationError",
    "KeyBitsError",
    "NoSolutionError",
    "ParameterError",
    "candidates_from_measurements",
    "decrypt",
    "decrypt_tier10",
    "decrypt_with_exponent",
    "equation_from_measurement",
    "key_bits_for",
    "recover_exponent",
    "shared_secret",
    "solve_congruences",
    "validate_parameters",
]


class DLError(ValueError):
    """Base class for errors raised by this module."""


class ParameterError(DLError):
    """A public group parameter is missing, malformed, or inconsistent."""


class EquationError(DLError):
    """A measurement is not a usable ``(k1, k2)`` integer pair."""


class NoSolutionError(DLError):
    """The measurements contradict each other or the public group."""


class AmbiguousError(DLError):
    """More than one exponent survives the public check ``g**a == A``."""


def _require_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ParameterError(f"{name} must be an int, got {type(value).__name__}")
    return value


def validate_parameters(public_parameters):
    """Validate and return the official group parameters as a dict."""
    if not isinstance(public_parameters, dict):
        raise ParameterError(
            f"public_parameters must be a dict, got {type(public_parameters).__name__}"
        )
    missing = [name for name in PARAMETER_NAMES if name not in public_parameters]
    if missing:
        raise ParameterError(f"public_parameters is missing {', '.join(missing)}")
    params = {name: public_parameters[name] for name in PARAMETER_NAMES}
    for name, value in params.items():
        _require_int(name, value)
    p, g, order = params["p"], params["g"], params["order"]
    if p < 3:
        raise ParameterError(f"p must be at least 3, got {p}")
    if not 1 < g < p:
        raise ParameterError(f"g must satisfy 1 < g < p, got {g}")
    if order < 1:
        raise ParameterError(f"order must be positive, got {order}")
    if pow(g, order, p) != 1:
        raise ParameterError(f"g**order mod p must be 1 (g={g}, order={order}, p={p})")
    for name in ("A", "B"):
        if not 0 < params[name] < p:
            raise ParameterError(f"{name} must satisfy 0 < {name} < p")
    if params["key_width_bits"] <= 0:
        raise ParameterError("key_width_bits must be positive")
    return params


def equation_from_measurement(k1, k2, order):
    """Turn one measured pair into ``a = c (mod m)``.

    Returns ``(c, m)`` or ``None`` when the pair carries no information (only
    possible for ``k1 = k2 = 0``).  Raises ``EquationError`` for non-integer
    input and ``NoSolutionError`` when the pair contradicts ``k1 + a k2 = 0``.
    """
    for name, value in (("k1", k1), ("k2", k2)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise EquationError(f"{name} must be an int, got {type(value).__name__}")
    _require_int("order", order)
    if order < 1:
        raise ParameterError(f"order must be positive, got {order}")
    k1 %= order
    k2 %= order
    if k2 == 0:
        if k1 == 0:
            return None
        raise NoSolutionError(f"measurement ({k1}, 0) cannot satisfy k1 + a*0 = 0")
    common = gcd(k2, order)
    if k1 % common:
        raise NoSolutionError(
            f"measurement ({k1}, {k2}): no a solves k1 + a*k2 = 0 mod {order}"
        )
    modulus = order // common
    try:
        inverse = mod_inverse(k2 // common, modulus)
    except RSAError as error:  # pragma: no cover - guarded by the gcd test
        raise EquationError(str(error)) from error
    residue = (-(k1 // common) * inverse) % modulus
    return residue, modulus


def solve_congruences(equations):
    """Combine ``[(c, m), ...]`` with the CRT; returns ``(residue, modulus)``."""
    equations = list(equations)
    if not equations:
        raise NoSolutionError("no equations to solve")
    residue, modulus = 0, 1
    for item in equations:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise EquationError(f"equation must be a (residue, modulus) pair, got {item!r}")
        other_residue, other_modulus = item
        for name, value in (("residue", other_residue), ("modulus", other_modulus)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise EquationError(f"{name} must be an int, got {type(value).__name__}")
        if other_modulus < 1:
            raise EquationError(f"modulus must be positive, got {other_modulus}")
        common = gcd(modulus, other_modulus)
        difference = other_residue - residue
        if difference % common:
            raise NoSolutionError(
                f"equations a = {residue} mod {modulus} and "
                f"a = {other_residue} mod {other_modulus} contradict each other"
            )
        lcm = modulus // common * other_modulus
        reduced = other_modulus // common
        if reduced == 1:
            step = 0
        else:
            step = (difference // common) * mod_inverse(modulus // common, reduced)
        residue = (residue + modulus * step) % lcm
        modulus = lcm
    return residue, modulus


def candidates_from_measurements(measurements, order):
    """Return every exponent in ``[0, order)`` consistent with the measurements."""
    equations = []
    for index, pair in enumerate(measurements):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise EquationError(f"measurement {index} must be a (k1, k2) pair, got {pair!r}")
        equation = equation_from_measurement(pair[0], pair[1], order)
        if equation is not None:
            equations.append(equation)
    if not equations:
        raise NoSolutionError("the measurements carry no information about a")
    residue, modulus = solve_congruences(equations)
    return [value for value in range(residue, order, modulus)]


def recover_exponent(measurements, public_parameters):
    """Return the unique exponent ``a`` with ``g**a mod p == A``.

    Raises ``NoSolutionError`` when nothing survives and ``AmbiguousError`` when
    several exponents still satisfy the public relation.
    """
    params = validate_parameters(public_parameters)
    values = [
        a
        for a in candidates_from_measurements(measurements, params["order"])
        if pow(params["g"], a, params["p"]) == params["A"]
    ]
    if not values:
        raise NoSolutionError("no exponent consistent with A = g**a mod p")
    if len(values) > 1:
        raise AmbiguousError(f"{len(values)} exponents fit the public values; collect more measurements")
    return values[0]


def shared_secret(B, a, p):
    """Return the Diffie-Hellman shared secret ``B**a mod p``."""
    _require_int("B", B)
    _require_int("a", a)
    _require_int("p", p)
    if not 0 < B < p:
        raise ParameterError(f"B must satisfy 0 < B < p, got {B}")
    if a < 0:
        raise ParameterError(f"exponent must be non-negative, got {a}")
    return pow(B, a, p)


def key_bits_for(secret, key_width_bits):
    """Return ``format(secret, f"0{key_width_bits}b")``, leading zeros kept."""
    _require_int("key_width_bits", key_width_bits)
    return key_bits_from_int(secret, key_width_bits)


def decrypt_with_exponent(a, public_parameters, ciphertext_hex):
    """Decrypt with an exponent that is already known (e.g. handed over by Junqi)."""
    params = validate_parameters(public_parameters)
    secret = shared_secret(params["B"], a, params["p"])
    key_bits = key_bits_for(secret, params["key_width_bits"])
    return decrypt_key_bits(key_bits, params["key_width_bits"], ciphertext_hex)


def decrypt(measurements, public_parameters, ciphertext_hex):
    """Decrypt tier 10 from measured ``(k1, k2)`` pairs.

    ``measurements`` is an iterable of integer pairs from the quantum
    period-finding run; a single ``(k1, k2)`` tuple is also accepted.
    """
    params = validate_parameters(public_parameters)
    if isinstance(measurements, (tuple, list)) and len(measurements) == 2 and all(
        isinstance(value, int) and not isinstance(value, bool) for value in measurements
    ):
        measurements = [measurements]
    a = recover_exponent(measurements, params)
    return decrypt_with_exponent(a, params, ciphertext_hex)


def decrypt_tier10(measurements, public_parameters, ciphertext_hex):
    """Tier 10 entry point: ``QC-10: ``, Diffie-Hellman shared secret, 7-bit key."""
    return decrypt(measurements, public_parameters, ciphertext_hex)
