"""Two-register Fourier sampling of public modular exponent multiplication.

For a work value y below p, the reversible map multiplies y by g**x * A**z
modulo p. Padding encodings remain fixed. Constructing these public powers
does not recover an exponent or enumerate candidate discrete logarithms.
"""

from math import gcd

from qiskit import QuantumCircuit

from ..tier07.qpe import build_inverse_qft
from ..tier09.modular import build_controlled_multiplier


REGISTER_BITS = 6
WORK_BITS = 7
_G_POWER_PREFIX = "tier10_controlled_g_power_"
_A_POWER_PREFIX = "tier10_controlled_A_power_"


def _validate_parameters(p, g, A, register_bits, work_bits):
    for name, value in (
        ("p", p), ("g", g), ("A", A),
        ("register_bits", register_bits), ("work_bits", work_bits),
    ):
        if type(value) is not int:
            raise TypeError(f"{name} must be an integer, not bool")
    if register_bits < 1 or work_bits < 1:
        raise ValueError("Register widths must be positive")
    if p < 2 or p > (1 << work_bits):
        raise ValueError("The public modulus must be at least two and fit the work register")
    if not 1 <= g < p or not 1 <= A < p:
        raise ValueError("Public group elements must be nonzero canonical residues")
    if gcd(g, p) != 1 or gcd(A, p) != 1:
        raise ValueError("Public group elements must be invertible modulo p")


def build_exponent_mapping(
    p, g, A, register_bits=REGISTER_BITS, work_bits=WORK_BITS,
) -> QuantumCircuit:
    """Build the exact map on X, Z, work, with no initialization or measurement.

    X occupies wires 0..t-1, Z occupies t..2*t-1, and the work integer occupies
    2*t..2*t+w-1; all registers use little-endian integer encoding. No extra
    or borrowed ancillary wires are required. Each public multiplication is
    exact, including its control-branch phase and the padding-state identity.

    Primality and a particular subgroup order are public instance promises,
    not computed by this generic circuit builder. Identity group elements
    are accepted for synthetic boundary cases.
    """
    _validate_parameters(p, g, A, register_bits, work_bits)
    circuit = QuantumCircuit(2 * register_bits + work_bits, name="tier10_exponent_mapping")
    work = list(range(2 * register_bits, 2 * register_bits + work_bits))
    cache = {}
    for base, offset, prefix in (
        (g, 0, _G_POWER_PREFIX),
        (A, register_bits, _A_POWER_PREFIX),
    ):
        for bit in range(register_bits):
            exponent = 1 << bit
            multiplier = pow(base, exponent, p)
            if multiplier not in cache:
                cache[multiplier] = build_controlled_multiplier(multiplier, p, work_bits).to_gate()
            # Only the outer public-power block is named. Its native MCX
            # children retain their names, and cache entries remain unchanged.
            powered = cache[multiplier].copy(name=f"{prefix}{exponent}")
            circuit.append(powered, [offset + bit, *work])
    return circuit


def build_qpe_circuit(
    p, g, A, register_bits=REGISTER_BITS, work_bits=WORK_BITS,
) -> QuantumCircuit:
    """Prepare work |1>, sample both Fourier registers, and measure qj into cj.

    Both inverse QFTs include their bit-order swaps. The low t classical
    bits are X and the high t bits are Z; the displayed bitstring must not
    be reversed. With A=g**a, ideal frequency labels obey v=a*u modulo the
    group order. Finite-grid rounding requires separate classical validation.
    """
    mapping = build_exponent_mapping(p, g, A, register_bits, work_bits)
    circuit = QuantumCircuit(
        2 * register_bits + work_bits, 2 * register_bits, name="tier10_fourier_sampling",
    )
    circuit.x(2 * register_bits)
    circuit.h(range(2 * register_bits))
    # Composition keeps power blocks at the outer level for truthful counting.
    circuit.compose(mapping, inplace=True)
    inverse_qft = build_inverse_qft(register_bits).to_gate()
    circuit.append(inverse_qft, range(register_bits))
    circuit.append(inverse_qft, range(register_bits, 2 * register_bits))
    circuit.measure(range(2 * register_bits), range(2 * register_bits))
    return circuit


def count_group_powers(circuit) -> dict:
    """Count only our outer power blocks, without inspecting gate definitions.

    Equivalent base multiplications sum powers of g and A separately, then
    add their operation counts. This does not express A as a power of g or
    claim that both bases are the same oracle.
    """
    if not isinstance(circuit, QuantumCircuit):
        raise TypeError("circuit must be a QuantumCircuit")
    g_exponents = []
    A_exponents = []
    for instruction in circuit.data:
        name = instruction.operation.name
        for prefix, exponents in (
            (_G_POWER_PREFIX, g_exponents), (_A_POWER_PREFIX, A_exponents),
        ):
            if name.startswith(prefix):
                exponent = int(name[len(prefix):])
                if exponent < 1 or exponent & (exponent - 1):
                    raise ValueError("Invalid public group-power block")
                exponents.append(exponent)
                break
    return {
        "controlled_power_blocks": len(g_exponents) + len(A_exponents),
        "g_exponents": g_exponents,
        "A_exponents": A_exponents,
        "equivalent_base_multiplications": sum(g_exponents) + sum(A_exponents),
    }
