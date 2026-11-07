"""Synthetic checks of ancilla-free native-MCX modular compilation.

Only small artificial moduli are used. No real Tier 9 modulus is factored,
no order is computed, and no challenge ciphertext or order-finding data is read.
"""

import math
import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from submissions.team3.tier09 import modular


SCORING_BASIS = ["rz", "sx", "x", "cx"]
SMALL_CASES = ((2, 5, 3), (3, 7, 3), (2, 15, 4), (7, 15, 4), (1, 15, 4))


def expected_basis_output(value, multiplier, modulus, width):
    control = value & 1
    work = value >> 1
    output = multiplier * work % modulus if control and work < modulus else work
    return control | (output << 1)


def small_expected_matrix(multiplier, modulus, width):
    dimension = 1 << (width + 1)
    expected = np.zeros((dimension, dimension), dtype=complex)
    for value in range(dimension):
        expected[expected_basis_output(value, multiplier, modulus, width), value] = 1
    return expected


class NativeModularTests(unittest.TestCase):
    def test_small_complete_unitaries_match_full_positive_phase_permutations(self):
        for multiplier, modulus, width in SMALL_CASES:
            with self.subTest(multiplier=multiplier, modulus=modulus):
                circuit = modular.build_controlled_multiplier(multiplier, modulus, width)
                self.assertEqual((circuit.num_qubits, circuit.num_clbits), (width + 1, 0))
                actual = Operator(circuit).data
                expected = small_expected_matrix(multiplier, modulus, width)
                self.assertTrue(
                    np.allclose(actual, expected, rtol=1e-10, atol=1e-10),
                    "Controlled modular mapping or its relative phase is incorrect",
                )
                self.assertTrue(np.allclose(actual.conj().T @ actual, np.eye(len(actual)), atol=1e-10))

    def test_inverse_matches_explicit_artificial_inverse_multiplier(self):
        # 7*13 == 1 (mod 15): a fixed synthetic inverse, not order finding.
        circuit = modular.build_controlled_multiplier(7, 15, 4)
        actual = Operator(circuit.inverse()).data
        expected = small_expected_matrix(13, 15, 4)
        self.assertTrue(np.allclose(actual, expected, rtol=1e-10, atol=1e-10))

    def test_seven_work_bit_gate_sequence_preserves_every_padding_encoding(self):
        width, multiplier, modulus = 7, 7, 15
        circuit = modular.build_controlled_multiplier(multiplier, modulus)
        self.assertEqual(circuit.num_qubits, 8)  # External control plus seven work; no extras.
        gates = []
        for item in circuit.data:
            self.assertIn(item.operation.name, {"cx", "ccx", "mcx"})
            wires = [circuit.find_bit(bit).index for bit in item.qubits]
            controls, target = wires[:-1], wires[-1]
            self.assertIn(0, controls)
            self.assertNotEqual(target, 0)
            self.assertNotIn(target, controls)
            self.assertEqual(item.operation.ctrl_state, (1 << len(controls)) - 1)
            gates.append((sum(1 << bit for bit in controls), target))

        # Simulate only known classical controlled-X truth tables. This checks
        # all 128 artificial work encodings and both external-control values,
        # including high-bit unused encodings, without constructing a large matrix.
        for initial in range(1 << (width + 1)):
            value = initial
            for controls, target in gates:
                if value & controls == controls:
                    value ^= 1 << target
            self.assertEqual(value, expected_basis_output(initial, multiplier, modulus, width))
        stats = modular.public_compilation_stats(multiplier, modulus, width)
        self.assertEqual(stats["gate_count"], len(gates))
        self.assertEqual(stats["normalizing_x_count"], 0)

    def test_native_aer_and_scoring_basis_agree_on_coherence_and_uncomputation(self):
        width, multiplier, modulus = 7, 7, 15
        controlled = modular.build_controlled_multiplier(multiplier, modulus, width)
        prepared = QuantumCircuit(width + 1)
        prepared.h(0)
        prepared.x(1)
        prepared.x(2)  # Work value 3 in one branch.
        prepared.h(3)
        prepared.p(math.pi / 2, 3)
        for target in range(4, width + 1):
            prepared.cx(3, target)  # The other branch is unused encoding 127.

        forward = prepared.copy()
        forward.compose(controlled, inplace=True)
        roundtrip = forward.copy()
        roundtrip.compose(controlled.inverse(), inplace=True)
        forward_indices, original_indices, expected = [], [], []
        for control in (0, 1):
            for work, amplitude in ((3, 0.5), (127, 0.5j)):
                value = control | (work << 1)
                original_indices.append(value)
                forward_indices.append(expected_basis_output(value, multiplier, modulus, width))
                expected.append(amplitude)

        simulator = AerSimulator(
            method="statevector", max_memory_mb=128,
            max_parallel_threads=2, max_parallel_experiments=1,
        )
        native = transpile(
            [forward, roundtrip], simulator, optimization_level=0, seed_transpiler=12345
        )
        self.assertTrue(
            any(circuit.count_ops().get("mcx", 0) > 0 for circuit in native),
            "Aer compilation unexpectedly removed every native MCX gate",
        )
        scored = transpile(
            [forward, roundtrip], basis_gates=SCORING_BASIS,
            optimization_level=1, seed_transpiler=12345,
        )
        for circuit in scored:
            self.assertTrue(set(circuit.count_ops()).issubset(SCORING_BASIS))
        circuits = [*native, *scored]
        for circuit, indices in zip(
            circuits, [forward_indices, original_indices] * 2, strict=True
        ):
            circuit.save_amplitudes(indices, label="selected_amplitudes")

        result = simulator.run(circuits, shots=1).result()
        self.assertTrue(result.success, "Synthetic native/basis Aer batch failed")
        observed = []
        for index in range(4):
            amplitudes = np.asarray(result.data(index)["selected_amplitudes"], dtype=complex)
            self.assertTrue(
                np.allclose(amplitudes, expected, rtol=1e-8, atol=1e-8),
                "Synthetic coherence, padding, or inverse output is incorrect",
            )
            self.assertAlmostEqual(float(np.vdot(amplitudes, amplitudes).real), 1.0, places=7)
            observed.append(amplitudes)
        self.assertTrue(np.allclose(observed[0], observed[2], rtol=1e-8, atol=1e-8))
        self.assertTrue(np.allclose(observed[1], observed[3], rtol=1e-8, atol=1e-8))

    def test_invalid_inputs_fail_without_building_a_nonpermutation(self):
        for arguments in ((3, 15, 4), (0, 7, 3), (2, 7, 2), (2, 5, 0)):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                modular.build_controlled_multiplier(*arguments)
        for arguments in ((True, 5, 3), (2, True, 3), (2, 5, True), (2.0, 5, 3)):
            with self.subTest(arguments=arguments), self.assertRaises(TypeError):
                modular.build_controlled_multiplier(*arguments)


if __name__ == "__main__":
    unittest.main()
