"""Tier 6 predicate tests on a few explicitly constructed artificial keys.

No challenge data is loaded, no keyspace is enumerated, and no Grover search
is run. The collision below follows directly from the public mask equations.
Only selected amplitudes and auxiliary-register probabilities are inspected.
"""

import math
import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common.toy_cipher import ToyCipher, mask
from submissions.team3.tier06 import oracle


class SyntheticOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simulator = AerSimulator(
            method="statevector", max_memory_mb=512,
            max_parallel_threads=2, max_parallel_experiments=1,
        )

    @staticmethod
    def coherent_zero_pair(width, alternate):
        """Prepare (|0> + |alternate>)/sqrt(2) without a dense initializer."""
        circuit = QuantumCircuit(width)
        pivot = (alternate & -alternate).bit_length() - 1
        circuit.h(pivot)
        for bit in range(oracle.KEY_BITS):
            if bit != pivot and (alternate >> bit) & 1:
                circuit.cx(pivot, bit)
        return circuit

    def run_selected(self, circuits, selections, *, check_work=False):
        for circuit, selected in zip(circuits, selections, strict=True):
            circuit.save_amplitudes(selected, label="selected_amplitudes")
            if check_work:
                circuit.save_probabilities(
                    list(oracle.WORK_QUBITS), label="work_probabilities"
                )
        compiled = transpile(
            circuits, self.simulator, optimization_level=0, seed_transpiler=12345
        )
        result = self.simulator.run(compiled, shots=1).result()
        self.assertTrue(result.success, "Synthetic Aer execution failed")
        output = []
        for index in range(len(circuits)):
            data = result.data(index)
            amplitudes = np.asarray(data["selected_amplitudes"], dtype=complex)
            if check_work:
                self.assertAlmostEqual(
                    float(data["work_probabilities"][0]), 1.0, places=8,
                    msg="The diffuser did not restore all work qubits",
                )
            output.append(amplitudes)
        return output

    def assert_selected_equal(self, observed, expected, *, complete_support=True):
        self.assertTrue(
            np.allclose(observed, expected, rtol=1e-8, atol=1e-9),
            "Artificial amplitude/sign comparison failed",
        )
        if complete_support:
            self.assertAlmostEqual(
                float(np.vdot(observed, observed).real), 1.0, places=8,
                msg="Amplitude leaked into changed key or auxiliary states",
            )

    def test_multiple_marked_keys_and_relative_phase_restore_dirty_borrowing(self):
        # With k bits {0,5,6,8} set, the XOR terms cancel and the only
        # nonzero nonlinear term (row 5: k6*k8) cancels k5. Thus both
        # k=0 and k=0x161 have mask(k,0)=0; no candidate search is needed.
        collision = 0x161
        self.assertEqual(mask(0, 0, oracle.KEY_BITS), 0)
        self.assertEqual(mask(collision, 0, oracle.KEY_BITS), 0)
        c_zero = ToyCipher(0, oracle.KEY_BITS).encrypt_byte(ord("Q"), 0)
        c_one = ToyCipher(1, oracle.KEY_BITS).encrypt_byte(ord("Q"), 0)
        self.assertEqual(
            ToyCipher(collision, oracle.KEY_BITS).decrypt_byte(c_zero, 0), ord("Q")
        )
        self.assertNotEqual(
            ToyCipher(1, oracle.KEY_BITS).decrypt_byte(c_zero, 0), ord("Q")
        )
        self.assertNotEqual(c_zero, c_one)

        both_marked = self.coherent_zero_pair(oracle.MAIN_QUBITS, collision)
        both_marked.compose(oracle.build_phase_oracle(c_zero), inplace=True)
        mixed_zero = self.coherent_zero_pair(oracle.MAIN_QUBITS, 1)
        mixed_zero.compose(oracle.build_phase_oracle(c_zero), inplace=True)
        mixed_one = self.coherent_zero_pair(oracle.MAIN_QUBITS, 1)
        mixed_one.compose(oracle.build_phase_oracle(c_one), inplace=True)

        observed = self.run_selected(
            [both_marked, mixed_zero, mixed_one], [[0, collision], [0, 1], [0, 1]]
        )
        amplitude = 1 / math.sqrt(2)
        expected = ((-amplitude, -amplitude), (-amplitude, amplitude),
                    (amplitude, -amplitude))
        for case, (actual, target) in enumerate(zip(observed, expected, strict=True)):
            with self.subTest(case=case):
                self.assert_selected_equal(actual, target)

    def test_bit_predicate_xor_and_uncomputation_restore_all_work(self):
        # For this synthetic byte, key 1 is marked and key 0 is not.
        c_one = ToyCipher(1, oracle.KEY_BITS).encrypt_byte(ord("Q"), 0)
        predicate = oracle.build_bit_oracle(c_one)
        self.assertEqual((predicate.num_qubits, predicate.num_clbits), (23, 0))

        computed = self.coherent_zero_pair(oracle.PILOT_QUBITS, 1)
        computed.compose(predicate, inplace=True)
        uncomputed = self.coherent_zero_pair(oracle.PILOT_QUBITS, 1)
        uncomputed.compose(predicate, inplace=True)
        uncomputed.compose(predicate, inplace=True)  # XOR the same predicate again.
        observed = self.run_selected(
            [computed, uncomputed],
            [[0, 1 | (1 << oracle.FLAG_QUBIT)], [0, 1]],
        )
        target = [1 / math.sqrt(2), 1 / math.sqrt(2)]
        for amplitudes in observed:
            self.assert_selected_equal(amplitudes, target)

    def test_diffuser_standard_sign_and_clean_auxiliary_return(self):
        dimension = 1 << oracle.KEY_BITS
        artificial_key = 0x161
        basis = QuantumCircuit(oracle.MAIN_QUBITS)
        for bit in range(oracle.KEY_BITS):
            if (artificial_key >> bit) & 1:
                basis.x(bit)
        basis.compose(oracle.build_diffuser(), inplace=True)

        uniform = QuantumCircuit(oracle.MAIN_QUBITS)
        uniform.h(range(oracle.KEY_BITS))
        uniform.compose(oracle.build_diffuser(), inplace=True)
        # Undo the known preparation, so a single saved amplitude verifies
        # D|+> = |+> without listing or inspecting the full keyspace.
        uniform.h(range(oracle.KEY_BITS))
        observed = self.run_selected(
            [basis, uniform], [[artificial_key, 0, 1, 1 << 13], [0]],
            check_work=True,
        )
        self.assert_selected_equal(
            observed[0], [2 / dimension - 1, 2 / dimension, 2 / dimension, 2 / dimension],
            complete_support=False,
        )
        self.assert_selected_equal(observed[1], [1.0])


if __name__ == "__main__":
    unittest.main()
