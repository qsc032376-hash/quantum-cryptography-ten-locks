"""Exact measured-phase postprocessing for Shor order finding.

Candidate periods come only from credible continued-fraction denominators and
their bounded LCM closure. We never trial-divide the modulus or scan possible
orders. Only an already verified, measurement-derived period is factored to
remove redundancy and certify minimality.
"""

from math import gcd, lcm


class InsufficientMeasurements(RuntimeError):
    """Valid measurements do not yet support an order; aggregates are safe."""

    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = dict(diagnostics or {})


def _validate_phase_bits(phase_bits):
    if type(phase_bits) is not int:
        raise TypeError("phase_bits must be an integer")
    if phase_bits < 1:
        raise ValueError("phase_bits must be positive")


def _validate_instance(base, modulus):
    if type(base) is not int or type(modulus) is not int:
        raise TypeError("base and modulus must be integers")
    if modulus < 4:
        raise ValueError("modulus must be at least four")
    if not 2 <= base <= modulus - 2:
        raise ValueError("base must lie between 2 and modulus - 2")
    if gcd(base, modulus) != 1:
        raise ValueError("Choose a coprime base; a classical precheck is not order finding")


def measurement_to_integer(bits, phase_bits=12) -> int:
    """Read c[t-1]...c[0] directly, with qubit j carrying weight 2**j."""
    _validate_phase_bits(phase_bits)
    if not isinstance(bits, str):
        raise TypeError("A measured phase must be a binary string")
    if len(bits) != phase_bits or set(bits) - {"0", "1"}:
        raise ValueError("The measured phase must have exactly phase_bits binary digits")
    return int(bits, 2)


def _convergents(numerator, denominator):
    """Yield exact continued-fraction convergents using integer arithmetic."""
    previous_p, current_p = 0, 1
    previous_q, current_q = 1, 0
    while denominator:
        quotient, remainder = divmod(numerator, denominator)
        next_p = quotient * current_p + previous_p
        next_q = quotient * current_q + previous_q
        yield next_p, next_q
        previous_p, current_p = current_p, next_p
        previous_q, current_q = current_q, next_q
        numerator, denominator = denominator, remainder


def _credible_denominator(measured, grid, modulus):
    for numerator, denominator in _convergents(measured, grid):
        if denominator >= modulus:
            break
        if denominator <= 1:
            continue
        # |y/Q - p/q| < 1/(2*N*N), without a rounded float comparison.
        error_numerator = abs(measured * denominator - numerator * grid)
        if 2 * modulus * modulus * error_numerator < grid * denominator:
            return denominator
    return None


def _lcm_candidates(denominators, limit):
    """All distinct subset LCMs up to limit; outliers cannot erase good subsets."""
    candidates = set()
    for denominator in sorted(denominators):
        additions = {denominator}
        for candidate in candidates:
            combined = lcm(candidate, denominator)
            if combined <= limit:
                additions.add(combined)
        candidates.update(additions)
    return sorted(candidates)


def _prime_divisors_of_order(period):
    """Factor the candidate period, never the public modulus."""
    divisors = []
    remaining = period
    candidate = 2
    while candidate * candidate <= remaining:
        if remaining % candidate == 0:
            divisors.append(candidate)
            while remaining % candidate == 0:
                remaining //= candidate
        candidate = 3 if candidate == 2 else candidate + 2
    if remaining > 1:
        divisors.append(remaining)
    return tuple(divisors)


def _minimize_verified_period(base, modulus, period):
    """Remove only prime divisors of a verified measurement-derived period."""
    order = period
    for prime in _prime_divisors_of_order(period):
        while order % prime == 0 and pow(base, order // prime, modulus) == 1:
            order //= prime
    primes = _prime_divisors_of_order(order)
    if pow(base, order, modulus) != 1 or any(
        pow(base, order // prime, modulus) == 1 for prime in primes
    ):
        raise ArithmeticError("The minimal-order certificate failed")
    return order, len(primes)


def recover_order(counts, base, modulus, phase_bits=12) -> tuple[int, dict]:
    """Recover an order from measured phases, or request more quantum evidence.

    No unobserved denominator multiples are tried. The LCM closure has at most
    modulus - 1 entries. Invalid inputs are distinct from insufficient evidence,
    so a caller can bound resampling without retrying programming errors.
    """
    _validate_instance(base, modulus)
    _validate_phase_bits(phase_bits)
    if not isinstance(counts, dict):
        raise TypeError("counts must be a dictionary of measured binary strings")

    grid = 1 << phase_bits
    denominators = set()
    diagnostics = {
        "measured_shots": 0,
        "distinct_outcomes": 0,
        "nonzero_shots": 0,
        "accepted_phase_shots": 0,
        "accepted_denominator_count": 0,
        "lcm_candidate_count": 0,
        "period_candidates_tested": 0,
        "verified_order": None,
        "minimal_order_verified": False,
    }
    for bits, frequency in counts.items():
        measured = measurement_to_integer(bits, phase_bits)
        if type(frequency) is not int:
            raise TypeError("Measurement frequencies must be integers")
        if frequency < 0:
            raise ValueError("Measurement frequencies must be nonnegative")
        if frequency == 0:
            continue
        diagnostics["measured_shots"] += frequency
        diagnostics["distinct_outcomes"] += 1
        if measured == 0:
            continue
        diagnostics["nonzero_shots"] += frequency
        denominator = _credible_denominator(measured, grid, modulus)
        if denominator is not None:
            denominators.add(denominator)
            diagnostics["accepted_phase_shots"] += frequency

    diagnostics["accepted_denominator_count"] = len(denominators)
    candidates = _lcm_candidates(denominators, modulus - 1)
    diagnostics["lcm_candidate_count"] = len(candidates)
    for candidate in candidates:
        diagnostics["period_candidates_tested"] += 1
        if pow(base, candidate, modulus) != 1:
            continue
        order, certificate_checks = _minimize_verified_period(base, modulus, candidate)
        diagnostics.update(
            verified_order=order,
            verified_period_multiple=candidate,
            minimal_order_verified=True,
            minimality_prime_checks=certificate_checks,
        )
        return order, diagnostics
    raise InsufficientMeasurements(
        "Observed phase denominators do not yet support an order; additional quantum samples are needed",
        diagnostics,
    )


def factors_from_order(base, modulus, order) -> tuple[int, int]:
    """Use a certified even order to extract complementary nontrivial factors.

    This is gcd postprocessing, not trial division of modulus. The challenge's
    distinct-prime semiprime promise supplies the interpretation as RSA factors.
    """
    _validate_instance(base, modulus)
    if type(order) is not int:
        raise TypeError("order must be an integer")
    if not 1 < order < modulus:
        raise ValueError("order must lie between 2 and modulus - 1")
    if pow(base, order, modulus) != 1:
        raise ValueError("The supplied order does not satisfy the modular period equation")
    if any(
        pow(base, order // prime, modulus) == 1
        for prime in _prime_divisors_of_order(order)
    ):
        raise ValueError("The supplied order is not minimal")
    if order % 2:
        raise ValueError("An odd order cannot supply the required factor extraction")
    halfway = pow(base, order // 2, modulus)
    if halfway in (1, modulus - 1):
        raise ValueError("The half-order power is trivial; another base is needed")
    first, second = sorted((gcd(halfway - 1, modulus), gcd(halfway + 1, modulus)))
    if not (1 < first < modulus and 1 < second < modulus):
        raise ValueError("Order postprocessing did not produce nontrivial factors")
    if first == second or first * second != modulus:
        raise ValueError("The gcd results are not distinct complementary factors")
    return first, second
