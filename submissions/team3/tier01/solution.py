"""Team 3 Tier 1: Bernstein--Vazirani with one opaque oracle application.

Run from the repository root. No recovered key or plaintext is printed or saved.
The separate classical.py module belongs to Youyang and is not duplicated here.
"""

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import load_locked
from tier01 import helper


N_INPUT_QUBITS = 24
TARGET_QUBIT = N_INPUT_QUBITS
N_QUBITS = N_INPUT_QUBITS + 1
SHOTS = 1
# Match the public scoring basis and compilation settings.
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 12345


def build_circuit():
    """Return the main 25-qubit/24-bit circuit (also used for diagrams).

    Qubit j is measured into classical bit j. The target is prepared in |->
    and is not measured. The supplied oracle remains an opaque named block;
    only the official counter traverses it, as required by the tier rules.
    """
    circuit = QuantumCircuit(N_QUBITS, N_INPUT_QUBITS, name="tier01_bv")
    circuit.x(TARGET_QUBIT)
    circuit.h(TARGET_QUBIT)
    circuit.h(range(N_INPUT_QUBITS))

    oracle = helper.build_oracle()
    if oracle.num_qubits != N_QUBITS or oracle.num_clbits != 0:
        raise ValueError("Tier 1 requires a 25-qubit oracle with no classical bits")
    circuit.append(oracle.to_gate(), range(N_QUBITS))

    circuit.h(range(N_INPUT_QUBITS))
    circuit.measure(range(N_INPUT_QUBITS), range(N_INPUT_QUBITS))
    if helper.count_oracle_calls(circuit) != 1:
        raise ValueError("Tier 1 requires exactly one oracle application")
    return circuit


def measurement_to_key(bitstring: str) -> int:
    """Decode c23...c0 from the single 24-bit classical register.

    Qiskit displays the most significant classical bit on the left. Because
    q[j] -> c[j] and qubit j represents 2**j, do NOT reverse this string.
    Byte conversion and decryption are delegated to the classical module.
    """
    if not isinstance(bitstring, str):
        raise TypeError("The measurement must be a binary string")
    if len(bitstring) != N_INPUT_QUBITS or any(b not in "01" for b in bitstring):
        raise ValueError("Expected exactly 24 binary digits from one register")
    return int(bitstring, 2)


def recover_key() -> int:
    """Recover the key from one actual, noiseless Aer measurement.

    No gate-definition inspection or classical key search is used. The ideal
    BV circuit is deterministic, so one shot suffices. Memory is capped and
    failures propagate without retries. Counts exist only in process memory.
    """
    circuit = build_circuit()  # Includes the required pre-transpilation check.
    simulator = AerSimulator(
        method="statevector", max_memory_mb=2048, max_parallel_threads=2
    )
    compiled = transpile(
        circuit,
        simulator,
        basis_gates=BASIS_GATES,
        optimization_level=1,
        seed_transpiler=SEED_TRANSPILER,
    )
    result = simulator.run(compiled, shots=SHOTS).result()
    if not result.success:
        raise RuntimeError("Aer failed to execute the Tier 1 circuit")
    counts = result.get_counts(compiled)
    if len(counts) != 1 or sum(counts.values()) != SHOTS:
        raise RuntimeError("Unexpected Tier 1 measurement result")
    return measurement_to_key(next(iter(counts)))


def solve() -> str:
    """Recover the key on Aer and decrypt the official Tier 1 ciphertext."""
    if __package__:
        from .classical import decrypt_tier1
    else:
        # The official checker loads solution.py by path and adds its directory.
        from classical import decrypt_tier1

    key = recover_key()
    plaintext = decrypt_tier1(key, load_locked(1)["ciphertext_hex"])
    if not isinstance(plaintext, str):
        raise TypeError("The classical module must return plaintext as a string")
    return plaintext
