"""Compare public constant folding with the frozen release on synthetic data.

No challenge input is loaded. Four synthetic ciphertexts are tested on a
nonuniform complex superposition with support on all 1024 key states. Saving
only the zero-work/zero-flag amplitudes checks both phase action and cleanup:
their probability sum must be one. This avoids a 19-qubit operator matrix.

The same batch also checks one complete Grover round. Equality of the phase
operator on the clean auxiliary subspace, its restoration of that subspace,
and the unchanged diffuser imply equality of every repeated round, including
25 rounds. Repeating a costly 25-round simulation is unnecessary here.
"""

import importlib.util
import inspect
from pathlib import Path
import sys
import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.toy_cipher import ToyCipher
from submissions.team3.tier05 import oracle as optimized
from submissions.team3.tier05 import solution


_SPEC = importlib.util.spec_from_file_location(
    "tier05_release_oracle_fixture",
    Path(__file__).parent / "fixtures" / "tier05_release_oracle.py",
)
legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(legacy)

KEY_DIMENSION = 1 << 10
SYNTHETIC_KEY = 0x12D
CASES = {
    "both": b"QC",
    "q_only": b"QD",
    "c_only": b"RC",
    "neither": b"RD",
}
TOLERANCE = 2e-10


def _synthetic_ciphertext(plaintext):
    return ToyCipher(SYNTHETIC_KEY, 10).encrypt(plaintext)


def _key_preparation():
    """Full-support complex amplitudes, with coherent borrowed key wires."""
    circuit = QuantumCircuit(10)
    for bit in range(10):
        circuit.ry(1.05 + 0.07 * bit, bit)
        circuit.rz(0.19 + 0.17 * bit, bit)
    for control, target in ((0, 5), (1, 6), (2, 7), (3, 8), (4, 9), (9, 0)):
        circuit.cx(control, target)
    return circuit


def _synthetic_signs(ciphertext):
    """Independent public-cipher expectations for artificial test data only."""
    return np.array([
        -1.0 if ToyCipher(key, 10).decrypt(ciphertext) == b"QC" else 1.0
        for key in range(KEY_DIMENSION)
    ])


class Tier05ConstantFoldingInterfaceTests(unittest.TestCase):
    def test_exact_byte_transform_contract_is_unchanged(self):
        for byte_index, ciphertext_byte in ((0, 0xA7), (1, 0x3D), (7, 0x81)):
            with self.subTest(byte_index=byte_index):
                self.assertEqual(
                    optimized.build_byte_transform(ciphertext_byte, byte_index),
                    legacy.build_byte_transform(ciphertext_byte, byte_index),
                )

    def test_diffuser_is_unchanged_for_induction_over_rounds(self):
        # Avoid comparing auto-generated instruction names. The semantic
        # numerical test below independently verifies the reflection action.
        self.assertEqual(
            inspect.getsource(optimized.build_diffuser),
            inspect.getsource(legacy.build_diffuser),
        )

    def test_public_sbox_work_is_removed_without_changing_layout(self):
        ciphertext = _synthetic_ciphertext(CASES["both"])
        original = legacy.build_phase_oracle(ciphertext)
        folded = optimized.build_phase_oracle(ciphertext)
        self.assertEqual((folded.num_qubits, folded.num_clbits), (19, 0))
        self.assertEqual(folded.name, legacy.ORACLE_NAME)
        self.assertEqual(optimized.KEY_QUBITS, legacy.KEY_QUBITS)
        self.assertEqual(optimized.WORK_QUBITS, legacy.WORK_QUBITS)
        self.assertEqual(optimized.FLAG_QUBIT, legacy.FLAG_QUBIT)
        # Six byte computations per phase block, each dropping two nibbles
        # of 3 CCX + 2 CX. These are structural counts, not scoring metrics.
        self.assertEqual(original.count_ops()["ccx"] - folded.count_ops()["ccx"], 36)
        self.assertEqual(original.count_ops()["cx"] - folded.count_ops()["cx"], 24)
        self.assertEqual(folded.count_ops().get("measure", 0), 0)
        self.assertEqual(folded.count_ops().get("reset", 0), 0)

    def test_phase_oracle_rejects_invalid_public_inputs(self):
        for value in (None, "QC", bytearray(b"QC")):
            with self.subTest(kind=type(value).__name__), self.assertRaises(TypeError):
                optimized.build_phase_oracle(value)
        for value in (b"", b"Q"):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                optimized.build_phase_oracle(value)

    def test_default_search_keeps_25_rounds_and_key_measurement_layout(self):
        circuit = solution.build_circuit(ciphertext=_synthetic_ciphertext(CASES["both"]))
        self.assertEqual((circuit.num_qubits, circuit.num_clbits), (19, 10))
        self.assertEqual(solution.count_oracle_calls(circuit), 25)
        self.assertEqual(circuit.count_ops().get(optimized.ORACLE_NAME, 0), 25)
        self.assertEqual(circuit.count_ops().get(optimized.DIFFUSER_NAME, 0), 25)
        measurements = [
            (circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index)
            for item in circuit.data if item.operation.name == "measure"
        ]
        self.assertEqual(measurements, [(bit, bit) for bit in range(10)])


