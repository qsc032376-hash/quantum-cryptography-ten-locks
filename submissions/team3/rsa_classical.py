"""Classical RSA post-processing for tiers 8 and 9.

After the quantum period search returns the factors ``p`` and ``q`` of the
public modulus ``N``, the official wrapping rule (``tier08/README.md``,
``tier09/README.md``) is:

1. ``phi = (p - 1)(q - 1)`` and ``d = e**-1 mod phi``.
2. ``k = wrapped_key**d mod N``.
3. ``key_bits = format(k, f"0{key_width_bits}b")``, leading zeros kept.
4. plaintext = ciphertext XOR ``keystream(key_bits, len(ciphertext))``.

The last step reuses :mod:`classical_keystream`, so no hashing or XOR code is
duplicated here.  The module never reads ``locked.json`` itself and never
hardcodes a factor: the caller supplies ``p`` and ``q``.
"""

import sys
from pathlib import Path

# Sibling module lives next to this file; independent of cwd and folder name.
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

PARAMETER_NAMES = ("N", "e", "wrapped_key", "key_width_bits")

__all__ = [
    "CiphertextError",
    "DecodeError",
    "FactorError",
    "KeyBitsError",
    "ParameterError",
    "RSAError",
    "decrypt",
    "decrypt_tier8",
    "decrypt_tier9",
    "euler_phi",
    "key_bits_for",
    "mod_inverse",
    "private_exponent",
    "unwrap_key",
    "validate_factors",
]


class RSAError(ValueError):
    """Base class for errors raised by this module."""


class FactorError(RSAError):
    """The candidate factors are not a valid factorisation of the modulus."""


class ParameterError(RSAError):
    """A public RSA parameter is missing, malformed, or unusable."""


def _require_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ParameterError(f"{name} must be an int, got {type(value).__name__}")
    return value


def validate_factors(n, p, q):
    """Check that ``p`` and ``q`` are a genuine, distinct factor pair of ``n``."""
    _require_int("N", n)
    for name, value in (("p", p), ("q", q)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise FactorError(f"{name} must be an int, got {type(value).__name__}")
        if value < 2:
            raise FactorError(f"{name} must be at least 2, got {value}")
        if value >= n:
            raise FactorError(f"{name} must be smaller than N, got {value}")
    if p * q != n:
        raise FactorError(f"p * q = {p * q} does not equal N = {n}")
    if p == q:
        raise FactorError("p and q must be distinct")
    return p, q


def euler_phi(p, q):
    """Return ``(p - 1)(q - 1)`` for distinct primes ``p`` and ``q``."""
    return (p - 1) * (q - 1)


def mod_inverse(value, modulus):
    """Return ``value**-1 mod modulus`` or raise ``ParameterError``."""
    _require_int("value", value)
    _require_int("modulus", modulus)
    if modulus <= 1:
        raise ParameterError(f"modulus must exceed 1, got {modulus}")
    value %= modulus
    old_r, r = value, modulus
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    if old_r != 1:
        raise ParameterError(
            f"{value} has no inverse modulo {modulus} (gcd = {old_r})"
        )
    return old_s % modulus


def private_exponent(e, p, q):
    """Return ``d = e**-1 mod phi``; raises when ``e`` is not invertible."""
    _require_int("e", e)
    if e < 2:
        raise ParameterError(f"e must be at least 2, got {e}")
    phi = euler_phi(p, q)
    return mod_inverse(e, phi)


def unwrap_key(wrapped_key, e, n, p, q):
    """Recover the symmetric key integer ``k = wrapped_key**d mod N``."""
    validate_factors(n, p, q)
    _require_int("wrapped_key", wrapped_key)
    if not 0 <= wrapped_key < n:
        raise ParameterError(
            f"wrapped_key must satisfy 0 <= c < N, got {wrapped_key}"
        )
    d = private_exponent(e, p, q)
    return pow(wrapped_key, d, n)


def key_bits_for(k, key_width_bits):
    """Return ``format(k, f"0{key_width_bits}b")`` with leading zeros kept."""
    _require_int("key_width_bits", key_width_bits)
    return key_bits_from_int(k, key_width_bits)


def _public_parameters(public_parameters):
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
    if params["key_width_bits"] <= 0:
        raise ParameterError("key_width_bits must be positive")
    return params


def decrypt(p, q, public_parameters, ciphertext_hex):
    """Decrypt one RSA-wrapped tier line from the factors and public parameters.

    ``public_parameters`` is ``locked.json["public_parameters"]`` with keys
    ``N``, ``e``, ``wrapped_key`` and ``key_width_bits``.  Returns the plaintext
    string; the key itself is not returned, so it cannot leak through logs.
    """
    params = _public_parameters(public_parameters)
    k = unwrap_key(params["wrapped_key"], params["e"], params["N"], p, q)
    key_bits = key_bits_for(k, params["key_width_bits"])
    return decrypt_key_bits(key_bits, params["key_width_bits"], ciphertext_hex)


def decrypt_tier8(p, q, public_parameters, ciphertext_hex):
    """Tier 8 entry point (``QC-08: ``, N = 35 in the official data)."""
    return decrypt(p, q, public_parameters, ciphertext_hex)


def decrypt_tier9(p, q, public_parameters, ciphertext_hex):
    """Tier 9 entry point (``QC-09: ``, N = 77 in the official data)."""
    return decrypt(p, q, public_parameters, ciphertext_hex)
