"""Reversible-oracle tests using only public ToyCipher synthetic examples.

No challenge ciphertext is read and no search for an unknown key is performed.
Only selected amplitudes of a few artificial circuits are returned by Aer;
neither keys nor statevectors are printed by these tests.
"""

import math
import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common.toy_cipher import ToyCipher
from submissions.team3.tier05 import oracle


class SyntheticOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simulator = AerSimulator(
            method="statevector",
            max_memory_mb=512,
            max_parallel_threads=2,
            max_parallel_experiments=1,
        )

    @staticmethod
    def basis_key_circuit(key):
        circuit = QuantumCircuit(oracle.N_QUBITS)
        for bit in range(oracle.KEY_BITS):
            if (key >> bit) & 1:
                circuit.x(bit)
        return circuit

    def selected_amplitudes(self, circuits, indices):
        for circuit, selected in zip(circuits, indices, strict=True):
            circuit.save_amplitudes(selected, label="selected_amplitudes")
        compiled = transpile(
            circuits, self.simulator, optimization_level=0, seed_transpiler=12345
        )
        result = self.simulator.run(compiled, shots=1).result()
        self.assertTrue(result.success, "Synthetic Aer execution failed")
        return [
            np.asarray(result.data(index)["selected_amplitudes"], dtype=complex)
            for index in range(len(circuits))
        ]

    def assert_amplitudes_equal(self, observed, expected, label):
        self.assertTrue(
            np.allclose(observed, expected, rtol=1e-8, atol=1e-9),
            f"Synthetic amplitude comparison failed: {label}",
        )
        self.assertAlmostEqual(
            float(np.vdot(observed, observed).real), 1.0, places=8,
            msg=f"Unexpected key/scratch/flag leakage: {label}",
        )

    def test_byte_zero_and_one_match_public_cipher_with_permuted_wires(self):
        # Two unrelated, explicitly chosen synthetic keys exercise rotated
        # mask wraparound and both high key bits. PERM is a wire relabeling:
        # the physical work wires must already encode the plaintext byte.
        circuits, indices = [], []
        for key in (0x2C6, 0x155):
            cipher = ToyCipher(key, oracle.KEY_BITS)
            for byte_index, plaintext_byte in enumerate(b"QC"):
                ciphertext_byte = cipher.encrypt_byte(plaintext_byte, byte_index)
                transform = oracle.build_byte_transform(ciphertext_byte, byte_index)
                self.assertEqual((transform.num_qubits, transform.num_clbits), (19, 0))
                circuit = self.basis_key_circuit(key)
                circuit.compose(transform, inplace=True)
                circuits.append(circuit)
                indices.append([key | (plaintext_byte << oracle.KEY_BITS)])
        for case, amplitudes in enumerate(self.selected_amplitudes(circuits, indices)):
            with self.subTest(case=case):
                self.assert_amplitudes_equal(amplitudes, [1.0], "byte transform")

    def test_phase_is_joint_prefix_predicate_and_uncomputes_coherent_dirty_keys(self):
        key = 0x2C6
        alternate = key ^ 1
        cipher = ToyCipher(key, oracle.KEY_BITS)
        synthetic_ciphertext = cipher.encrypt(b"QC")
        self.assertNotEqual(
            ToyCipher(alternate, oracle.KEY_BITS).decrypt(synthetic_ciphertext),
            b"QC", "The chosen artificial control case must be unmarked",
        )

        # A borrowed dirty key bit is in coherent superposition. Both output
        # amplitudes are checked at the original key indices with ALL work
        # and flag bits zero. Their squared magnitudes summing to one verifies
        # that no amplitude leaks into changed keys or dirty auxiliary wires.
        coherent = self.basis_key_circuit(key)
        coherent.h(0)  # The chosen key's bit zero is initially zero.
        coherent.compose(oracle.build_phase_oracle(synthetic_ciphertext), inplace=True)
        circuits, indices = [coherent], [[key, alternate]]
        expected = [[-1 / math.sqrt(2), 1 / math.sqrt(2)]]

        # One-byte-only matches must stay unmarked; this detects accidentally
        # testing either byte alone or using OR instead of the two-byte AND.
        for prefix in (b"QX", b"XC"):
            circuit = self.basis_key_circuit(key)
            circuit.compose(oracle.build_phase_oracle(cipher.encrypt(prefix)), inplace=True)
            circuits.append(circuit)
            indices.append([key])
            expected.append([1.0])

        observed = self.selected_amplitudes(circuits, indices)
        for case, (amplitudes, target) in enumerate(zip(observed, expected, strict=True)):
            with self.subTest(case=case):
                self.assert_amplitudes_equal(amplitudes, target, "phase predicate and cleanup")

    def test_diffuser_has_standard_sign_and_restores_clean_auxiliaries(self):
        dimension = 1 << oracle.KEY_BITS
        selected = list(range(dimension))  # All selected indices have zero auxiliaries.
        key = 0x155
        basis = self.basis_key_circuit(key)
        basis.compose(oracle.build_diffuser(), inplace=True)
        uniform = QuantumCircuit(oracle.N_QUBITS)
        uniform.h(range(oracle.KEY_BITS))
        uniform.compose(oracle.build_diffuser(), inplace=True)

        basis_expected = np.full(dimension, 2 / dimension, dtype=complex)
        basis_expected[key] -= 1
        uniform_expected = np.full(dimension, 1 / math.sqrt(dimension), dtype=complex)
        basis_observed, uniform_observed = self.selected_amplitudes(
            [basis, uniform], [selected, selected]
        )
        self.assert_amplitudes_equal(basis_observed, basis_expected, "diffuser basis column")
        self.assert_amplitudes_equal(uniform_observed, uniform_expected, "diffuser uniform state")


if __name__ == "__main__":
    unittest.main()
