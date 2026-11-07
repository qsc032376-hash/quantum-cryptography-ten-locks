"""Tier 6 first-byte predicate, built only from the public cipher description.

The known byte is Q. Moving its public inverse permutation/S-box to the
comparison constant is equivalent to a full first-byte decryption check; it
does not solve for, enumerate, or store any key. Every key-dependent operation
is a reversible mask circuit. No challenge files are read by this module.
"""

from math import pi

from qiskit import QuantumCircuit
from qiskit.synthesis import synth_mcx_n_clean_m15, synth_mcx_n_dirty_i15

from common.toy_cipher import inverse_permute, inverse_sbox_layer
from tier06 import helper


KEY_BITS = 14
WORK_BITS = 8
MAIN_QUBITS = KEY_BITS + WORK_BITS
PILOT_QUBITS = MAIN_QUBITS + 1
KEY_QUBITS = tuple(range(KEY_BITS))
WORK_QUBITS = tuple(range(KEY_BITS, MAIN_QUBITS))
PHASE_TARGET_QUBIT = WORK_QUBITS[-1]
FLAG_QUBIT = MAIN_QUBITS
ORACLE_NAME = "tier06_phase_oracle"
BIT_ORACLE_NAME = "tier06_bit_oracle"
DIFFUSER_NAME = "tier06_diffuser"

# The inverse image of the PUBLIC known plaintext byte, never a key value.
_KNOWN_INPUT_BYTE = inverse_sbox_layer(inverse_permute(ord("Q")))


def _mask_target(ciphertext_byte: int) -> int:
    if type(ciphertext_byte) is not int:
        raise TypeError("ciphertext_byte must be an integer, not bool")
    if not 0 <= ciphertext_byte <= 255:
        raise ValueError("ciphertext_byte must be between 0 and 255")
    # For byte i=0, key rotation and ROUND_CONSTANT*i are both zero.
    return ciphertext_byte ^ _KNOWN_INPUT_BYTE


def _build_mask(n_qubits: int) -> QuantumCircuit:
    """XOR public mask(k, 0) into the work register, preserving the key."""
    circuit = QuantumCircuit(n_qubits, name="tier06_mask")
    for operation, *indices in helper.mask_gates(KEY_BITS):
        if operation == "cx":
            key_bit, work_bit = indices
            circuit.cx(KEY_QUBITS[key_bit], WORK_QUBITS[work_bit])
        elif operation == "ccx":
            key_a, key_b, work_bit = indices
            circuit.ccx(KEY_QUBITS[key_a], KEY_QUBITS[key_b], WORK_QUBITS[work_bit])
        else:
            raise ValueError("Unsupported operation in the public mask description")
    return circuit


def _comparison_x(circuit: QuantumCircuit, expected_mask: int):
    """Convert equality to the public mask constant into all-one controls."""
    for bit, wire in enumerate(WORK_QUBITS):
        if not expected_mask & (1 << bit):
            circuit.x(wire)


def _append_dirty_mcx(circuit: QuantumCircuit, controls: tuple[int, ...], target: int):
    """Apply an exact MCX, returning borrowed key wires even if entangled."""
    synthesized = synth_mcx_n_dirty_i15(
        len(controls), relative_phase=False, action_only=False
    )
    dirty_count = synthesized.num_qubits - len(controls) - 1
    if not 0 <= dirty_count <= len(KEY_QUBITS):
        raise RuntimeError("The MCX synthesis needs too many borrowed key wires")
    circuit.append(
        synthesized.to_gate(label=f"exact_mcx{len(controls)}_dirty"),
        controls + (target,) + KEY_QUBITS[:dirty_count],
    )


def build_phase_oracle(ciphertext_byte: int) -> QuantumCircuit:
    """Return the 22-qubit first-byte-Q phase oracle with clean work.

    Starting with zero work, mask(k,0) is computed and compared to a public
    constant. An MCZ on the eight work bits marks exactly the matching keys.
    Its target is work[7], shared with the work register rather than an extra
    flag. Five key wires are borrowed as dirty MCX7 ancillas and restored.
    The comparison normalization and the full mask computation are undone.
    """
    target_mask = _mask_target(ciphertext_byte)
    mask = _build_mask(MAIN_QUBITS)
    circuit = QuantumCircuit(MAIN_QUBITS, name=ORACLE_NAME)
    circuit.compose(mask, inplace=True)
    _comparison_x(circuit, target_mask)
    circuit.h(PHASE_TARGET_QUBIT)
    _append_dirty_mcx(circuit, WORK_QUBITS[:-1], PHASE_TARGET_QUBIT)
    circuit.h(PHASE_TARGET_QUBIT)
    _comparison_x(circuit, target_mask)
    circuit.compose(mask.inverse(), inplace=True)
    return circuit


def build_bit_oracle(ciphertext_byte: int) -> QuantumCircuit:
    """Return a 23-qubit oracle XORing the same Q predicate into flag[22].

    The work register must start at zero and is restored. The flag may start
    at either value, or be in a superposition: flag -> flag XOR predicate(k).
    Six key wires act as exact dirty MCX8 ancillas and are returned unchanged.
    The pilot circuit can therefore measure this flag without retaining work.
    """
    target_mask = _mask_target(ciphertext_byte)
    mask = _build_mask(PILOT_QUBITS)
    circuit = QuantumCircuit(PILOT_QUBITS, name=BIT_ORACLE_NAME)
    circuit.compose(mask, inplace=True)
    _comparison_x(circuit, target_mask)
    _append_dirty_mcx(circuit, WORK_QUBITS, FLAG_QUBIT)
    _comparison_x(circuit, target_mask)
    circuit.compose(mask.inverse(), inplace=True)
    return circuit


def build_diffuser() -> QuantumCircuit:
    """Return 2|+><+| - I on the 14 key qubits, restoring clean work.

    Called only after the phase oracle has uncomputed work, this reflection
    borrows six zero work qubits for an exact MCX13. The public synthesis's
    ancilla count is derived from its width, not guessed or hard-coded.
    """
    synthesized = synth_mcx_n_clean_m15(KEY_BITS - 1)
    clean_count = synthesized.num_qubits - KEY_BITS
    if not 0 <= clean_count <= len(WORK_QUBITS):
        raise RuntimeError("The diffuser synthesis needs too many clean work qubits")

    circuit = QuantumCircuit(MAIN_QUBITS, name=DIFFUSER_NAME)
    circuit.h(KEY_QUBITS)
    circuit.x(KEY_QUBITS)
    target = KEY_QUBITS[-1]
    circuit.h(target)
    circuit.append(
        synthesized.to_gate(label="exact_mcx13_clean"),
        KEY_QUBITS + WORK_QUBITS[:clean_count],
    )
    circuit.h(target)
    circuit.x(KEY_QUBITS)
    circuit.h(KEY_QUBITS)
    circuit.global_phase = pi
    return circuit
