"""Tier 5 Grover search: reversible public cipher, measured candidates only.

Full-message decryption remains delegated to Youyang's separate module. The
public prefix is checked only for candidates that actually occur in counts.
No key-space enumeration or stored answer is used.
"""

from importlib.util import module_from_spec, spec_from_file_location
import math
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import load_locked
from common.toy_cipher import ToyCipher


def _load_local_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __package__:
    from . import gf2_synthesis, oracle
else:
    # The official Checker loads solution.py by path without a parent package.
    gf2_synthesis = _load_local_module("tier05_gf2_synthesis", Path(__file__).with_name("gf2_synthesis.py"))
    oracle = _load_local_module("team_tier05_oracle", Path(__file__).with_name("oracle.py"))


KEY_BITS = 10
PLAINTEXT_PREFIX = "QC-05: "
ITERATIONS = 25
MAX_ITERATIONS = 25  # Local resource budget, not an official query restriction.
SHOTS = 128
MAX_SHOTS = 128
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 12345


def _validate_iterations(iterations):
    if type(iterations) is not int:
        raise TypeError("Grover iterations must be an integer")
    if not 1 <= iterations <= MAX_ITERATIONS:
        raise ValueError("This implementation budgets between 1 and 25 iterations")


def theoretical_success_probability(iterations=ITERATIONS):
    """Ideal probability for the official promise of one marked key in 1024."""
    if type(iterations) is not int or iterations < 0:
        raise ValueError("Iterations must be a nonnegative integer")
    theta = math.asin(1 / math.sqrt(2**KEY_BITS))
    return math.sin((2 * iterations + 1) * theta) ** 2


def _public_inputs():
    locked = load_locked(5)
    parameters = locked["public_parameters"]
    prefix = parameters["known_prefix"].encode("ascii")
    ciphertext = bytes.fromhex(locked["ciphertext_hex"])
    if parameters["key_bits"] != KEY_BITS or not prefix.startswith(b"QC"):
        raise ValueError("Unexpected Tier 5 public parameters")
    if len(ciphertext) < len(prefix):
        raise ValueError("Ciphertext must contain the full public prefix")
    return ciphertext, prefix


def count_oracle_calls(circuit):
    """Count outer phase-marking blocks before transpilation, not cipher substeps."""
    return sum(item.operation.name == oracle.ORACLE_NAME for item in circuit.data)


def build_circuit(*, ciphertext=None, iterations=ITERATIONS):
    """Build 10 search + 8 scratch + 1 flag qubits, with 10 measured key bits."""
    _validate_iterations(iterations)
    if ciphertext is None:
        ciphertext, _ = _public_inputs()
    phase_oracle = oracle.build_phase_oracle(ciphertext).to_gate()
    diffuser = oracle.build_diffuser().to_gate()
    circuit = QuantumCircuit(oracle.N_QUBITS, KEY_BITS, name="tier05_grover")
    circuit.h(range(KEY_BITS))
    for _ in range(iterations):
        circuit.append(phase_oracle, range(oracle.N_QUBITS))
        circuit.append(diffuser, range(oracle.N_QUBITS))
    circuit.measure(range(KEY_BITS), range(KEY_BITS))
    if count_oracle_calls(circuit) != iterations:
        raise RuntimeError("Unexpected phase Oracle count")
    return circuit


def measurement_to_key(bitstring: str) -> int:
    """q[j] -> c[j], so c9...c0 converts directly to the integer key."""
    if not isinstance(bitstring, str):
        raise TypeError("The measurement must be a binary string")
    if len(bitstring) != KEY_BITS or any(bit not in "01" for bit in bitstring):
        raise ValueError("Expected exactly 10 binary digits from one register")
    return int(bitstring, 2)


