"""Tier 10: measured two-register discrete logarithm, with robust readout.

Only measurement-derived, full-modulus candidates are publicly verified.
No exponent range is enumerated, no inconsistent equations are merged, and
DH shared-secret/keystream decryption remains in Youyang's shared module.
Returned exponents, counts and witnesses are private; never log them.
"""

from collections import Counter
from dataclasses import dataclass, field
from math import gcd
from pathlib import Path
import sys
import time

from qiskit import transpile
from qiskit_aer import AerSimulator

from common import is_correct, load_locked

if not __package__:
    # Checker imports solution.py by path, including from a renamed team directory.
    team_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(team_dir.parent))
    __package__ = f"{team_dir.name}.tier10"

from ..tier08.order import _prime_divisors_of_order
from .circuit import (
    REGISTER_BITS, WORK_BITS, build_qpe_circuit, count_group_powers,
)
from .readout import candidate_evidence, measurement_from_counts

SHOTS_PER_BATCH = 128
MAX_BATCHES = 2
MAX_SHOTS = SHOTS_PER_BATCH * MAX_BATCHES
MAX_CANDIDATES_PER_BATCH = 8
BASIS_GATES = ["rz", "sx", "x", "cx"]  # Official scoring basis only.
SEED_TRANSPILER = 12345
SEED_SIMULATOR = 1010


class InsufficientQuantumEvidence(RuntimeError):
    """The bounded quantum samples did not supply a verified candidate."""


