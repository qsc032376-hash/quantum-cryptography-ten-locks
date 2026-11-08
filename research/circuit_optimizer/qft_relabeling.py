"""Explicit boundary reversal detection and complete wire-permutation maps."""

from dataclasses import dataclass
from math import pi
from qiskit import QuantumCircuit
from qiskit.circuit import Gate
from qiskit.circuit.library import SwapGate


def inverse_qft(width):
    if type(width) is not int or width < 1:
        raise ValueError("Positive integer width required")
    circuit = QuantumCircuit(width)
    for j in range(width // 2):
        circuit.swap(j, width - 1 - j)
    for target in range(width):
        for earlier in range(target):
            circuit.cp(-pi / (1 << (target - earlier)), target, earlier)
        circuit.h(target)
    return circuit


def require_unitary(circuit):
    if circuit.num_clbits or any(not isinstance(i.operation, Gate) for i in circuit.data):
        raise ValueError("Unitary quantum-only blocks required")


def reversal_map(width, register):
    register = tuple(register)
    if (len(register) < 2 or len(set(register)) != len(register)
            or any(type(q) is not int or not 0 <= q < width for q in register)):
        raise ValueError("Distinct in-range register wires required")
    mapping = list(range(width))
    for a, b in zip(register, reversed(register)):
        mapping[a] = b
    return tuple(mapping)


def split_boundary_reversal(circuit, register, side="input"):
    """Recognize only a complete explicit leading/trailing SWAP layer.

    No hidden block expansion and no guesses from gate names. The rule is
    valid for any unitary core, including either Fourier sign convention.
    """
    require_unitary(circuit)
    register = tuple(register)
    permutation = reversal_map(circuit.num_qubits, register)
    if side not in ("input", "output"):
        raise ValueError("side must be input or output")
    size = len(register) // 2
    layer = list(circuit.data[:size] if side == "input" else circuit.data[-size:])
    expected = {frozenset((register[j], register[-1-j])) for j in range(size)}
    actual = []
    for item in layer:
        if item.operation.base_class is not SwapGate:
            raise ValueError("No explicit boundary reversal layer")
        actual.append(frozenset(circuit.find_bit(q).index for q in item.qubits))
    if len(actual) != size or len(set(actual)) != size or set(actual) != expected:
        raise ValueError("Incomplete or different boundary permutation")
    core = circuit.copy_empty_like()
    for item in (circuit.data[size:] if side == "input" else circuit.data[:-size]):
        core.append(item)
    return core, permutation


def conjugate_wires(circuit, permutation):
    """Conjugate every qarg, including targets and borrowed ancillas."""
    require_unitary(circuit)
    permutation = tuple(permutation)
    if (any(type(q) is not int for q in permutation)
            or sorted(permutation) != list(range(circuit.num_qubits))):
        raise ValueError("Expected a full wire permutation")
    result = circuit.copy_empty_like()
    for item in circuit.data:
        result.append(item.operation, [permutation[circuit.find_bit(q).index] for q in item.qubits])
    return result


@dataclass
class InputReversalPlan:
    circuit: QuantumCircuit
    required_input_permutation: tuple
    # candidate = original * R. Use R|psi> as input, or prove R|psi>=|psi>.


def absorb_input_reversal(prefix, transform, register):
    require_unitary(prefix)
    if prefix.num_qubits != transform.num_qubits:
        raise ValueError("Prefix and transform must have the same quantum wires")
    core, permutation = split_boundary_reversal(transform, register, "input")
    mapped = conjugate_wires(prefix, permutation)
    return InputReversalPlan(mapped.compose(core), permutation)


def absorb_output_reversal(transform, register, measurement_map):
    """Return core and q->c map; only immediate computational-basis readout.

    The caller supplies actual classical bit IDs, including multi-register
    offsets. This does not modify a preceding quantum block or a bitstring.
    """
    core, permutation = split_boundary_reversal(transform, register, "output")
    mapping = dict(measurement_map)
    if (any(type(q) is not int or not 0 <= q < transform.num_qubits for q in mapping)
            or any(type(c) is not int or c < 0 for c in mapping.values())
            or len(set(mapping.values())) != len(mapping)):
        raise ValueError("Measurement map must use distinct valid classical bits")
    return core, {permutation[q]: c for q, c in mapping.items()}
