"""Tier 2 BB84 receiver: use each public Channel exactly once.

All basis choices precede disclosure. No channel private state is inspected;
only receive_all(), finish(), n_qubits, and the public measurement log are used.
The fixed, data-independent seed makes this educational experiment repeatable;
it is not a production cryptographic random-number generator.
"""

from fractions import Fraction
import random

from qiskit import QuantumCircuit

from common import load_locked, xor_bytes
from tier02 import helper


BASIS_SEED = 20261107


def build_circuit(basis=1):
    """Build Bob's one-qubit measurement, defaulting to the X-basis diagram.

    The supplied Channel prepares Alice's incoming qubit and runs Aer. Bob
    must not replace that preparation with an independently initialized state.
    """
    if type(basis) is not int or basis not in (0, 1):
        raise ValueError("Basis must be 0 (Z) or 1 (X)")
    circuit = QuantumCircuit(1, 1, name="bob_x" if basis else "bob_z")
    if basis:
        circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def analyze_link(bob_bases, measured_bits, public_data):
    """Sift measured data; return reconciliation inputs and nonsecret statistics.

    Only matching-basis check positions contribute to BOTH the QBER numerator
    and denominator. Every public check position is excluded from key material.
    Original qubit indices are retained for the public reconciliation helper.
    """
    alice_bases = public_data["alice_bases"]
    n_qubits = len(bob_bases)
    if not n_qubits or len(measured_bits) != n_qubits or len(alice_bases) != n_qubits:
        raise ValueError("Channel measurements and basis arrays must have equal lengths")
    if any(bit not in (0, 1) for values in (bob_bases, measured_bits, alice_bases) for bit in values):
        raise ValueError("Channel bases and measurement values must be binary")

    # JSON public check indices may be strings; normalize them once.
    check_bits = {}
    for raw_index, bit in public_data["check_bits"].items():
        if type(raw_index) is int:
            index = raw_index
        elif isinstance(raw_index, str) and raw_index.isdecimal():
            index = int(raw_index)
        else:
            raise ValueError("Invalid public check index")
        if index in check_bits or not 0 <= index < n_qubits or bit not in (0, 1):
            raise ValueError("Invalid public check set")
        check_bits[index] = bit

    matched = [i for i in range(n_qubits) if bob_bases[i] == alice_bases[i]]
    check_indices = [i for i in matched if i in check_bits]
    if not check_indices:
        raise ValueError("No matching-basis public check samples; do not remeasure")
    errors = sum(measured_bits[i] != check_bits[i] for i in check_indices)
    key_bits = {i: measured_bits[i] for i in matched if i not in check_bits}
    stats = {
        "qubits": n_qubits,
        "z_basis_measurements": bob_bases.count(0),
        "x_basis_measurements": bob_bases.count(1),
        "sifted_bits": len(matched),
        "check_samples": len(check_indices),
        "check_errors": errors,
        "qber": errors / len(check_indices),
        "retained_key_bits": len(key_bits),
    }
    return key_bits, stats


def choose_clean_link(reports):
    """Select the lower measured QBER; fail on absent or tied evidence.

    A lower observed error rate is the selection criterion under this tier's
    promise of one clean link. It is not a general proof of channel security.
    """
    if len(reports) != 2:
        raise ValueError("Tier 2 requires exactly two link reports")
    rates = {}
    for name, stats in reports.items():
        samples, errors = stats["check_samples"], stats["check_errors"]
        if samples <= 0 or not 0 <= errors <= samples:
            raise ValueError("Invalid public check sample counts")
        rates[name] = Fraction(errors, samples)
    ordered = sorted(rates, key=rates.get)
    if rates[ordered[0]] == rates[ordered[1]]:
        raise RuntimeError("QBER is tied; no clean link identified and no retry allowed")
    return ordered[0]


def recover_key_with_diagnostics():
    """Recover bytes through actual Channel measurements and public reconcile.

    Create one Channel per link, measure each index once, then disclose bases.
    The diagnostics contain only aggregate sample counts/QBER, never measured
    values or the reconciliation inputs/outputs. Failures propagate, no retries.
    """
    if any(entry[0] in helper.LINKS for entry in helper.Channel.log):
        raise RuntimeError("These links were already measured in this process")
    channels = {name: helper.Channel(name) for name in helper.LINKS}
    rng = random.Random(BASIS_SEED)
    bases = {
        name: [rng.getrandbits(1) for _ in range(channel.n_qubits)]
        for name, channel in channels.items()
    }
    reports = {}
    candidates = {}
    # Channel copies each receiver into its log and composes it with a fresh input.
    # Reuse the two unmodified templates; each position still gets its own Aer shot.
    receivers = (build_circuit(0), build_circuit(1))
    for name, channel in channels.items():
        circuits = [receivers[basis] for basis in bases[name]]
        measured_bits = channel.receive_all(circuits)
        public_data = channel.finish()
        key_bits, stats = analyze_link(bases[name], measured_bits, public_data)
        reports[name] = stats
        candidates[name] = (key_bits, public_data["reconcile"])

    selected = choose_clean_link(reports)
    key_bits, reconciliation = candidates[selected]
    key = helper.reconcile(key_bits, reconciliation)
    if not isinstance(key, bytes) or not key:
        raise RuntimeError("Public reconciliation did not return nonempty key bytes")
    return key, {
        "basis_seed": BASIS_SEED,
        "links": reports,
        "selected_link": selected,
        "measurement_circuits": sum(stats["qubits"] for stats in reports.values()),
        "reconcile_calls": 1,
    }


def recover_key():
    """Return the measured/reconciled key without printing or persisting it."""
    key, _ = recover_key_with_diagnostics()
    return key


def solve() -> str:
    """Run the real receiver and return the plaintext via official XOR helpers."""
    key = recover_key()
    ciphertext = bytes.fromhex(load_locked(2)["ciphertext_hex"])
    return xor_bytes(ciphertext, key).decode("utf-8")