def _validate_parameters(parameters):
    if not isinstance(parameters, dict):
        raise TypeError("Expected public group parameters")
    p, g, order, public_A = (parameters[name] for name in ("p", "g", "order", "A"))
    if any(type(value) is not int for value in (p, g, order, public_A)):
        raise TypeError("Public group parameters must be integers")
    if not 3 <= p <= 1 << WORK_BITS or not 2 <= order <= 1 << REGISTER_BITS:
        raise ValueError("Public group does not fit the declared registers")
    if not 1 < g < p or not 1 <= public_A < p or gcd(g, p) != 1:
        raise ValueError("Invalid public generator or group element")
    # The field modulus is promised prime by the official challenge. Verify
    # the PUBLIC generator order, factoring only that supplied small order.
    if pow(g, order, p) != 1 or any(
        pow(g, order // prime, p) == 1 for prime in _prime_divisors_of_order(order)
    ):
        raise ValueError("The supplied generator does not have the declared order")
    if pow(public_A, order, p) != 1:
        raise ValueError("The public A is outside the declared subgroup")
    if "B" in parameters:
        public_B = parameters["B"]
        if (type(public_B) is not int or not 1 <= public_B < p
                or pow(public_B, order, p) != 1):
            raise ValueError("The public B is outside the declared subgroup")
    return parameters


def _public_parameters():
    return _validate_parameters(load_locked(10)["public_parameters"])


def build_circuit(*, parameters=None):
    """Official diagram entry point, identical to the real quantum builder."""
    parameters = _public_parameters() if parameters is None else _validate_parameters(parameters)
    return build_qpe_circuit(
        parameters["p"], parameters["g"], parameters["A"],
        register_bits=REGISTER_BITS, work_bits=WORK_BITS,
    )


def verify_public_candidate(exponent, parameters):
    """Verify ONE measurement-derived exponent; never search an exponent range."""
    return (type(exponent) is int and 0 <= exponent < parameters["order"]
            and pow(parameters["g"], exponent, parameters["p"]) == parameters["A"])


@dataclass
class ExponentRecovery:
    exponent: int = field(repr=False)
    counts: dict[str, int] = field(repr=False)
    measurement: tuple[int, int] = field(repr=False)
    counts_key: str = field(repr=False)
    diagnostics: dict


def recover_exponent_with_diagnostics():
    """Return a measured residue modulo the public order, counts and evidence.

    One 128-shot batch, at most one bounded supplement; at most 8 new observed
    candidates per batch. Rank candidates by aggregated shot support rather
    than blindly combining all approximate Fourier equations.
    """
    started = time.perf_counter()
    parameters = _public_parameters()
    order = parameters["order"]
    circuit = build_circuit(parameters=parameters)
    queries = count_group_powers(circuit)
    expected = {
        "controlled_power_blocks": 2 * REGISTER_BITS,
        "g_exponents": [1 << j for j in range(REGISTER_BITS)],
        "A_exponents": [1 << j for j in range(REGISTER_BITS)],
        "equivalent_base_multiplications": 2 * ((1 << REGISTER_BITS) - 1),
    }
    if queries != expected:
        raise RuntimeError("Unexpected dual-register controlled powers")
    logical_metrics = {
        "qubits": circuit.num_qubits, "classical_bits": circuit.num_clbits,
        "opaque_gate_count": circuit.size() - 2 * REGISTER_BITS,
        "depth_including_measurements": circuit.depth(),
    }
    simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
    compiled = transpile(
        circuit, simulator, optimization_level=1,
        seed_transpiler=SEED_TRANSPILER, num_processes=1,
    )
    compilation_seconds = time.perf_counter() - started
    if compilation_seconds >= 100:
        raise TimeoutError("Compilation exhausted the execution budget; no retry")
    combined = Counter()
    tested = set()
    batches = []
    for batch in range(MAX_BATCHES):
        batch_started = time.perf_counter()
        result = simulator.run(
            compiled, shots=SHOTS_PER_BATCH, seed_simulator=SEED_SIMULATOR + batch,
        ).result()
        if not result.success:
            raise RuntimeError("Aer failed; no retry")
        counts = {bits: int(count) for bits, count in result.get_counts().items()}
        if sum(counts.values()) != SHOTS_PER_BATCH:
            raise RuntimeError("Incomplete two-register measurements")
        combined.update(counts)
        duration = time.perf_counter() - batch_started
        weights, witnesses, evidence = candidate_evidence(dict(combined), order, register_bits=REGISTER_BITS)
        ranked = sorted((candidate for candidate in weights if candidate not in tested),
                        key=lambda candidate: (-weights[candidate], candidate))
        verified = None
        checks = 0
        for candidate in ranked[:MAX_CANDIDATES_PER_BATCH]:
            tested.add(candidate)
            checks += 1
            if verify_public_candidate(candidate, parameters):
                verified = candidate
                break
        batches.append({
            "shots": SHOTS_PER_BATCH, "seed_simulator": SEED_SIMULATOR + batch,
            "elapsed_seconds": round(duration, 6), "new_candidates_checked": checks,
        })
        if verified is not None:
            pair = witnesses[verified]
            witness_key = next(
                bits for bits, count in combined.items()
                if count > 0 and measurement_from_counts(bits, order, register_bits=REGISTER_BITS) == pair
            )
            support = weights[verified]
            informative = evidence["informative_shots"]
            total = sum(combined.values())
            if not 0 < support <= informative <= total:
                raise RuntimeError("Invalid measurement support accounting")
            diagnostics = {
                "register_bits": REGISTER_BITS, "work_bits": WORK_BITS,
                "public_group_order": order,
                "extra_or_borrowed_qubits": 0,
                "logical_opaque_metrics": logical_metrics,
                "simulation_operation_counts": {name: int(count) for name, count in compiled.count_ops().items()},
                "queries_per_shot": queries,
                "batches": batches, "aer_run_calls": len(batches), "shots": total,
                "readout_evidence": evidence,
                "distinct_measurement_derived_candidates": len(weights),
                "public_candidate_checks": len(tested),
                "maximum_public_candidate_checks": MAX_BATCHES * MAX_CANDIDATES_PER_BATCH,
                "verified_informative_support_shots": support,
                "support_fraction_of_all_shots": support / total,
                "support_fraction_of_informative_shots": support / informative,
                "support_is_same_batch_empirical_not_independent_probability": True,
                "exponent_residue_recovered_from_measurements": True,
                "public_relation_verified": True,
                "classical_interface_witness_has_full_modulus": True,
                "controlled_power_blocks_shot_weighted": 2 * REGISTER_BITS * total,
                "equivalent_base_multiplications_shot_weighted": 2 * ((1 << REGISTER_BITS) - 1) * total,
                "build_and_transpile_seconds": round(compilation_seconds, 6),
                "elapsed_seconds": round(time.perf_counter() - started, 6),
                "plaintext_hash_verified": False, "secret_values_recorded": False,
            }
            return ExponentRecovery(verified, dict(combined), pair, witness_key, diagnostics)
        if batch + 1 < MAX_BATCHES and time.perf_counter() - started + duration >= 110:
            raise TimeoutError("Insufficient time for a bounded supplemental batch")
    raise InsufficientQuantumEvidence("No measurement-derived exponent passed the public relation within the sampling/candidate budgets")


def recover_exponent() -> int:
    """Private exponent residue, not the DH shared-secret key."""
    return recover_exponent_with_diagnostics().exponent


def solve():
    """Send one verified full-modulus sample through the shared classical API.

    The referenced classical version merges all input equations and can
    enumerate incomplete congruence classes. Supplying just this verified,
    full-order equation avoids both paths. Never pass all noisy raw samples.
    """
    try:
        from ..dh_classical import (
            measurement_from_counts as shared_measurement,
            equation_from_counts as shared_equation,
            recover_exponent as shared_recover,
            decrypt_tier10,
        )
    except ModuleNotFoundError as error:
        if error.name != f"{__package__.rsplit('.', 1)[0]}.dh_classical":
            raise
        raise NotImplementedError("Tier 10 requires Youyang's dh_classical module") from error
    locked = load_locked(10)
    parameters = _validate_parameters(locked["public_parameters"])
    recovery = recover_exponent_with_diagnostics()
    pair = shared_measurement(recovery.counts_key, parameters["order"], register_bits=REGISTER_BITS, layout="xz")
    equation = shared_equation(recovery.counts_key, parameters["order"], register_bits=REGISTER_BITS, layout="xz")
    if pair != recovery.measurement or equation != (recovery.exponent, parameters["order"]):
        raise RuntimeError("Shared readout convention disagrees with the verified quantum witness")
    if shared_recover([pair], parameters) != recovery.exponent:
        raise RuntimeError("Shared exponent recovery disagrees with the verified quantum witness")
    try:
        plaintext = decrypt_tier10([pair], parameters, locked["ciphertext_hex"])
    except ValueError:
        raise RuntimeError("Tier 10 DH or keystream validation failed") from None
    if not isinstance(plaintext, str) or not plaintext.startswith("QC-10: "):
        raise RuntimeError("Tier 10 plaintext prefix validation failed")
    if not is_correct(10, plaintext):
        raise RuntimeError("Tier 10 plaintext failed final hash verification")
    return plaintext
