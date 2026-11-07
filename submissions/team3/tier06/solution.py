"""Measured, bounded multi-solution Grover search for Tier 6.

Only the public first byte Q is used by the quantum predicate. Calibration
estimates the marked population from an actual flag measurement; it never
enumerates keys. Returned candidates/counts are private data: do not log them.
"""

from collections import Counter
from dataclasses import dataclass, field
from importlib.util import module_from_spec, spec_from_file_location
import math
from pathlib import Path
import time

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import is_correct, load_locked
from common.toy_cipher import ToyCipher


def _load_local_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __package__:
    from . import oracle
else:
    # The Checker imports solution.py by path without a package.
    oracle = _load_local_module("team_tier06_oracle", Path(__file__).with_name("oracle.py"))

KEY_BITS, MAIN_QUBITS, PILOT_QUBITS = oracle.KEY_BITS, oracle.MAIN_QUBITS, oracle.PILOT_QUBITS
build_bit_oracle = oracle.build_bit_oracle
build_diffuser = oracle.build_diffuser
build_phase_oracle = oracle.build_phase_oracle

KEY_SPACE = 1 << KEY_BITS
PLAINTEXT_PREFIX = "QC-06: "
PILOT_SHOTS = 2048
MAX_ITERATIONS = 24
MAX_SEARCH_SHOTS = 1024
MAX_SEARCH_BATCHES = 2
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 12345
SEED_SIMULATOR = 606
PHASE_NAME = "tier06_Q_phase"
BIT_NAME = "tier06_Q_flag"


def _public_inputs():
    locked = load_locked(6)
    public = locked["public_parameters"]
    if public["key_bits"] != KEY_BITS or public["known_prefix"] != "Q":
        raise ValueError("Unexpected Tier 6 public prefix or key width")
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    if not ciphertext:
        raise ValueError("Empty Tier 6 ciphertext")
    return ciphertext, public["checksum"]


def _ciphertext(value):
    if value is None:
        value, _ = _public_inputs()
    if not isinstance(value, bytes) or not value:
        raise ValueError("Expected nonempty ciphertext bytes")
    return value


def build_circuit(iterations=12, *, ciphertext=None):
    """14 key + 8 work qubits; work[7] doubles as the phase target.

    The no-argument circuit is a diagram with a nominal 12 rounds. Recovery
    always supplies the round count selected by the measured calibration.
    Classical bit j measures key qubit j, so int(bitstring, 2) needs no reversal.
    """
    if type(iterations) is not int or not 1 <= iterations <= MAX_ITERATIONS:
        raise ValueError("Grover iterations exceed the local resource budget")
    ciphertext = _ciphertext(ciphertext)
    circuit = QuantumCircuit(MAIN_QUBITS, KEY_BITS, name="tier06_search")
    phase = build_phase_oracle(ciphertext[0]).to_gate(label="Q only")
    phase.name = PHASE_NAME
    diffuser = build_diffuser().to_gate(label="diffuser")
    circuit.h(range(KEY_BITS))
    for _ in range(iterations):
        circuit.append(phase, range(MAIN_QUBITS))
        circuit.append(diffuser, range(MAIN_QUBITS))
    circuit.measure(range(KEY_BITS), range(KEY_BITS))
    return circuit


def build_calibration_circuit(*, ciphertext=None):
    """One Grover round, then compute Q predicate into an extra measured flag.

    Phase-oracle work is uncomputed, so measuring that work would not estimate
    success. The second, bit-valued predicate explicitly records f(key).
    """
    ciphertext = _ciphertext(ciphertext)
    circuit = QuantumCircuit(PILOT_QUBITS, 1, name="tier06_calibration")
    phase = build_phase_oracle(ciphertext[0]).to_gate()
    phase.name = PHASE_NAME
    marker = build_bit_oracle(ciphertext[0]).to_gate()
    marker.name = BIT_NAME
    circuit.h(range(KEY_BITS))
    circuit.append(phase, range(MAIN_QUBITS))
    circuit.compose(build_diffuser(), range(MAIN_QUBITS), inplace=True)
    circuit.append(marker, range(PILOT_QUBITS))
    circuit.measure(PILOT_QUBITS - 1, 0)
    return circuit


