"""Classical post-processing for tier 10 (Diffie-Hellman / discrete log).

The official lock (``tier10/README.md``) is Diffie-Hellman in a small group:
``A = g**a mod p``, ``B = g**b mod p``, and the shared secret is ``B**a mod p``.
The line is masked with ``keystream(format(secret, f"0{key_width_bits}b"))``.

The quantum period search behind this tier measures a pair ``(k1, k2)`` that
satisfies the linear congruence

    k1 + a * k2 = 0  (mod order)

The theory note (``docs/TIER10_THEORY.md``) writes the same relation as

    u * a = v  (mod order)

with ``u`` the X-register frequency and ``v`` the Z-register frequency.  The two
forms are equivalent under ``k2 = u`` and ``k1 = -v mod order``; both are
supported here.

Raw QFT readouts are *not* frequencies.  Each register is ``m = 6`` bits wide
(``L = 64`` points) while the group order is 41, so a readout ``y`` must be
rounded to the nearest grid point first:

    frequency = round(order * y / L) mod order

``frequency_from_register`` and the ``*_from_counts`` helpers below apply that
mapping and then build the ``(k1, k2)`` equation.  A wrong (off-peak) readout
produces a wrong congruence, which the exponent check ``g**a == A`` rejects.

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

REGISTER_BITS = 6
QFT_SIZE = 1 << REGISTER_BITS

__all__ = [
    "AmbiguousError",
    "CiphertextError",
    "DecodeError",
    "DLError",
    "EquationError",
    "KeyBitsError",
    "NoSolutionError",
    "ParameterError",
    "QFT_SIZE",
    "REGISTER_BITS",
    "candidates_from_measurements",
    "decrypt",
    "decrypt_from_counts",
    "decrypt_tier10",
    "decrypt_with_exponent",
    "equation_from_counts",
    "equation_from_measurement",
    "frequency_from_register",
    "key_bits_for",
    "measurement_from_counts",
    "measurement_from_readout",
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


def _prime_factors(value):
    """Return the set of prime factors of ``value`` by trial division."""
    factors = set()
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            factors.add(divisor)
            value //= divisor
        divisor += 1 if divisor == 2 else 2
    if value > 1:
        factors.add(value)
    return factors


def validate_parameters(public_parameters):
    """Validate and return the official group parameters as a dict.

    Besides type and range checks this verifies that ``order`` is the *minimal*
    order of ``g`` and that ``A``/``B`` lie in the subgroup ``<g>``, using only
    public group arithmetic.  No discrete logarithm is computed here.
    """
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
    for prime in _prime_factors(order):
        if pow(g, order // prime, p) == 1:
            raise ParameterError(
                f"order={order} is not the minimal order of g; "
                f"g**(order/{prime}) is already 1"
            )
    for name in ("A", "B"):
        if not 0 < params[name] < p:
            raise ParameterError(f"{name} must satisfy 0 < {name} < p")
        if pow(params[name], order, p) != 1:
            raise ParameterError(f"{name} is not in the subgroup generated by g")
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


def _check_register_bits(register_bits):
    if isinstance(register_bits, bool) or not isinstance(register_bits, int):
        raise ParameterError(
            f"register_bits must be an int, got {type(register_bits).__name__}"
        )
    if register_bits < 1:
        raise ParameterError(f"register_bits must be positive, got {register_bits}")
    return register_bits


def frequency_from_register(reading, order, register_bits=REGISTER_BITS):
    """Round one QFT readout to the nearest frequency modulo ``order``.

    ``reading`` is the integer value ``y`` of a register with
    ``0 <= y < 2**register_bits``.  The grid point is
    ``round(order * y / 2**register_bits)`` computed in integer arithmetic, and
    the result is reduced modulo ``order`` so ``41 -> 0`` wraps correctly.  The
    raw readout must never be used as the frequency itself.
    """
    _check_register_bits(register_bits)
    _require_int("reading", reading)
    _require_int("order", order)
    if order < 1:
        raise ParameterError(f"order must be positive, got {order}")
    size = 1 << register_bits
    if not 0 <= reading < size:
        raise ParameterError(f"reading must satisfy 0 <= y < {size}, got {reading}")
    return ((2 * order * reading + size) // (2 * size)) % order


def measurement_from_readout(y_x, y_z, order, register_bits=REGISTER_BITS):
    """Convert the two register readouts into the ``(k1, k2)`` equation pair.

    The theory note's ``u a = v (mod order)`` becomes ``k1 + a k2 = 0`` with
    ``k2 = u`` and ``k1 = -v mod order``.
    """
    u = frequency_from_register(y_x, order, register_bits)
    v = frequency_from_register(y_z, order, register_bits)
    return (-v) % order, u


def measurement_from_counts(
    bitstring, order, register_bits=REGISTER_BITS, layout="xz"
):
    """Read one Qiskit counts string of a ``2 * register_bits`` register.

    Qiskit prints ``c[n-1] ... c0`` (most significant character first), so
    ``int(bitstring, 2)`` is the measured integer ``T``.  With ``layout="xz"``
    (the theory note's wiring) the low ``register_bits`` bits are the X register
    and the high bits are Z; ``layout="zx"`` swaps the two halves.
    """
    _check_register_bits(register_bits)
    if layout not in ("xz", "zx"):
        raise ParameterError(f"layout must be 'xz' or 'zx', got {layout!r}")
    if not isinstance(bitstring, str):
        raise ParameterError(
            f"counts must be a bit string, got {type(bitstring).__name__}"
        )
    width = 2 * register_bits
    if len(bitstring) != width:
        raise ParameterError(f"counts must be {width} bits, got {len(bitstring)}")
    if set(bitstring) - {"0", "1"}:
        raise ParameterError("counts may only contain '0' and '1'")
    total = int(bitstring, 2)
    mask = (1 << register_bits) - 1
    low, high = total & mask, total >> register_bits
    if layout == "xz":
        y_x, y_z = low, high
    else:
        y_x, y_z = high, low
    return measurement_from_readout(y_x, y_z, order, register_bits)


def equation_from_counts(
    bitstring, order, register_bits=REGISTER_BITS, layout="xz"
):
    """Round a counts string and return its ``(residue, modulus)`` equation."""
    k1, k2 = measurement_from_counts(bitstring, order, register_bits, layout)
    return equation_from_measurement(k1, k2, order)


def decrypt_from_counts(
    readouts, public_parameters, ciphertext_hex, layout="xz"
):
    """Decrypt tier 10 from raw 12-bit Qiskit counts strings.

    ``readouts`` is one counts string or an iterable of them; each is rounded
    with :func:`frequency_from_register` before the equation is built, so raw
    readouts are never mistaken for mod-41 frequencies.
    """
    params = validate_parameters(public_parameters)
    if isinstance(readouts, str):
        readouts = [readouts]
    measurements = [
        measurement_from_counts(text, params["order"], layout=layout)
        for text in readouts
    ]
    return decrypt(measurements, params, ciphertext_hex)


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


MAX_CANDIDATES_PER_EQUATION = 64
MAX_PAIRWISE_COMBINATIONS = 64
MAX_VERIFICATIONS = 512


def _usable_equations(measurements, order):
    """Convert samples to equations, skipping uninformative or inconsistent ones.

    Structural problems (non-integer entries, wrong tuple shape) stay hard
    errors; a sample that merely contradicts ``k1 + a k2 = 0`` is dropped, since
    a 64-point QFT over a 41-element group can round an off-peak readout into a
    wrong congruence.
    """
    equations = []
    for index, pair in enumerate(measurements):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise EquationError(
                f"measurement {index} must be a (k1, k2) pair, got {pair!r}"
            )
        try:
            equation = equation_from_measurement(pair[0], pair[1], order)
        except NoSolutionError:
            continue
        if equation is not None:
            equations.append(equation)
    return equations


def _verified_candidates(equations, params):
    """Return exponents verified by ``g**a == A``, using bounded work.

    Each equation is tried on its own first (that is the common case: for prime
    order a single non-zero frequency pins one exponent).  Equations with too
    many residues -- and equations that are individually compatible with every
    exponent -- are skipped instead of enumerated.  Only when no single equation
    yields a candidate are bounded pairwise CRT combinations tried.
    """
    order, p, g, target = (
        params["order"],
        params["p"],
        params["g"],
        params["A"],
    )
    seen = set()
    verified = []
    checks = 0

    def consider(residue, modulus):
        nonlocal checks
        count = (order - residue + modulus - 1) // modulus
        if count > MAX_CANDIDATES_PER_EQUATION:
            return
        for candidate in range(residue, order, modulus):
            if checks >= MAX_VERIFICATIONS:
                return
            checks += 1
            if candidate in seen:
                continue
            if pow(g, candidate, p) == target:
                seen.add(candidate)
                verified.append(candidate)

    for residue, modulus in equations:
        consider(residue, modulus)
        if verified or checks >= MAX_VERIFICATIONS:
            break

    if not verified:
        pairs = 0
        for i, first in enumerate(equations):
            for second in equations[i + 1 :]:
                if pairs >= MAX_PAIRWISE_COMBINATIONS or checks >= MAX_VERIFICATIONS:
                    break
                pairs += 1
                try:
                    combined = solve_congruences([first, second])
                except NoSolutionError:
                    continue
                consider(*combined)
            if checks >= MAX_VERIFICATIONS:
                break
    return verified


def recover_exponent(measurements, public_parameters):
    """Return the unique exponent ``a`` with ``g**a mod p == A``.

    The samples are not merged unconditionally: each equation is tried on its
    own, then bounded pairs are combined, and every candidate is verified
    against the public relation.  A wrong (off-peak) sample therefore cannot
    veto the correct candidate; it simply produces no verified exponent.

    Raises ``NoSolutionError`` when no sample yields a verified candidate (the
    caller should resample) and ``AmbiguousError`` when several candidates
    cannot be distinguished.
    """
    params = validate_parameters(public_parameters)
    equations = _usable_equations(measurements, params["order"])
    if not equations:
        raise NoSolutionError(
            "no informative measurement: (0, 0) samples or contradictory pairs only; "
            "collect more shots"
        )
    verified = _verified_candidates(equations, params)
    if not verified:
        raise NoSolutionError(
            "no exponent satisfies g**a == A from these samples; "
            "the readouts were probably off-peak, resample"
        )
    if len(verified) > 1:
        raise AmbiguousError(
            f"{len(verified)} exponents satisfy g**a == A; collect more measurements"
        )
    return verified[0]


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
