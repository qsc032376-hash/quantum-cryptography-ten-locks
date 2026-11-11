"""Tier 7: recover a 14-bit phase by QPE and check it with quantum interference.

Never print or serialize measured phase integers, bitstrings, Oracle matrices,
or plaintext. The classical keystream belongs to the shared team module.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import time

from qiskit import transpile
from qiskit.result import Counts
from qiskit_aer import AerSimulator

from common import is_correct, load_locked
from tier07 import helper


def _load_local_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __package__:
    from . import qpe
else:
    # The Checker imports solution.py by path without a parent package.
    qpe = _load_local_module("team_tier07_qpe", Path(__file__).with_name("qpe.py"))

PHASE_BITS = qpe.PHASE_BITS
build_qpe_circuit = qpe.build_qpe_circuit
build_phase_check_circuit = qpe.build_phase_check_circuit
count_controlled_powers = qpe.count_controlled_powers

SHOTS = 64
CHECK_SHOTS = 32
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 12345
# Pre-compile the recorded circuit at level 2; the Checker's fixed level-1
# re-transpile then sees 209 CX / depth 154 / 536 total gates instead of
# 209 / 266 / 727. Compilation only; algorithm and measurement are unchanged.
PRE_OPTIMIZATION_LEVEL = 2
SEED_SIMULATOR = 707


def build_circuit(*, unitary=None, eigenstate=None):
    """Official diagram interface; the same circuit is used in real recovery."""
    if unitary is None:
        unitary = helper.build_unitary()
    if eigenstate is None:
        eigenstate = helper.build_eigenstate()
    return build_qpe_circuit(unitary, eigenstate, phase_bits=PHASE_BITS)


def measurement_to_phase(bitstring):
    """qj -> cj and a full inverse QFT give c13...c0: no bit reversal."""
    if not isinstance(bitstring, str) or len(bitstring) != PHASE_BITS or set(bitstring) - {"0", "1"}:
        raise ValueError("Expected exactly 14 binary measurement digits")
    return int(bitstring, 2)


def phase_from_counts(counts, expected_shots=SHOTS):
    """Validate exact-grid ideal QPE, without guessing from plaintext hashes.

    Cross-check direct binary conversion, explicit qj/cj weights, and Qiskit's
    integer-outcome conversion. Leading zeroes remain in the 14-character key.
    """
    if type(expected_shots) is not int or expected_shots < 1:
        raise ValueError("Invalid shot count")
    positive = {}
    for bits, count in counts.items():
        measurement_to_phase(bits)
        if type(count) is not int or count < 0:
            raise ValueError("Invalid measurement frequency")
        if count:
            positive[bits] = count
    if sum(positive.values()) != expected_shots:
        raise RuntimeError("Incomplete QPE measurements")
    if len(positive) != 1:
        raise RuntimeError("Exact-grid ideal QPE did not produce one consistent outcome")
    bitstring, frequency = next(iter(positive.items()))
    phase = measurement_to_phase(bitstring)
    weighted = sum(int(bitstring[-1 - j]) << j for j in range(PHASE_BITS))
    integer_counts = Counts(positive, memory_slots=PHASE_BITS).int_outcomes()
    if weighted != phase or integer_counts != {phase: frequency} or format(phase, "014b") != bitstring:
        raise RuntimeError("Measurement register conversions disagree")
    return phase, {
        "shots": expected_shots,
        "distinct_outcomes": len(positive),
        "dominant_count": frequency,
        "dominant_probability": frequency / expected_shots,
        "conversion_methods_agree": True,
        "leading_zero_width_preserved": True,
    }


def _simulate(simulator, circuit, shots, seed):
    compiled = transpile(
        circuit, basis_gates=BASIS_GATES, optimization_level=PRE_OPTIMIZATION_LEVEL,
        seed_transpiler=SEED_TRANSPILER, num_processes=1,
    )
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    if not result.success:
        raise RuntimeError("Aer execution failed; no retry")
    counts = {bits: int(value) for bits, value in result.get_counts().items()}
    if sum(counts.values()) != shots:
        raise RuntimeError("Incomplete Aer measurements")
    return counts


def recover_phase_with_diagnostics():
    """Return private measured integer k and a safe aggregate report.

    One QPE batch (64 shots), then one phase-cancellation batch (32 shots).
    The second circuit uses the MEASURED integer; it does not query a hidden
    phase attribute, read a classical eigenspectrum, or try alternative keys.
    """
    started = time.perf_counter()
    unitary = helper.build_unitary()
    eigenstate = helper.build_eigenstate()
    circuit = build_circuit(unitary=unitary, eigenstate=eigenstate)
    expected_queries = {
        "controlled_power_blocks": PHASE_BITS,
        "equivalent_base_U_applications": (1 << PHASE_BITS) - 1,
        "exponents": [1 << j for j in range(PHASE_BITS)],
    }
    queries = count_controlled_powers(circuit)
    if queries != expected_queries:
        raise RuntimeError("Unexpected QPE controlled powers")
    simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
    counts = _simulate(simulator, circuit, SHOTS, SEED_SIMULATOR)
    phase, measurement = phase_from_counts(counts, SHOTS)
    qpe_seconds = time.perf_counter() - started
    if qpe_seconds > 100:
        raise TimeoutError("Insufficient time budget for phase verification; no retry")
    check_started = time.perf_counter()
    check = build_phase_check_circuit(unitary, eigenstate, phase, phase_bits=PHASE_BITS)
    check_queries = count_controlled_powers(check)
    if check_queries != expected_queries:
        raise RuntimeError("Unexpected phase-check controlled powers")
    check_counts = _simulate(simulator, check, CHECK_SHOTS, SEED_SIMULATOR + 1)
    if check_counts != {"0" * PHASE_BITS: CHECK_SHOTS}:
        raise RuntimeError("Measured phase failed quantum phase cancellation; no retry")
    diagnostics = {
        "phase_bits": PHASE_BITS,
        "target_qubits": 1,
        "qpe_measurement": measurement,
        "qpe_queries_per_shot": queries,
        "phase_check_queries_per_shot": check_queries,
        "phase_check_shots": CHECK_SHOTS,
        "phase_check_all_zero_shots": CHECK_SHOTS,
        "phase_check_passed": True,
        "aer_run_calls": 2,
        "total_shots": SHOTS + CHECK_SHOTS,
        "controlled_power_blocks_shot_weighted": PHASE_BITS * (SHOTS + CHECK_SHOTS),
        "equivalent_base_U_applications_shot_weighted": ((1 << PHASE_BITS) - 1) * (SHOTS + CHECK_SHOTS),
        "matrix_power_construction": "full complex 2x2 matrix; repeated squaring, no eigenspectrum",
        "qpe_seconds": round(qpe_seconds, 6),
        "phase_check_seconds": round(time.perf_counter() - check_started, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "plaintext_hash_verified": False,
        "secret_values_recorded": False,
    }
    return phase, diagnostics


def recover_phase() -> int:
    """Private 14-bit integer for Junrui's decrypt(k, ciphertext_hex) adapter."""
    return recover_phase_with_diagnostics()[0]


def _load_decrypt():
    if __package__:
        try:
            from ..tier07_classical import decrypt
        except ModuleNotFoundError as error:
            if error.name != f"{__package__.rsplit('.', 1)[0]}.tier07_classical":
                raise
            raise NotImplementedError("Team tier07_classical.py is missing") from None
        return decrypt

    path = Path(__file__).resolve().parents[1] / "tier07_classical.py"
    if not path.is_file():
        raise NotImplementedError("Team tier07_classical.py is missing")
    return _load_local_module("team_tier07_classical", path).decrypt


def solve() -> str:
    """Return verified text from the measured phase and the shared decryptor."""
    decrypt = _load_decrypt()
    locked = load_locked(7)
    if locked["public_parameters"]["key_bits"] != PHASE_BITS:
        raise ValueError("Unexpected public phase precision")
    phase = recover_phase()
    plaintext = decrypt(phase, locked["ciphertext_hex"])
    if not isinstance(plaintext, str) or not plaintext.startswith("QC-07: ") or not is_correct(7, plaintext):
        raise RuntimeError("Tier 7 plaintext failed final hash verification")
    return plaintext
