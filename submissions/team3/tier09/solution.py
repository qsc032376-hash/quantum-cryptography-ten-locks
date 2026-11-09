"""Tier 9 order finding with exact native MCX and clean synthesis workspace.

QFT and measured-order mathematics are reused unchanged from earlier tiers.
Aer receives native gates; the official scorer separately expands the actual
executed circuit to its required basis. Never print returned factor values.
"""

from collections import Counter
from math import gcd
from pathlib import Path
import sys
import time

from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

from common import is_correct, load_locked

if not __package__:
    # The official Checker loads solution.py by file path, outside its package.
    team_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(team_dir.parent))
    __package__ = f"{team_dir.name}.tier09"

from ..rsa_classical import CiphertextError, DecodeError, KeyBitsError, RSAError, decrypt_tier9
from ..tier07.qpe import build_inverse_qft
from ..tier08.order import InsufficientMeasurements, recover_order, factors_from_order
from .shared_controls import build_controlled_multiplier

PHASE_BITS = 14
WORK_BITS = 7
SYNTHESIS_WORK_BITS = 1
BASE = 2
SHOTS_PER_BATCH = 64
MAX_BATCHES = 2
MAX_SHOTS = SHOTS_PER_BATCH * MAX_BATCHES
BASIS_GATES = ["rz", "sx", "x", "cx"]  # Scoring basis, NOT the Aer execution basis.
SEED_TRANSPILER = 12345
SEED_SIMULATOR = 909
_POWER_PREFIX = "tier09_controlled_modmul_power_"


def _public_parameters():
    parameters = load_locked(9)["public_parameters"]
    if parameters["N"] != 77:
        raise ValueError("Expected the official Tier 9 modulus")
    return parameters


def build_circuit(*, modulus=None, base=BASE, phase_bits=PHASE_BITS, work_bits=WORK_BITS):
    """14 counting wires, 7 work wires, and one zero-initialized workspace.

    Work bit zero starts at one. Count qj controls multiplication by the
    public pow(base, 2**j, modulus), then the full inverse QFT maps qj to cj.
    The extra wire is part of the actual circuit sent to Aer. Native MCX
    leaves it idle; official basis synthesis may use and restore it as a
    clean ancilla. It is not appended only to a separate scoring circuit.
    Smaller explicit dimensions support synthetic tests only.
    """
    if modulus is None:
        modulus = _public_parameters()["N"]
    if type(modulus) is not int or modulus < 4:
        raise ValueError("Invalid modulus")
    if type(base) is not int or not 2 <= base <= modulus - 2 or gcd(base, modulus) != 1:
        raise ValueError("Choose a public nontrivial coprime base")
    if type(phase_bits) is not int or phase_bits < 1:
        raise ValueError("Invalid phase-register width")
    if type(work_bits) is not int or work_bits < 1 or modulus > (1 << work_bits):
        raise ValueError("Modulus does not fit the work register")
    circuit = QuantumCircuit(phase_bits + work_bits, phase_bits, name="tier09_order_finding")
    circuit.add_register(QuantumRegister(SYNTHESIS_WORK_BITS, "synthesis_work"))
    work = list(range(phase_bits, phase_bits + work_bits))
    circuit.x(work[0])
    circuit.h(range(phase_bits))
    cache = {}
    for control in range(phase_bits):
        exponent = 1 << control
        multiplier = pow(base, exponent, modulus)
        if multiplier not in cache:
            cache[multiplier] = build_controlled_multiplier(multiplier, modulus, work_bits).to_gate()
        powered = cache[multiplier].copy(name=f"{_POWER_PREFIX}{exponent}")
        circuit.append(powered, [control, *work])
    circuit.append(build_inverse_qft(phase_bits).to_gate(), range(phase_bits))
    circuit.measure(range(phase_bits), range(phase_bits))
    return circuit


