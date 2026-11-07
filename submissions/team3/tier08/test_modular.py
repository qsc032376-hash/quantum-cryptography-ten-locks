"""Small synthetic modular permutations, with exact controlled/dirty behavior.

Only artificial moduli 5, 7, and 15 are used. No Tier 8 challenge data, real
factorization, order finding, or candidate-key search is performed here.
"""

import math
import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from submissions.team3.tier08 import modular


SYNTHETIC_CASES = ((2, 5, 3), (3, 7, 3), (2, 15, 4), (7, 15, 4), (1, 15, 4))


def controlled_permutation_matrix(multiplier, modulus, work_bits, n_qubits):
    """Independent small truth table, including arbitrary dirty-wire inputs."""
    dimension = 1 << n_qubits
    matrix = np.zeros((dimension, dimension), dtype=complex)
    work_mask = ((1 << work_bits) - 1) << 1
    for basis in range(dimension):
        work = (basis & work_mask) >> 1
        output = multiplier * work % modulus if (basis & 1) and work < modulus else work
        mapped = (basis & ~work_mask) | (output << 1)
        matrix[mapped, basis] = 1.0
    return matrix


class ModularPermutationTests(unittest.TestCase):
    def test_small_tables_are_bijections_and_preserve_unused_encodings(self):
        for multiplier, modulus, width in SYNTHETIC_CASES:
            with self.subTest(modulus=modulus, multiplier=multiplier):
                table = modular.permutation_table(multiplier, modulus, width)
                expected = [
                    multiplier * value % modulus if value < modulus else value
                    for value in range(1 << width)
                ]
                self.assertEqual(table, expected)
                self.assertEqual(sorted(table), list(range(1 << width)))
                self.assertEqual(table[modulus:], list(range(modulus, 1 << width)))
                self.assertEqual(modular.permutation_table(1, modulus, width), list(range(1 << width)))

    def test_complete_controlled_unitary_has_no_relative_phases_or_dirty_changes(self):
        for multiplier, modulus, width in SYNTHETIC_CASES:
            with self.subTest(modulus=modulus, multiplier=multiplier):
                circuit = modular.build_controlled_multiplier(multiplier, modulus, width)
                dirty = modular.dirty_qubit_count(width)
                self.assertEqual(circuit.num_qubits, 1 + width + dirty)
                self.assertEqual(circuit.num_clbits, 0)
                self.assertLessEqual(circuit.num_qubits, 7)
                actual = Operator(circuit).data
                expected = controlled_permutation_matrix(
                    multiplier, modulus, width, circuit.num_qubits
                )
                self.assertTrue(
                    np.allclose(actual, expected, rtol=1e-10, atol=1e-10),
                    "Controlled permutation changed an output, relative phase, or dirty wire",
                )
                self.assertTrue(
                    np.allclose(actual.conj().T @ actual, np.eye(len(actual)), atol=1e-10),
                    "The artificial modular circuit is not unitary",
                )

    def test_inverse_matches_known_synthetic_inverse_multiplier(self):
        # 2*8 == 1 (mod 15); this is an explicit artificial inverse, not order finding.
        circuit = modular.build_controlled_multiplier(2, 15, 4)
        actual_inverse = Operator(circuit.inverse()).data
        expected_inverse = controlled_permutation_matrix(8, 15, 4, circuit.num_qubits)
        self.assertTrue(
            np.allclose(actual_inverse, expected_inverse, rtol=1e-10, atol=1e-10),
            "Inverse circuit differs from the artificial inverse modular permutation",
        )

    def test_coherent_control_and_dirty_ancillas_survive_forward_and_inverse(self):
        width, multiplier, modulus, input_work = 4, 7, 15, 3
        controlled = modular.build_controlled_multiplier(multiplier, modulus, width)
        dirty_start = width + 1
        self.assertGreaterEqual(modular.dirty_qubit_count(width), 2)
        prepared = QuantumCircuit(controlled.num_qubits)
        prepared.h(0)
        for bit in range(width):
            if (input_work >> bit) & 1:
                prepared.x(1 + bit)
        prepared.h(dirty_start)
        prepared.p(math.pi / 2, dirty_start)
        prepared.cx(0, dirty_start + 1)  # Entangle the second borrowed wire with control.

        forward = prepared.copy()
        forward.compose(controlled, inplace=True)
        roundtrip = forward.copy()
        roundtrip.compose(controlled.inverse(), inplace=True)
        output_indices, input_indices, expected = [], [], []
        for control in (0, 1):
            for dirty_low in (0, 1):
                dirty_value = dirty_low | (control << 1)
                common = control | (dirty_value << dirty_start)
                output_work = multiplier * input_work % modulus if control else input_work
                output_indices.append(common | (output_work << 1))
                input_indices.append(common | (input_work << 1))
                expected.append((1j ** dirty_low) / 2)
        forward.save_amplitudes(output_indices, label="selected_amplitudes")
        roundtrip.save_amplitudes(input_indices, label="selected_amplitudes")

        simulator = AerSimulator(
            method="statevector", max_memory_mb=128,
            max_parallel_threads=2, max_parallel_experiments=1,
        )
        compiled = transpile(
            [forward, roundtrip], simulator, optimization_level=0, seed_transpiler=12345
        )
        result = simulator.run(compiled, shots=1).result()
        self.assertTrue(result.success, "Synthetic modular Aer batch failed")
        for index in range(2):
            with self.subTest(circuit=index):
                amplitudes = np.asarray(result.data(index)["selected_amplitudes"], dtype=complex)
                self.assertTrue(
                    np.allclose(amplitudes, expected, rtol=1e-9, atol=1e-9),
                    "Coherent control/dirty amplitudes or inverse roundtrip are incorrect",
                )
                self.assertAlmostEqual(float(np.vdot(amplitudes, amplitudes).real), 1.0, places=8)

    def test_invalid_parameters_are_rejected_before_circuit_use(self):
        invalid_values = ((3, 15, 4), (0, 7, 3), (2, 7, 2), (2, 5, 0))
        for arguments in invalid_values:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    modular.permutation_table(*arguments)
                with self.assertRaises(ValueError):
                    modular.build_controlled_multiplier(*arguments)
        for arguments in ((True, 5, 3), (2, True, 3), (2, 5, True), (2.0, 5, 3)):
            with self.subTest(arguments=arguments), self.assertRaises(TypeError):
                modular.permutation_table(*arguments)


if __name__ == "__main__":
    unittest.main()