def count_oracle_calls(circuit):
    """Count our named public predicate blocks BEFORE transpilation."""
    operations = circuit.count_ops()
    return {
        "phase": int(operations.get(PHASE_NAME, 0)),
        "bit_predicate": int(operations.get(BIT_NAME, 0)),
    }


def measurement_to_key(bitstring):
    if not isinstance(bitstring, str) or len(bitstring) != KEY_BITS or set(bitstring) - {"0", "1"}:
        raise ValueError("Expected exactly 14 measured binary digits")
    return int(bitstring, 2)


def deduplicate_candidates(counts, ciphertext):
    """Check only positive-count measured keys, using only public byte zero."""
    ciphertext = _ciphertext(ciphertext)
    candidates = []
    total = prefix_shots = measured_unique = 0
    for bitstring, frequency in counts.items():
        key = measurement_to_key(bitstring)
        if type(frequency) is not int or frequency < 0:
            raise ValueError("Invalid measurement frequency")
        if not frequency:
            continue
        measured_unique += 1
        total += frequency
        if ToyCipher(key, KEY_BITS).decrypt_byte(ciphertext[0], 0) == ord("Q"):
            candidates.append(key)
            prefix_shots += frequency
    return sorted(candidates), {
        "measured_unique": measured_unique,
        "prefix_candidates": len(candidates),
        "prefix_shots": prefix_shots,
        "total_shots": total,
    }


def estimate_marked_count(hits, shots):
    """Infer M on the public small-population branch 0 < M/N < 1/4.

    p1 = sin^2(3 theta), theta = asin(sqrt(M/N)). Wilson 95% bounds are
    approximate statistical intervals, not proof of M or complete coverage.
    """
    if type(hits) is not int or type(shots) is not int or not 0 < hits < shots:
        raise ValueError("Insufficient calibration evidence; no automatic retry")
    p = hits / shots
    z = 1.959963984540054
    denominator = 1 + z * z / shots
    center = (p + z * z / (2 * shots)) / denominator
    half = z * math.sqrt(p * (1 - p) / shots + z * z / (4 * shots * shots)) / denominator
    theta = math.asin(math.sqrt(p)) / 3
    theta_low = math.asin(math.sqrt(max(0, center - half))) / 3
    theta_high = math.asin(math.sqrt(min(1, center + half))) / 3
    lower = KEY_SPACE * math.sin(theta_low) ** 2
    upper = KEY_SPACE * math.sin(theta_high) ** 2
    estimate = KEY_SPACE * math.sin(theta) ** 2
    iterations = math.floor(math.pi / (4 * theta))
    if not 1 <= iterations <= MAX_ITERATIONS or upper >= KEY_SPACE / 4:
        raise ValueError("Estimated population is outside the supported search budget")
    angles = [(2 * iterations + 1) * theta_low, (2 * iterations + 1) * theta_high]
    # No zero may lie inside the interval; otherwise endpoint bounds are unsafe.
    if math.ceil(angles[0] / math.pi) <= math.floor(angles[1] / math.pi):
        raise ValueError("Calibration interval is too wide for stable amplification")
    success_lower = min(math.sin(angle) ** 2 for angle in angles)
    if success_lower < 0.5:
        raise ValueError("Calibration interval is too wide for the sampling budget")
    # Conditional coupon-collector union bound: P(any of M missed) <=
    # M exp(-draws/M). Valid only if M is below our statistical upper bound.
    marked_upper = math.ceil(upper)
    target = math.ceil(marked_upper * math.log(marked_upper / 0.05))
    shots_needed = math.ceil(target / success_lower / 64) * 64
    if shots_needed > MAX_SEARCH_SHOTS:
        raise ValueError("Estimated candidate coverage exceeds the finite shot budget")
    return {
        "p_hat": p,
        "marked_estimate": estimate,
        "marked_interval95": [lower, upper],
        "small_population_branch_assumption": "0 < M/N < 1/4 (public about-64 promise)",
        "iterations": iterations,
        "predicted_success_probability": math.sin((2 * iterations + 1) * theta) ** 2,
        "predicted_success_lower95": success_lower,
        "target_marked_draws": target,
        "planned_search_shots": shots_needed,
        "conditional_miss_probability_target": 0.05,
        "coverage_is_not_guaranteed": True,
    }