def count_modular_powers(circuit):
    """Count our outer blocks, never permutation-cycle lengths."""
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
    """Run one native Aer batch, plus at most one evidence-driven supplement.

    No classical factoring fallback. Repeated multiplier construction is
    cached, the full execution circuit is compiled once, and no dense matrix
    is created. Return private factors and aggregate evidence only.
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
        "qubits": circuit.num_qubits, "classical_bits": circuit.num_clbits,
        "opaque_gate_count": circuit.size() - PHASE_BITS,
        "depth_including_measurements": circuit.depth(),
    }
    simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
    # The pinned Aer statevector backend implements MCX exactly. Preserve it
    # for execution; official scoring will decompose this SAME executed circuit.
    compiled = transpile(
        circuit, simulator, optimization_level=1,
        seed_transpiler=SEED_TRANSPILER, num_processes=1,
    )
    compilation_seconds = time.perf_counter() - started
    if compilation_seconds >= 100:
        raise TimeoutError("Compilation exhausted the execution budget; no simulation retry")
    native_counts = {name: int(count) for name, count in compiled.count_ops().items()}
    combined = Counter()
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
            raise RuntimeError("Incomplete phase measurements")
        combined.update(counts)
        duration = time.perf_counter() - batch_started
        batches.append({
            "shots": SHOTS_PER_BATCH, "seed_simulator": SEED_SIMULATOR + batch,
            "elapsed_seconds": round(duration, 6),
        })
        try:
            order, evidence = recover_order(dict(combined), BASE, modulus, PHASE_BITS)
        except InsufficientMeasurements:
            if batch + 1 == MAX_BATCHES:
                raise
            if time.perf_counter() - started + duration >= 110:
                raise TimeoutError("Insufficient time for one bounded supplemental batch") from None
            continue
        factors = factors_from_order(BASE, modulus, order)
        if (len(factors) != 2 or any(type(f) is not int or not 1 < f < modulus for f in factors)
                or factors[0] * factors[1] != modulus):
            raise RuntimeError("Measured order did not yield nontrivial complementary factors")
        total_shots = sum(combined.values())
        diagnostics = {
            "modulus": modulus, "base": BASE,
            "phase_bits": PHASE_BITS, "work_bits": WORK_BITS,
            "additional_qubits": SYNTHESIS_WORK_BITS, "borrowed_qubits": 0,
            "clean_synthesis_workspace_qubits": SYNTHESIS_WORK_BITS,
            "logical_opaque_metrics": logical,
            "simulation_operation_counts": native_counts,
            "simulation_basis": "Aer statevector native basis (MCX retained)",
            "queries_per_shot": queries,
            "batches": batches,
            "aer_run_calls": len(batches), "shots": total_shots,
            "distinct_measured_outcomes": len(combined),
            "recovered_order": order, "order_evidence": evidence,
            "modular_order_check": pow(BASE, order, modulus) == 1,
            "nontrivial_factors_verified": True,
            "factors_recovered_from_measurements": True,
            "controlled_power_blocks_shot_weighted": PHASE_BITS * total_shots,
            "equivalent_base_multiplications_shot_weighted": ((1 << PHASE_BITS) - 1) * total_shots,
            "build_and_transpile_seconds": round(compilation_seconds, 6),
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "plaintext_hash_verified": False, "secret_values_recorded": False,
        }
        return tuple(factors), diagnostics
    raise InsufficientMeasurements("No order recovered within the finite shot budget")


def recover_factors() -> tuple[int, int]:
    """Measured factors for Junrui's RSA adapter; do not print them."""
    return recover_factors_with_diagnostics()[0]


def solve():
    """Run the quantum flow and delegate RSA/keystream to Youyang's module."""
    locked = load_locked(9)
    p, q = recover_factors()
    try:
        plaintext = decrypt_tier9(p, q, locked["public_parameters"], locked["ciphertext_hex"])
    except (RSAError, CiphertextError, DecodeError, KeyBitsError):
        raise RuntimeError("Tier 9 RSA or keystream validation failed") from None
    if not isinstance(plaintext, str) or not plaintext.startswith("QC-09: "):
        raise RuntimeError("Tier 9 plaintext prefix validation failed")
    if not is_correct(9, plaintext):
        raise RuntimeError("Tier 9 plaintext failed final hash verification")
    return plaintext
