"""Public reversible Tier 5 cipher checks and the Grover reflection.

This module constructs gates from the published mask, S-box and permutation.
It does not read challenge data, search keys, or inspect a hidden oracle.
All work qubits and the comparison flag must start in zero and are restored.
"""

from math import pi

from qiskit import QuantumCircuit
from qiskit.synthesis import synth_mcx_n_clean_m15, synth_mcx_n_dirty_i15

from common.toy_cipher import inverse_permute, inverse_sbox_layer
from tier05 import helper


KEY_BITS = 10
N_QUBITS = 19
KEY_QUBITS = tuple(range(KEY_BITS))
WORK_QUBITS = tuple(range(KEY_BITS, KEY_BITS + 8))
FLAG_QUBIT = 18
ORACLE_NAME = "tier05_phase_oracle"
DIFFUSER_NAME = "tier05_diffuser"


def build_byte_transform(ciphertext_byte: int, byte_index: int) -> QuantumCircuit:
    """Compute one decrypted byte into initially zero work qubits.

    At return, WORK_QUBITS[j] contains plaintext bit j. The data bit j used
    by the mask and S-box is mapped to WORK_QUBITS[PERM[j]] throughout, so
    the final public permutation requires no physical SWAP gates. This is
    a preparation unitary for zero work: its inverse restores those zeros.

    Byte i uses the key rotated left by 3*i: rotated bit j is original key
    bit (j - 3*i) mod 10. The flag is untouched. No key value is computed
    classically; all key-dependent operations are reversible quantum gates.
    """
    if type(ciphertext_byte) is not int:
        raise TypeError("ciphertext_byte must be an integer, not bool")
    if not 0 <= ciphertext_byte <= 255:
        raise ValueError("ciphertext_byte must be between 0 and 255")
    if type(byte_index) is not int:
        raise TypeError("byte_index must be an integer, not bool")
    if byte_index < 0:
        raise ValueError("byte_index must be nonnegative")

    circuit = QuantumCircuit(N_QUBITS, name=f"tier05_byte_{byte_index}")
    data = tuple(WORK_QUBITS[helper.PERM[j]] for j in range(8))
    shift = (3 * byte_index) % KEY_BITS
    rotated_key = tuple(KEY_QUBITS[(j - shift) % KEY_BITS] for j in range(KEY_BITS))

    initial_byte = ciphertext_byte ^ ((helper.ROUND_CONSTANT * byte_index) % 256)
    for bit in range(8):
        if initial_byte & (1 << bit):
            circuit.x(data[bit])

    for operation, *indices in helper.mask_gates(KEY_BITS):
        if operation == "cx":
            key_bit, data_bit = indices
            circuit.cx(rotated_key[key_bit], data[data_bit])
        elif operation == "ccx":
            key_a, key_b, data_bit = indices
            circuit.ccx(rotated_key[key_a], rotated_key[key_b], data[data_bit])
        else:
            raise ValueError("Unsupported operation in the public mask description")

    for offset in (0, 4):
        for operation, *indices in helper.SBOX_GATES:
            wires = tuple(data[offset + index] for index in indices)
            if operation == "x":
                circuit.x(wires[0])
            elif operation == "cx":
                circuit.cx(*wires)
            elif operation == "ccx":
                circuit.ccx(*wires)
            else:
                raise ValueError("Unsupported operation in the public S-box description")
    return circuit


def _comparison_x(circuit: QuantumCircuit, expected_byte: int):
    """Turn equality to a known byte into an all-ones control condition."""
    for bit, wire in enumerate(WORK_QUBITS):
        if not expected_byte & (1 << bit):
            circuit.x(wire)


def _dirty_comparison_gate():
    """An exact MCX8 with six borrowed key wires, restored even if entangled."""
    synthesized = synth_mcx_n_dirty_i15(
        len(WORK_QUBITS), relative_phase=False, action_only=False
    )
    dirty_count = synthesized.num_qubits - len(WORK_QUBITS) - 1
    if not 0 <= dirty_count <= len(KEY_QUBITS):
        raise RuntimeError("The MCX synthesis needs more borrowed key wires than available")
    # The synthesis order is controls, target, then borrowed ancillas.
    wires = WORK_QUBITS + (FLAG_QUBIT,) + KEY_QUBITS[:dirty_count]
    return synthesized.to_gate(label="exact_mcx8_dirty"), wires