def _simulate(simulator, circuit, shots, seed):
    compiled = transpile(
        circuit, basis_gates=BASIS_GATES, optimization_level=1,
        seed_transpiler=SEED_TRANSPILER, num_processes=1,
    )
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    if not result.success:
        raise RuntimeError("Aer failed; no automatic retry")
    counts = {bits: int(count) for bits, count in result.get_counts().items()}
    if sum(counts.values()) != shots:
        raise RuntimeError("Incomplete Aer measurements")
    return counts


@dataclass
class CandidateRecovery:
    candidates: list[int] = field(repr=False)
    counts: dict[str, int] = field(repr=False)
    diagnostics: dict


def recover_candidates_with_diagnostics(*, confirm_candidates=None):
    """One calibration, at most two search batches and 1024 search shots.

    The caller must keep candidates and raw counts private. Diagnostics contain
    aggregates only. An optional callback receives only newly measured Q
    candidates; a missed hash may use the remaining bounded search batch.
    """
    started = time.perf_counter()
    ciphertext, _ = _public_inputs()
    simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
    calibration = build_calibration_circuit(ciphertext=ciphertext)
    pilot_queries = count_oracle_calls(calibration)
    if pilot_queries != {"phase": 1, "bit_predicate": 1}:
        raise RuntimeError("Invalid calibration query accounting")
    pilot = _simulate(simulator, calibration, PILOT_SHOTS, SEED_SIMULATOR)
    if set(pilot) - {"0", "1"}:
        raise RuntimeError("Unexpected calibration flag measurement")
    estimate = estimate_marked_count(pilot.get("1", 0), PILOT_SHOTS)
    calibration_seconds = time.perf_counter() - started
    rounds = estimate["iterations"]
    search = build_circuit(rounds, ciphertext=ciphertext)
    queries = count_oracle_calls(search)
    if queries != {"phase": rounds, "bit_predicate": 0}:
        raise RuntimeError("Invalid search query accounting")
    all_counts = Counter()
    batches = []
    prefix_by_key = {}
    batch_shots = estimate["planned_search_shots"]
    search_started = time.perf_counter()
    supplemental_batch_skipped_for_time = False
    hash_supplement_requested = False
    for batch in range(MAX_SEARCH_BATCHES):
        if time.perf_counter() - started >= 110:
            raise TimeoutError("Search time budget exhausted; no retry")
        batch_started = time.perf_counter()
        counts = _simulate(simulator, search, batch_shots, SEED_SIMULATOR + 1 + batch)
        batch_seconds = time.perf_counter() - batch_started
        all_counts.update(counts)
        # Each unique measured key is checked once, even across batches.
        fresh = {bits: count for bits, count in counts.items() if bits not in prefix_by_key}
        fresh_candidates, _ = deduplicate_candidates(fresh, ciphertext)
        accepted = set(fresh_candidates)
        prefix_by_key.update({bits: measurement_to_key(bits) in accepted for bits in fresh})
        total = sum(all_counts.values())
        marked_draws = sum(count for bits, count in all_counts.items() if prefix_by_key[bits])
        batches.append({
            "shots": batch_shots, "seed_simulator": SEED_SIMULATOR + 1 + batch,
            "elapsed_seconds": round(batch_seconds, 6),
        })
        if marked_draws / total < 0.5:
            raise RuntimeError("Observed amplification failed; stop without retry")
        confirmed = confirm_candidates(sorted(accepted)) if confirm_candidates is not None else False
        missing = estimate["target_marked_draws"] - marked_draws
        if (total >= MAX_SEARCH_SHOTS or batch + 1 >= MAX_SEARCH_BATCHES
                or (missing <= 0 and (confirm_candidates is None or confirmed))):
            break
        if time.perf_counter() - started + batch_seconds >= 110:
            supplemental_batch_skipped_for_time = True
            break
        # Keep the original coverage supplement. If no candidate passed the
        # final checks, use the remaining budget with the same calibrated
        # circuit and the next simulator seed.
        if confirm_candidates is not None and not confirmed:
            hash_supplement_requested = True
            supplement = MAX_SEARCH_SHOTS - total
        else:
            supplement = math.ceil(missing / estimate["predicted_success_lower95"] / 64) * 64
        batch_shots = min(MAX_SEARCH_SHOTS - total, supplement)
    candidates = sorted(measurement_to_key(bits) for bits, valid in prefix_by_key.items() if valid)
    if not candidates:
        raise RuntimeError("No measured candidate passed the public Q predicate")
    diagnostics = {
        "calibration_shots": PILOT_SHOTS,
        "calibration_flag_hits": pilot.get("1", 0),
        "calibration_seed_simulator": SEED_SIMULATOR,
        "calibration_seconds": round(calibration_seconds, 6),
        "calibration_queries_per_shot": pilot_queries,
        "estimate": estimate,
        "search_batches": batches,
        "search_seconds": round(time.perf_counter() - search_started, 6),
        "search_shots": total,
        "distinct_measured_candidates": len(all_counts),
        "public_prefix_candidates": len(candidates),
        "public_prefix_shots": marked_draws,
        "public_prefix_hit_rate": marked_draws / total,
        "classical_unique_candidates_checked": len(prefix_by_key),
        "search_queries_per_shot": queries,
        "phase_queries_shot_weighted": PILOT_SHOTS + rounds * total,
        "bit_predicate_queries_shot_weighted": PILOT_SHOTS,
        "aer_run_calls": 1 + len(batches),
        "coverage_target_draws_reached": marked_draws >= estimate["target_marked_draws"],
        "supplemental_batch_skipped_for_time": supplemental_batch_skipped_for_time,
        "hash_supplement_requested": hash_supplement_requested,
        "calibration_upper_not_contradicted_by_observed_candidates":
            len(candidates) <= estimate["marked_interval95"][1],
        "complete_candidate_coverage_proven": False,
        "checksum_checked": False,
        "plaintext_hash_verified": False,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    return CandidateRecovery(candidates, dict(all_counts), diagnostics)


def recover_candidates() -> list[int]:
    """Private 14-bit integer candidates for Junrui's classical integration."""
    return recover_candidates_with_diagnostics().candidates


def _load_filter():
    if __package__:
        try:
            from ..toy_cipher_classical import filter_candidates
        except ModuleNotFoundError as error:
            if error.name != f"{__package__.rsplit('.', 1)[0]}.toy_cipher_classical":
                raise
            raise NotImplementedError("Team toy_cipher_classical.py is missing") from None
        return filter_candidates

    path = Path(__file__).resolve().parents[1] / "toy_cipher_classical.py"
    if not path.is_file():
        raise NotImplementedError("Team toy_cipher_classical.py is missing")
    return _load_local_module("team_toy_cipher_classical", path).filter_candidates


def _solve_with_diagnostics():
    filter_candidates = _load_filter()
    ciphertext, checksum = _public_inputs()
    verified = set()
    checksum_passes = full_prefix_passes = hash_passes = 0

    def confirm_candidates(candidates):
        nonlocal checksum_passes, full_prefix_passes, hash_passes
        if candidates:
            plaintexts = filter_candidates(6, candidates, ciphertext.hex(), checksum)
            if not isinstance(plaintexts, list) or any(not isinstance(text, str) for text in plaintexts):
                raise TypeError("Expected filter_candidates to return list[str]")
            checksum_passes += len(plaintexts)
            for text in plaintexts:
                prefix_ok = text.startswith(PLAINTEXT_PREFIX)
                hash_ok = is_correct(6, text)
                full_prefix_passes += prefix_ok
                hash_passes += hash_ok
                if prefix_ok and hash_ok:
                    verified.add(text)
        return bool(verified)

    recovery = recover_candidates_with_diagnostics(confirm_candidates=confirm_candidates)
    if len(verified) != 1:
        raise RuntimeError(
            "Measured candidates do not yield one hash-confirmed plaintext "
            f"({len(recovery.candidates)} Q candidates, {checksum_passes} checksum/UTF-8 "
            f"passes, {hash_passes} hash passes, {recovery.diagnostics['search_shots']} search shots)"
        )
    return verified.pop(), {
        **recovery.diagnostics,
        "checksum_checked": True,
        "checksum_utf8_passes": checksum_passes,
        "full_prefix_passes": full_prefix_passes,
        "hash_passes": hash_passes,
        "plaintext_hash_verified": True,
    }


def solve() -> str:
    """Return the unique prefix- and hash-confirmed text from measured candidates."""
    plaintext, _ = _solve_with_diagnostics()
    return plaintext
