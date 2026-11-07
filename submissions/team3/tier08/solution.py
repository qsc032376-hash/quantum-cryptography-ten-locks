"""Tier 8 quantum order finding; factors originate only in Aer measurements.

The public modular permutation is compiled reversibly. No classical search
for the order or factors of N is used, and RSA decryption stays in the shared
classical module. Do not log returned factors or decrypted values.
"""

from collections import Counter
from math import gcd
from pathlib import Path
import sys
import time

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import is_correct, load_locked

if not __package__:
    # The official Checker loads solution.py by file path, outside its package.
    team_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(team_dir.parent))
    __package__ = f"{team_dir.name}.tier08"

from ..rsa_classical import CiphertextError, DecodeError, KeyBitsError, RSAError, decrypt_tier8
from ..tier07.qpe import build_inverse_qft
from .modular import build_controlled_multiplier, dirty_qubit_count
from ..tier08.order import (
    InsufficientMeasurements, recover_order, factors_from_order,
)

PHASE_BITS = 12
WORK_BITS = 6
BASE = 2
SHOTS_PER_BATCH = 64
MAX_BATCHES = 2
MAX_SHOTS = SHOTS_PER_BATCH * MAX_BATCHES
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 12345
SEED_SIMULATOR = 808
_POWER_PREFIX = "tier08_controlled_modmul_power_"


def _public_parameters():
    parameters = load_locked(8)["public_parameters"]
    if parameters["N"] != 35:
        raise ValueError("Expected the official Tier 8 modulus")
    return parameters


def build_circuit(*, modulus=None, base=BASE, phase_bits=PHASE_BITS, work_bits=WORK_BITS):
    """Count q0..11; work q12..17 starts at integer 1; qj measures into cj.

    Other counting wires are borrowed as dirty MCX ancillas, restored exactly
    even when entangled. No additional qubits or order-dependent shortcuts.
    Optional dimensions are for small synthetic tests, not hidden-data tuning.
    """
    if modulus is None:
        modulus = _public_parameters()["N"]
    if type(modulus) is not int or modulus < 3:
        raise ValueError("Invalid modulus")
    if type(base) is not int or not 2 <= base <= modulus - 2 or gcd(base, modulus) != 1:
        raise ValueError("Choose a public nontrivial coprime base; do not extract gcd factors here")
    if type(phase_bits) is not int or phase_bits < 1:
        raise ValueError("Invalid phase-register width")
    if type(work_bits) is not int or work_bits < 1 or modulus > (1 << work_bits):
        raise ValueError("Modulus does not fit the work register")
    borrowed_count = dirty_qubit_count(work_bits)
    if phase_bits - 1 < borrowed_count:
        raise ValueError("Not enough other counting wires for exact dirty borrowing")
    circuit = QuantumCircuit(phase_bits + work_bits, phase_bits, name="tier08_order_finding")
    work = list(range(phase_bits, phase_bits + work_bits))
    circuit.x(work[0])  # Little-endian |1>, with all other work bits zero.
    circuit.h(range(phase_bits))
    cache = {}
    for control in range(phase_bits):
        exponent = 1 << control
        multiplier = pow(base, exponent, modulus)  # Public modular exponentiation only.
        if multiplier not in cache:
            cache[multiplier] = build_controlled_multiplier(multiplier, modulus, work_bits).to_gate()
        powered = cache[multiplier].copy(name=f"{_POWER_PREFIX}{exponent}")
        dirty = [wire for wire in range(phase_bits) if wire != control][:borrowed_count]
        circuit.append(powered, [control, *work, *dirty])
    circuit.append(build_inverse_qft(phase_bits).to_gate(), range(phase_bits))
    circuit.measure(range(phase_bits), range(phase_bits))
    return circuit


def count_modular_powers(circuit):
    """Read our named outer blocks only; do not infer order from permutations."""
    exponents = []
    for item in circuit.data:
        name = item.operation.name
        if name.startswith(_POWER_PREFIX):
            exponent = int(name[len(_POWER_PREFIX):])
            if exponent < 1 or exponent & (exponent - 1):
                raise ValueError("Invalid modular-power block")
            exponents.append(exponent)
    return {
        "controlled_power_blocks": len(exponents),
        "equivalent_base_multiplications": sum(exponents),
        "exponents": exponents,
    }