def validate_candidate(key, ciphertext, prefix):
    """Check a measured key against public known text using the official cipher.

    This checks only the public prefix; it does not duplicate the team's
    full-message decryption module and never searches for unmeasured keys.
    """
    if type(key) is not int or not 0 <= key < 2**KEY_BITS:
        raise ValueError("Expected a 10-bit integer key")
    if not isinstance(ciphertext, bytes) or not isinstance(prefix, bytes):
        raise TypeError("Ciphertext and prefix must be bytes")
    if len(prefix) < 2 or len(ciphertext) < len(prefix):
        raise ValueError("A complete public prefix is required")
    return ToyCipher(key, KEY_BITS).decrypt(ciphertext[:len(prefix)]) == prefix


def recover_key_with_diagnostics(*, iterations=ITERATIONS, shots=SHOTS):
    """Execute one Grover circuit once, then check only measured candidates."""
    _validate_iterations(iterations)
    if type(shots) is not int or not 1 <= shots <= MAX_SHOTS:
        raise ValueError("Shots must be an integer between 1 and 128")
    ciphertext, prefix = _public_inputs()
    circuit = build_circuit(ciphertext=ciphertext, iterations=iterations)
    simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
    compiled = transpile(
        circuit, simulator, basis_gates=BASIS_GATES, optimization_level=2,
        seed_transpiler=SEED_TRANSPILER, num_processes=1,
    )
    compiled, _, _ = gf2_synthesis.gf2_runs(compiled)
    result = simulator.run(compiled, shots=shots).result()
    if not result.success:
        raise RuntimeError("Aer failed to execute the Grover circuit")
    counts = result.get_counts(compiled)
    if not counts or any(type(count) is not int or count <= 0 for count in counts.values()):
        raise RuntimeError("Invalid Grover measurement frequencies")
    if sum(counts.values()) != shots:
        raise RuntimeError("Grover measurement count differs from requested shots")

    valid = []
    successes = 0
    for bitstring, count in counts.items():
        key = measurement_to_key(bitstring)
        if validate_candidate(key, ciphertext, prefix):
            valid.append(key)
            successes += count
    if len(valid) != 1 or successes <= shots / 2:
        raise RuntimeError("Grover did not make one prefix-valid measured key likely")
    return valid[0], {
        "search_qubits": KEY_BITS,
        "total_qubits": oracle.N_QUBITS,
        "iterations": iterations,
        "aer_run_calls": 1,
        "shots": shots,
        "oracle_calls_per_circuit": iterations,
        "oracle_queries_including_shots": iterations * shots,
        "distinct_measured_candidates": len(counts),
        "prefix_valid_candidates": len(valid),
        "prefix_success_shots": successes,
        "measured_success_rate": successes / shots,
        "theoretical_success_probability": theoretical_success_probability(iterations),
        "candidate_checks_limited_to_measurements": True,
        "public_prefix_verified": True,
    }


def recover_key() -> int:
    """Public integration entry point: return only the measured integer key."""
    key, _ = recover_key_with_diagnostics()
    return key


def _load_decrypt():
    if __package__:
        try:
            from ..toy_cipher_classical import decrypt_tier5
        except ModuleNotFoundError as error:
            if error.name != f"{__package__.rsplit('.', 1)[0]}.toy_cipher_classical":
                raise
            raise NotImplementedError("Team toy_cipher_classical.py is missing") from None
        return decrypt_tier5

    path = Path(__file__).resolve().parents[1] / "toy_cipher_classical.py"
    if not path.is_file():
        raise NotImplementedError("Team toy_cipher_classical.py is missing")
    return _load_local_module("team_toy_cipher_classical", path).decrypt_tier5


def solve() -> str:
    """Run the real Grover recovery and decrypt the official ciphertext."""
    decrypt_tier5 = _load_decrypt()
    key = recover_key()
    plaintext = decrypt_tier5(key, load_locked(5)["ciphertext_hex"])
    if not isinstance(plaintext, str):
        raise TypeError("The classical module must return plaintext as a string")
    if not plaintext.startswith(PLAINTEXT_PREFIX):
        raise ValueError("Tier 5 plaintext does not match the required prefix")
    return plaintext