def _build_mask_transform(byte_index: int) -> QuantumCircuit:
    """XOR the rotated-key mask into work; omit the public byte constant.

    Work bit j holds mask bit j (before S-box/PERM). All key-dependent
    operations remain reversible quantum CX/CCX gates. This exact XOR map
    preserves the key and flag and works on arbitrary work-register inputs.
    """
    if type(byte_index) is not int:
        raise TypeError("byte_index must be an integer, not bool")
    if byte_index < 0:
        raise ValueError("byte_index must be nonnegative")
    circuit = QuantumCircuit(N_QUBITS, name=f"tier05_mask_{byte_index}")
    shift = (3 * byte_index) % KEY_BITS
    rotated_key = tuple(KEY_QUBITS[(j - shift) % KEY_BITS] for j in range(KEY_BITS))
    for operation, *indices in helper.mask_gates(KEY_BITS):
        if operation == "cx":
            key_bit, work_bit = indices
            circuit.cx(rotated_key[key_bit], WORK_QUBITS[work_bit])
        elif operation == "ccx":
            key_a, key_b, work_bit = indices
            circuit.ccx(rotated_key[key_a], rotated_key[key_b], WORK_QUBITS[work_bit])
        else:
            raise ValueError("Unsupported operation in the public mask description")
    return circuit


def build_phase_oracle(ciphertext: bytes) -> QuantumCircuit:
    """Apply -1 iff the first two decrypted bytes are QC, with clean work.

    Register layout is key[0:10], work[10:18], flag[18]. The flag starts
    at zero; no phase-kickback preparation of a separate |-> qubit is needed.
    First compute the Q comparison into the flag and uncompute its byte.
    Then compute C and phase-flip only when both comparisons hold. Finally
    uncompute C and reverse the entire first comparison, restoring all work.

    For each PUBLIC target byte b, decrypt(c,i)==b is equivalent to
    mask(rot_i(key)) == c XOR RC_i XOR S^-1(PERM^-1(b)). Only those public
    constants are evaluated classically. Folding the S-box/PERM out of the
    comparison preserves the full phase action on zero work/flag, including
    arbitrary key superpositions; it does not search for or encode any key.
    The general build_byte_transform API remains unchanged.
    """
    if not isinstance(ciphertext, bytes):
        raise TypeError("ciphertext must be bytes")
    if len(ciphertext) < 2:
        raise ValueError("The Tier 5 oracle requires at least two ciphertext bytes")

    targets = tuple(
        ciphertext[index]
        ^ ((helper.ROUND_CONSTANT * index) % 256)
        ^ inverse_sbox_layer(inverse_permute(known_byte))
        for index, known_byte in enumerate(b"QC")
    )
    first_byte = _build_mask_transform(0)
    second_byte = _build_mask_transform(1)
    comparison_gate, comparison_wires = _dirty_comparison_gate()

    first_check = QuantumCircuit(N_QUBITS, name="tier05_first_byte_check")
    first_check.compose(first_byte, inplace=True)
    _comparison_x(first_check, targets[0])
    first_check.append(comparison_gate, comparison_wires)
    _comparison_x(first_check, targets[0])
    first_check.compose(first_byte.inverse(), inplace=True)

    circuit = QuantumCircuit(N_QUBITS, name=ORACLE_NAME)
    circuit.compose(first_check, inplace=True)
    circuit.compose(second_byte, inplace=True)
    _comparison_x(circuit, targets[1])
    circuit.h(FLAG_QUBIT)
    circuit.append(comparison_gate, comparison_wires)
    circuit.h(FLAG_QUBIT)
    _comparison_x(circuit, targets[1])
    circuit.compose(second_byte.inverse(), inplace=True)
    circuit.compose(first_check.inverse(), inplace=True)
    return circuit


def build_diffuser() -> QuantumCircuit:
    """Reflect key amplitudes by 2|+><+| - I, restoring zero work qubits.

    The preceding oracle must have restored its work/flag. Four work qubits
    are then available as clean MCX9 ancillas under the pinned Qiskit version.
    The final global pi phase selects the conventional positive reflection.
    """
    synthesized = synth_mcx_n_clean_m15(KEY_BITS - 1)
    clean_count = synthesized.num_qubits - KEY_BITS
    if not 0 <= clean_count <= len(WORK_QUBITS):
        raise RuntimeError("The diffuser synthesis needs too many clean work qubits")

    circuit = QuantumCircuit(N_QUBITS, name=DIFFUSER_NAME)
    circuit.h(KEY_QUBITS)
    circuit.x(KEY_QUBITS)
    target = KEY_QUBITS[-1]
    circuit.h(target)
    circuit.append(
        synthesized.to_gate(label="exact_mcx9_clean"),
        KEY_QUBITS + WORK_QUBITS[:clean_count],
    )
    circuit.h(target)
    circuit.x(KEY_QUBITS)
    circuit.h(KEY_QUBITS)
    circuit.global_phase = pi
    return circuit