def recover_factors_with_diagnostics():
    """Return a private (p,q) pair and aggregate, measurement-derived evidence.

    One 64-shot batch normally suffices. At most one extra batch is allowed,
    solely if continued-fraction evidence is insufficient and time permits.
    """
    started = time.perf_counter()
    modulus = _public_parameters()["N"]
    circuit = build_circuit(modulus=modulus)
    queries = count_modular_powers(circuit)
    expected = {
        "controlled_power_blocks": PHASE_BITS,
        "equivalent_base_multiplications": (1 << PHASE_BITS) - 1,
        "exponents": [1 << j for j in range(PHASE_BITS)],
    }
    if queries != expected:
        raise RuntimeError("Unexpected controlled modular powers")
    logical = {
        "qubits": circuit.num_qubits,
        "classical_bits": circuit.num_clbits,
        "opaque_gate_count": circuit.size() - PHASE_BITS,
        "depth_including_measurements": circuit.depth(),
    }
    simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
    compiled = transpile(
        circuit, basis_gates=BASIS_GATES, optimization_level=1,
        seed_transpiler=SEED_TRANSPILER, num_processes=1,
    )
    compilation_seconds = time.perf_counter() - started
    if compilation_seconds >= 100:
        raise TimeoutError("Compilation exhausted the execution budget; no simulation retry")
    combined = Counter()
    batches = []
    order_diagnostics = None
    for batch in range(MAX_BATCHES):
        batch_started = time.perf_counter()
        result = simulator.run(
            compiled, shots=SHOTS_PER_BATCH, seed_simulator=SEED_SIMULATOR + batch,
        ).result()
        if not result.success:
            raise RuntimeError("Aer failed; no retry")
        counts = {bits: int(count) for bits, count in result.get_counts().items()}
        if sum(counts.values()) != SHOTS_PER_BATCH:
            raise RuntimeError("Incomplete phase measurements")
        combined.update(counts)
        duration = time.perf_counter() - batch_started
        batches.append({
            "shots": SHOTS_PER_BATCH, "seed_simulator": SEED_SIMULATOR + batch,
            "elapsed_seconds": round(duration, 6),
        })
        try:
            order, order_diagnostics = recover_order(dict(combined), BASE, modulus, PHASE_BITS)
        except InsufficientMeasurements:
            if batch + 1 == MAX_BATCHES:
                raise
            if time.perf_counter() - started + duration >= 110:
                raise TimeoutError("Insufficient time for one bounded supplemental batch") from None
            continue
        # A valid but unusable order requires a different base, not more shots
        # of this same circuit. Stop rather than claim classical factorization.
        factors = factors_from_order(BASE, modulus, order)
        if (len(factors) != 2 or any(type(value) is not int or not 1 < value < modulus for value in factors)
                or factors[0] * factors[1] != modulus):
            raise RuntimeError("Measured order did not yield a valid nontrivial factor pair")
        total_shots = sum(combined.values())
        diagnostics = {
            "modulus": modulus,
            "base": BASE,
            "phase_bits": PHASE_BITS,
            "work_bits": WORK_BITS,
            "additional_qubits": 0,
            "borrowed_dirty_counting_qubits_per_block": dirty_qubit_count(WORK_BITS),
            "logical_opaque_metrics": logical,
            "queries_per_shot": queries,
            "batches": batches,
            "aer_run_calls": len(batches),
            "shots": total_shots,
            "distinct_measured_outcomes": len(combined),
            "recovered_order": order,
            "order_evidence": order_diagnostics,
            "modular_order_check": pow(BASE, order, modulus) == 1,
            "nontrivial_factors_verified": True,
            "factors_recovered_from_measurements": True,
            "controlled_power_blocks_shot_weighted": PHASE_BITS * total_shots,
            "equivalent_base_multiplications_shot_weighted": ((1 << PHASE_BITS) - 1) * total_shots,
            "build_and_transpile_seconds": round(compilation_seconds, 6),
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "plaintext_hash_verified": False,
            "secret_values_recorded": False,
        }
        return tuple(factors), diagnostics
    raise InsufficientMeasurements("No order recovered within the finite shot budget")


def recover_factors() -> tuple[int, int]:
    """Private factors for Junrui's shared RSA decrypt adapter."""
    return recover_factors_with_diagnostics()[0]


def solve():
    """Run quantum recovery, then delegate all RSA/keystream work."""
    locked = load_locked(8)
    p, q = recover_factors()
    try:
        plaintext = decrypt_tier8(p, q, locked["public_parameters"], locked["ciphertext_hex"])
    except (RSAError, CiphertextError, DecodeError, KeyBitsError):
        raise RuntimeError("Tier 8 RSA or keystream validation failed") from None
    if not isinstance(plaintext, str) or not plaintext.startswith("QC-08: "):
        raise RuntimeError("Tier 8 plaintext prefix validation failed")
    if not is_correct(8, plaintext):
        raise RuntimeError("Tier 8 plaintext failed final hash verification")
    return plaintext
