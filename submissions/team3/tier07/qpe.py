"""Tier 7 QPE construction, retaining the complete controlled-unitary phase.

The public rules permit matrix multiplication to build integer powers of U.
The matrix here is used only for that purpose: no eigenvalues, eigenvectors,
angles, determinant phases, or circuit phase attributes are inspected. This
module never loads challenge files or prints/serializes matrices or results.
"""

from math import pi

from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Operator


PHASE_BITS = 14
_POWER_PREFIX = "tier07_controlled_U_power_"


def _validate_width(width: int):
    if type(width) is not int:
        raise TypeError("The phase-register width must be an integer, not bool")
    if width < 1:
        raise ValueError("The phase-register width must be positive")


def _validate_one_qubit(circuit, name):
    if not isinstance(circuit, QuantumCircuit):
        raise TypeError(f"{name} must be a QuantumCircuit")
    if circuit.num_qubits != 1 or circuit.num_clbits != 0:
        raise ValueError(f"{name} must have one qubit and no classical bits")


def build_inverse_qft(width: int, *, reverse_input: bool = True) -> QuantumCircuit:
    """Return the inverse-QFT core, with optional input bit reversal.

    The forward DFT convention is exp(+2*pi*i*x*y / 2**width). Initial
    swaps are the inverse of the final swaps in the full forward QFT.
    Without swaps, the caller must reverse the phase-register inputs.
    """
    _validate_width(width)
    circuit = QuantumCircuit(width, name="tier07_inverse_qft")
    if reverse_input:
        for bit in range(width // 2):
            circuit.swap(bit, width - 1 - bit)
    for target in range(width):
        for earlier in range(target):
            circuit.cp(-pi / (1 << (target - earlier)), target, earlier)
        circuit.h(target)
    return circuit


def _build_phase_register(
    unitary: QuantumCircuit,
    eigenstate: QuantumCircuit,
    phase_bits: int,
    name: str,
    *,
    reverse_controls: bool = False,
) -> QuantumCircuit:
    """Prepare the supplied eigenstate and controlled powers, without readout."""
    _validate_width(phase_bits)
    _validate_one_qubit(unitary, "unitary")
    _validate_one_qubit(eigenstate, "eigenstate")

    target = phase_bits
    circuit = QuantumCircuit(phase_bits + 1, phase_bits, name=name)
    preparation = eigenstate.to_gate(label="supplied eigenstate")
    preparation.name = "tier07_eigenstate_preparation"
    circuit.append(preparation, [target])
    circuit.h(range(phase_bits))

    # Operator includes the circuit's complete complex scalar. Never normalize
    # it away: after controlling U that scalar becomes a measurable phase.
    power_matrix = Operator(unitary).data
    for bit in range(phase_bits):
        exponent = 1 << bit
        controlled = UnitaryGate(power_matrix, label=f"U^{exponent}").control(
            1, annotated=False
        )
        controlled.name = f"{_POWER_PREFIX}{exponent}"
        control_bit = phase_bits - 1 - bit if reverse_controls else bit
        circuit.append(controlled, [control_bit, target])
        if bit + 1 < phase_bits:
            # Out-of-place multiplication leaves all previously made gates
            # intact and needs exactly phase_bits-1 repeated squarings.
            power_matrix = power_matrix @ power_matrix
    return circuit


def build_qpe_circuit(
    unitary: QuantumCircuit,
    eigenstate: QuantumCircuit,
    phase_bits: int = PHASE_BITS,
) -> QuantumCircuit:
    """Return QPE with q[n-1-j] controlling U**(2**j), then q[j] -> c[j].

    The final qubit holds the supplied V|1> state; do not add a separate X
    preparation. For a phase k/2**phase_bits, the counts key c[n-1]...c[0]
    directly represents k in binary. The reversed controls absorb the
    inverse QFT's input swaps; no measured-string reversal is required.
    """
    circuit = _build_phase_register(
        unitary, eigenstate, phase_bits, "tier07_qpe", reverse_controls=True
    )
    circuit.append(
        build_inverse_qft(phase_bits, reverse_input=False).to_gate(),
        range(phase_bits),
    )
    circuit.measure(range(phase_bits), range(phase_bits))
    return circuit


def build_phase_check_circuit(
    unitary: QuantumCircuit,
    eigenstate: QuantumCircuit,
    phase: int,
    phase_bits: int = PHASE_BITS,
) -> QuantumCircuit:
    """Validate a measured phase integer by cancelling its control phases.

    Use only a candidate recovered by measurement for real challenge data.
    This circuit has no inverse QFT. Correct cancellation followed by H gives
    all zeros; for any different integer on the same exact phase grid, at
    least one control has residual phase pi and deterministically yields 1.
    """
    _validate_width(phase_bits)
    if type(phase) is not int:
        raise TypeError("The measured phase candidate must be an integer, not bool")
    denominator = 1 << phase_bits
    if not 0 <= phase < denominator:
        raise ValueError("The measured phase candidate is outside the phase register")

    circuit = _build_phase_register(
        unitary, eigenstate, phase_bits, "tier07_phase_check"
    )
    for bit in range(phase_bits):
        residue = (phase * (1 << bit)) % denominator
        if residue:
            circuit.p(-2 * pi * residue / denominator, bit)
    circuit.h(range(phase_bits))
    circuit.measure(range(phase_bits), range(phase_bits))
    return circuit


def count_controlled_powers(circuit: QuantumCircuit) -> dict:
    """Count only our named outer power blocks; never inspect definitions.

    Exponents are the U powers, such as [1, 2, 4], in application order.
    Their sum is the equivalent number of base-U applications, distinct from
    the number of compressed, controlled powered gates actually appended.
    """
    if not isinstance(circuit, QuantumCircuit):
        raise TypeError("Expected a QuantumCircuit")
    exponents = []
    for instruction in circuit.data:
        name = instruction.operation.name
        if not name.startswith(_POWER_PREFIX):
            continue
        suffix = name[len(_POWER_PREFIX):]
        if not suffix.isdecimal():
            raise ValueError("Malformed controlled-U power block name")
        exponent = int(suffix)
        if exponent < 1 or exponent & (exponent - 1):
            raise ValueError("Controlled-U block exponents must be powers of two")
        exponents.append(exponent)
    return {
        "controlled_power_blocks": len(exponents),
        "equivalent_base_U_applications": sum(exponents),
        "exponents": exponents,
    }
