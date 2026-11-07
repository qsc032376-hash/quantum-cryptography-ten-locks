"""Team 3 Tier 3: Deutsch--Jozsa with one measurement per opaque oracle.

The 24 key characters follow oracle order, 00 through 23. No recovered key,
per-oracle classification, measurement counts, or plaintext is printed/saved.
Youyang's shared classical module is not copied or reimplemented here.
"""

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import load_locked
from tier03 import helper


N_ORACLES = 24
N_INPUT_QUBITS = 6
TARGET_QUBIT = N_INPUT_QUBITS
N_QUBITS = N_INPUT_QUBITS + 1
SHOTS = 1
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 12345


def build_circuit(oracle_index: int = 0):
    """Return one 7-qubit/6-bit circuit; default oracle 0 is for diagrams.

    Prepare the unmeasured target in |->, query the supplied opaque oracle
    once, undo the input Hadamards, and measure q[j] into c[j]. The official
    oracle counter is called before any transpilation.
    """
    if type(oracle_index) is not int:
        raise TypeError("The oracle index must be an integer")
    if not 0 <= oracle_index < N_ORACLES:
        raise ValueError("The oracle index must be between 0 and 23")

    circuit = QuantumCircuit(
        N_QUBITS, N_INPUT_QUBITS, name=f"tier03_dj_{oracle_index:02d}"
    )
    circuit.x(TARGET_QUBIT)
    circuit.h(TARGET_QUBIT)
    circuit.h(range(N_INPUT_QUBITS))

    oracle = helper.build_oracle(oracle_index)
    if oracle.num_qubits != N_QUBITS or oracle.num_clbits != 0:
        raise ValueError("Tier 3 requires a 7-qubit oracle with no classical bits")
    circuit.append(oracle.to_gate(), range(N_QUBITS))

    circuit.h(range(N_INPUT_QUBITS))
    circuit.measure(range(N_INPUT_QUBITS), range(N_INPUT_QUBITS))
    if helper.count_oracle_calls(circuit) != 1:
        raise ValueError("Each Tier 3 circuit requires exactly one oracle application")
    return circuit


def measurement_to_bit(bitstring: str) -> str:
    """Map one measured c5...c0 string to a constant/balanced key character.

    On an ideal simulator, a promised constant oracle always yields all zeros,
    whereas a balanced oracle never does. The returned character belongs at
    the oracle's index, not at a reversed classical-bit position.
    """
    if not isinstance(bitstring, str):
        raise TypeError("The measurement must be a binary string")
    if len(bitstring) != N_INPUT_QUBITS or any(b not in "01" for b in bitstring):
        raise ValueError("Expected exactly 6 binary digits from one register")
    return "0" if bitstring == "0" * N_INPUT_QUBITS else "1"


def recover_key_bits() -> str:
    """Run 24 circuits in oracle order, with one shot and one query each.

    Only actual Aer measurement results determine the key characters. Oracle
    definitions/matrices are never inspected for classification. There are
    no automatic retries; simulator failures propagate to the caller.
    """
    circuits = [build_circuit(index) for index in range(N_ORACLES)]
    simulator = AerSimulator(
        method="statevector",
        max_memory_mb=256,
        max_parallel_threads=2,
        max_parallel_experiments=1,
    )
    compiled = transpile(
        circuits,
        simulator,
        basis_gates=BASIS_GATES,
        optimization_level=1,
        seed_transpiler=SEED_TRANSPILER,
        num_processes=1,
    )
    result = simulator.run(compiled, shots=SHOTS).result()
    if not result.success:
        raise RuntimeError("Aer failed to execute the Tier 3 circuits")
    if len(result.results) != N_ORACLES:
        raise RuntimeError("Expected 24 Tier 3 circuit results")

    key_bits = []
    for index in range(N_ORACLES):
        counts = result.get_counts(index)
        if len(counts) != 1 or sum(counts.values()) != SHOTS:
            raise RuntimeError("Unexpected Tier 3 measurement result")
        key_bits.append(measurement_to_bit(next(iter(counts))))
    return "".join(key_bits)


def solve() -> str:
    """Return decrypted text once Youyang's shared module is integrated.

    The verified interface is classical_keystream.decrypt(tier, key_bits,
    ciphertext_hex). Until that module is available, report an unfinished
    solution before loading an oracle or starting an unnecessary quantum job.
    """
    try:
        from submissions.team3.classical_keystream import decrypt
    except ModuleNotFoundError as error:
        if error.name != "submissions.team3.classical_keystream":
            raise
        raise NotImplementedError(
            "Integrate Youyang's submissions/team3/classical_keystream.py "
            "before running solve(); recover_key_bits() supports quantum-only validation"
        ) from None

    key_bits = recover_key_bits()
    plaintext = decrypt(3, key_bits, load_locked(3)["ciphertext_hex"])
    if not isinstance(plaintext, str):
        raise TypeError("The classical module must return plaintext as a string")
    return plaintext