class Tier05ConstantFoldingQuantumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        preparation = _key_preparation()
        # This is a ten-qubit synthetic preparation, never a hidden oracle.
        cls.initial = np.asarray(Statevector.from_instruction(preparation).data)
        cls.expected = {}
        cls.outputs = {}
        circuits = []
        identities = []
        phase_snapshot_corrections = {}
        for case, plaintext in CASES.items():
            ciphertext = _synthetic_ciphertext(plaintext)
            cls.expected[case] = cls.initial * _synthetic_signs(ciphertext)
            for version, implementation in (("release", legacy), ("folded", optimized)):
                circuit = QuantumCircuit(19, name=f"synthetic_{case}_{version}")
                circuit.compose(preparation, range(10), inplace=True)
                circuit.compose(implementation.build_phase_oracle(ciphertext), inplace=True)
                # Lower ten basis bits are key, so these indices have all
                # eight work bits and the flag equal to zero.
                circuit.save_amplitudes(list(range(KEY_DIMENSION)), label="phase")
                phase_snapshot_corrections[(case, version)] = 1.0
                if case == "both":
                    diffuser = implementation.build_diffuser()
                    # compose hoists the suffix's global phase onto the full
                    # circuit, so the earlier snapshot already contains it.
                    # Remove only that KNOWN suffix metadata from the prefix
                    # snapshot, never a phase fitted to observed amplitudes.
                    phase_snapshot_corrections[(case, version)] = np.exp(
                        -1j * float(diffuser.global_phase)
                    )
                    circuit.compose(diffuser, inplace=True)
                    circuit.save_amplitudes(list(range(KEY_DIMENSION)), label="round")
                circuits.append(circuit)
                identities.append((case, version))

        simulator = AerSimulator(
            method="statevector", max_memory_mb=512,
            max_parallel_threads=2, max_parallel_experiments=1,
        )
        compiled = transpile(
            circuits, simulator, optimization_level=0,
            seed_transpiler=12345, num_processes=1,
        )
        result = simulator.run(compiled, shots=1, seed_simulator=505).result()
        if not result.success or len(result.results) != len(circuits):
            raise AssertionError("Synthetic phase-equivalence Aer batch failed")
        for index, identity in enumerate(identities):
            data = result.data(index)
            cls.outputs[identity] = {
                label: np.asarray(data[label])
                for label in ("phase", "round") if label in data
            }
            cls.outputs[identity]["phase"] = (
                cls.outputs[identity]["phase"] * phase_snapshot_corrections[identity]
            )
        phase_expected = cls.expected["both"]
        round_expected = 2 * np.mean(phase_expected) - phase_expected
        cls.diagnostics = {
            "synthetic_ciphertexts": len(CASES),
            "synthetic_key_basis_states_per_ciphertext": KEY_DIMENSION,
            "aer_run_calls": 1,
            "aer_circuits": len(circuits),
            "qubits_per_circuit": 19,
            "shots_per_circuit": 1,
            "maximum_grover_rounds_simulated": 1,
            "max_phase_amplitude_error": max(
                float(np.max(np.abs(values["phase"] - cls.expected[case])))
                for (case, _), values in cls.outputs.items()
            ),
            "max_old_new_phase_amplitude_error": max(
                float(np.max(np.abs(
                    cls.outputs[(case, "release")]["phase"]
                    - cls.outputs[(case, "folded")]["phase"]
                ))) for case in CASES
            ),
            "max_key_probability_error": max(
                float(np.max(np.abs(np.abs(values["phase"]) ** 2 - np.abs(cls.initial) ** 2)))
                for values in cls.outputs.values()
            ),
            "max_clean_auxiliary_probability_defect": max(
                abs(1.0 - float(np.vdot(amplitudes, amplitudes).real))
                for values in cls.outputs.values() for amplitudes in values.values()
            ),
            "max_one_round_amplitude_error": max(
                float(np.max(np.abs(cls.outputs[("both", version)]["round"] - round_expected)))
                for version in ("release", "folded")
            ),
        }

    def assert_amplitudes_close(self, actual, expected):
        self.assertEqual(actual.shape, expected.shape)
        # Scalar-only failures avoid dumping amplitudes or candidate values.
        self.assertLess(float(np.max(np.abs(actual - expected))), TOLERANCE)

    def test_synthetic_input_has_full_support_and_complex_coherence(self):
        self.assertGreater(float(np.min(np.abs(self.initial))), 1e-5)
        self.assertGreater(float(np.max(np.abs(self.initial.imag))), 0.01)
        self.assertAlmostEqual(float(np.vdot(self.initial, self.initial).real), 1.0, places=12)

    def test_all_four_conditions_match_public_cipher_with_exact_relative_phase(self):
        for case in CASES:
            with self.subTest(case=case):
                expected = self.expected[case]
                desired_sign = -1 if case == "both" else 1
                self.assertLess(
                    abs(expected[SYNTHETIC_KEY] - desired_sign * self.initial[SYNTHETIC_KEY]),
                    TOLERANCE,
                )
                for version in ("release", "folded"):
                    self.assert_amplitudes_close(self.outputs[(case, version)]["phase"], expected)

    def test_release_and_folded_phase_actions_match_without_global_phase_adjustment(self):
        for case in CASES:
            with self.subTest(case=case):
                self.assert_amplitudes_close(
                    self.outputs[(case, "folded")]["phase"],
                    self.outputs[(case, "release")]["phase"],
                )

    def test_phase_preserves_key_distribution_and_cleans_all_auxiliaries(self):
        initial_probabilities = np.abs(self.initial) ** 2
        for identity, snapshots in self.outputs.items():
            with self.subTest(case=identity[0], version=identity[1]):
                probabilities = np.abs(snapshots["phase"]) ** 2
                self.assert_amplitudes_close(probabilities, initial_probabilities)
                self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=10)

    def test_one_round_matches_analytic_diffusion_and_preserves_clean_subspace(self):
        phase_state = self.expected["both"]
        expected = 2 * np.mean(phase_state) - phase_state
        for version in ("release", "folded"):
            with self.subTest(version=version):
                actual = self.outputs[("both", version)]["round"]
                self.assert_amplitudes_close(actual, expected)
                self.assertAlmostEqual(float(np.vdot(actual, actual).real), 1.0, places=10)
        self.assert_amplitudes_close(
            self.outputs[("both", "folded")]["round"],
            self.outputs[("both", "release")]["round"],
        )


if __name__ == "__main__":
    unittest.main()
