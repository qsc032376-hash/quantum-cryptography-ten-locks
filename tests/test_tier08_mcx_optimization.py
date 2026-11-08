"""Exact synthetic equivalence checks for the local Tier 8 MCX replacement.

The release fixture is frozen from commit 868fb65. No real locked data,
period, factors, plaintext, or Checker is used. Dense matrices stop at nine
qubits; six-control templates and small Shor circuits use statevectors.
"""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from submissions.team3.tier08 import modular, solution


FIXTURE_PATH = Path(__file__).with_name("fixtures") / "tier08_release_modular.py"
RELEASE_COMMIT = "868fb65e20c73a27bffc118f3617080df9cf2f8b"
RELEASE_MODULAR_BLOB = "9518f07afb0c96696224e48e1074ed755a76b24d"
spec = importlib.util.spec_from_file_location("tier08_release_modular_fixture", FIXTURE_PATH)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

EVIDENCE = {
    "release_commit": RELEASE_COMMIT,
    "max_dense_matrix_qubits": 0,
    "max_matrix_absolute_error": 0.0,
    "max_statevector_absolute_error": 0.0,
    "max_shor_amplitude_difference": 0.0,
    "max_shor_measurement_probability_difference": 0.0,
    "artificial_aer_run_calls": 0,
    "artificial_aer_circuits": 0,
    "aer_threads": 2,
    "aer_memory_limit_mb": 512,
    "real_tier08_executions": 0,
}


def embed(circuit, width):
    """Keep original wires low and add untouched high wires to common space."""
    result = QuantumCircuit(width)
    result.compose(circuit, list(range(circuit.num_qubits)), inplace=True)
    return result


def mcx_destinations(controls, width):
    values = np.arange(1 << width, dtype=np.int64)
    control_mask = (1 << controls) - 1
    selected = (values & control_mask) == control_mask
    return values ^ (selected.astype(np.int64) << controls)


def modular_destinations(multiplier, modulus, work_bits, width):
    values = np.arange(1 << width, dtype=np.int64)
    work_mask = (1 << work_bits) - 1
    work_values = (values >> 1) & work_mask
    selected = ((values & 1) == 1) & (work_values < modulus)
    mapped = np.where(selected, multiplier * work_values % modulus, work_values)
    return (values & ~(work_mask << 1)) | (mapped << 1)


def permutation_matrix(destinations):
    result = np.zeros((len(destinations), len(destinations)), dtype=complex)
    result[destinations, np.arange(len(destinations))] = 1
    return result


def assert_complex_close(test, actual, expected, evidence_key, tolerance=1e-9):
    error = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    EVIDENCE[evidence_key] = max(EVIDENCE[evidence_key], error)
    test.assertLessEqual(error, tolerance, "Exact complex comparison failed; phase cannot be ignored")


def random_entangled_state(width, seed):
    rng = np.random.default_rng(seed)
    values = rng.normal(size=1 << width) + 1j * rng.normal(size=1 << width)
    return values / np.linalg.norm(values)


def permuted_state(state, destinations):
    expected = np.empty_like(state)
    expected[destinations] = state
    return expected


def statevector_circuit(operation, initial=None):
    circuit = QuantumCircuit(operation.num_qubits)
    if initial is not None:
        circuit.set_statevector(initial)
    circuit.compose(operation, inplace=True)
    circuit.save_statevector(label="artificial_state")
    return circuit


def artificial_shor(*, use_release, phase_bits=6, work_bits=4):
    """Use the unchanged production builder, only with public synthetic N=15."""
    with patch.object(solution, "load_locked", side_effect=AssertionError("Synthetic tests must not read locked data")):
        if use_release:
            with (
                patch.object(solution, "build_controlled_multiplier", new=release.build_controlled_multiplier),
                patch.object(solution, "dirty_qubit_count", new=release.dirty_qubit_count),
            ):
                return solution.build_circuit(modulus=15, base=2, phase_bits=phase_bits, work_bits=work_bits)
        return solution.build_circuit(modulus=15, base=2, phase_bits=phase_bits, work_bits=work_bits)


class ExactMatrixTests(unittest.TestCase):
    def test_release_fixture_is_byte_exact(self):
        data = FIXTURE_PATH.read_bytes()
        git_blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        self.assertEqual(hashlib.sha1(git_blob).hexdigest(), RELEASE_MODULAR_BLOB)

    def test_small_templates_are_exact_mcx_in_a_common_dirty_space(self):
        for controls in range(1, 6):
            with self.subTest(controls=controls):
                old = release._mcx_template(controls)
                new = modular._mcx_template(controls)
                width = max(old.num_qubits, new.num_qubits)
                self.assertLessEqual(width, 9)
                EVIDENCE["max_dense_matrix_qubits"] = max(EVIDENCE["max_dense_matrix_qubits"], width)
                expected = permutation_matrix(mcx_destinations(controls, width))
                old_matrix = Operator(embed(old, width)).data
                new_matrix = Operator(embed(new, width)).data
                for actual in (old_matrix, new_matrix):
                    assert_complex_close(self, actual, expected, "max_matrix_absolute_error")
                assert_complex_close(self, new_matrix, old_matrix, "max_matrix_absolute_error")
                if controls <= 3:
                    self.assertEqual(old.num_qubits, new.num_qubits)
                    self.assertEqual(old.count_ops(), new.count_ops())

    def test_borrowed_width_reduction_preserves_small_cases(self):
        self.assertEqual([release.dirty_qubit_count(n) for n in range(1, 7)], [0, 0, 0, 2, 3, 4])
        self.assertEqual([modular.dirty_qubit_count(n) for n in range(1, 7)], [0, 0, 0, 1, 2, 2])

    def test_synthetic_modular_maps_padding_control_and_inverse_exactly(self):
        # All are artificial moduli; every work and dirty basis state is covered.
        for multiplier, modulus, work_bits in ((2, 5, 3), (2, 9, 4), (2, 5, 5)):
            with self.subTest(modulus=modulus, work_bits=work_bits):
                old = release.build_controlled_multiplier(multiplier, modulus, work_bits)
                new = modular.build_controlled_multiplier(multiplier, modulus, work_bits)
                width = max(old.num_qubits, new.num_qubits)
                self.assertLessEqual(width, 9)
                EVIDENCE["max_dense_matrix_qubits"] = max(EVIDENCE["max_dense_matrix_qubits"], width)
                old_common = embed(old, width)
                new_common = embed(new, width)
                expected = permutation_matrix(modular_destinations(multiplier, modulus, work_bits, width))
                old_matrix = Operator(old_common).data
                new_matrix = Operator(new_common).data
                for actual in (old_matrix, new_matrix):
                    assert_complex_close(self, actual, expected, "max_matrix_absolute_error")
                assert_complex_close(self, new_matrix, old_matrix, "max_matrix_absolute_error")
                inverse = pow(multiplier, -1, modulus)
                inverse_expected = permutation_matrix(modular_destinations(inverse, modulus, work_bits, width))
                assert_complex_close(self, Operator(new_common.inverse()).data, inverse_expected, "max_matrix_absolute_error")

    def test_main_layout_base_iqft_shots_and_twelve_powers_are_unchanged(self):
        self.assertEqual((solution.BASE, solution.PHASE_BITS, solution.WORK_BITS), (2, 12, 6))
        self.assertEqual((solution.SHOTS_PER_BATCH, solution.MAX_BATCHES, solution.MAX_SHOTS), (64, 2, 128))
        self.assertEqual((solution.SEED_TRANSPILER, solution.SEED_SIMULATOR), (12345, 808))
        expected_powers = {
            "controlled_power_blocks": 12,
            "equivalent_base_multiplications": 4095,
            "exponents": [1 << bit for bit in range(12)],
        }
        for use_release, borrowed_count in ((True, 4), (False, 2)):
            with self.subTest(release=use_release):
                # Only build the 18q structure; do NOT simulate it or make its matrix.
                circuit = artificial_shor(use_release=use_release, phase_bits=12, work_bits=6)
                self.assertEqual((circuit.num_qubits, circuit.num_clbits), (18, 12))
                self.assertEqual(solution.count_modular_powers(circuit), expected_powers)
                measurements = [
                    (circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index)
                    for item in circuit.data if item.operation.name == "measure"
                ]
                self.assertEqual(measurements, [(bit, bit) for bit in range(12)])
                iqfts = [item for item in circuit.data if item.operation.name == "tier07_inverse_qft"]
                self.assertEqual(len(iqfts), 1)
                self.assertEqual(iqfts[0].operation.definition, solution.build_inverse_qft(12))
                self.assertEqual(
                    [circuit.find_bit(item.qubits[0]).index for item in circuit.data if item.operation.name == "x"],
                    [12],
                )
                powers = [item for item in circuit.data if item.operation.name.startswith("tier08_controlled_modmul_power_")]
                for control, item in enumerate(powers):
                    wires = [circuit.find_bit(qubit).index for qubit in item.qubits]
                    self.assertEqual(wires[:7], [control, *range(12, 18)])
                    self.assertEqual(len(wires[7:]), borrowed_count)
                    self.assertEqual(len(wires), len(set(wires)))
                    self.assertTrue(all(wire < 12 and wire != control for wire in wires[7:]))


class CoherentAerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the OLD, wider space so the new operation must act as identity on
        # former borrowed wires, even when those wires are entangled with all others.
        cls.width = release._mcx_template(6).num_qubits
        cls.initial_mcx = random_entangled_state(cls.width, 32026)
        cls.initial_modular = random_entangled_state(cls.width, 42026)
        old_mcx = embed(release._mcx_template(6), cls.width)
        new_mcx = embed(modular._mcx_template(6), cls.width)
        old_modular = embed(release.build_controlled_multiplier(2, 5, 6), cls.width)
        new_modular = embed(modular.build_controlled_multiplier(2, 5, 6), cls.width)
        old_shor = artificial_shor(use_release=True).remove_final_measurements(inplace=False)
        new_shor = artificial_shor(use_release=False).remove_final_measurements(inplace=False)
        circuits = [
            statevector_circuit(old_mcx, cls.initial_mcx),
            statevector_circuit(new_mcx, cls.initial_mcx),
            statevector_circuit(old_modular, cls.initial_modular),
            statevector_circuit(new_modular, cls.initial_modular),
            statevector_circuit(old_shor),
            statevector_circuit(new_shor),
        ]
        simulator = AerSimulator(
            method="statevector", max_memory_mb=512,
            max_parallel_threads=2, max_parallel_experiments=1,
        )
        # Unknown dirty input is intentional; do not let the transpiler assume
        # wires are initially zero or rewrite a merely zero-state-correct gate.
        compiled = transpile(
            circuits, simulator, optimization_level=0, seed_transpiler=12345,
            qubits_initially_zero=False, num_processes=1,
        )
        result = simulator.run(compiled, shots=1, seed_simulator=32026).result()
        if not result.success:
            raise AssertionError("The artificial statevector batch failed")
        cls.states = [np.asarray(result.data(index)["artificial_state"], dtype=complex) for index in range(len(circuits))]
        EVIDENCE["artificial_aer_run_calls"] += 1
        EVIDENCE["artificial_aer_circuits"] += len(circuits)

    def test_six_control_mcx_preserves_arbitrary_dirty_entanglement_and_phase(self):
        expected = permuted_state(self.initial_mcx, mcx_destinations(6, self.width))
        for actual in self.states[:2]:
            assert_complex_close(self, actual, expected, "max_statevector_absolute_error")
        assert_complex_close(self, self.states[0], self.states[1], "max_statevector_absolute_error")

    def test_six_control_modular_map_preserves_padding_and_arbitrary_dirty_entanglement(self):
        expected = permuted_state(self.initial_modular, modular_destinations(2, 5, 6, self.width))
        for actual in self.states[2:4]:
            assert_complex_close(self, actual, expected, "max_statevector_absolute_error")
        assert_complex_close(self, self.states[2], self.states[3], "max_statevector_absolute_error")

    def test_small_shor_full_complex_state_and_measurement_distribution_agree(self):
        old, new = self.states[4:6]
        assert_complex_close(self, new, old, "max_shor_amplitude_difference")
        old_probability = (np.abs(old) ** 2).reshape(16, 64).sum(axis=0)
        new_probability = (np.abs(new) ** 2).reshape(16, 64).sum(axis=0)
        assert_complex_close(self, new_probability, old_probability, "max_shor_measurement_probability_difference")
        expected = np.zeros(64)
        expected[[0, 16, 32, 48]] = 0.25  # Known synthetic N=15 demonstration only.
        for probabilities in (old_probability, new_probability):
            assert_complex_close(self, probabilities, expected, "max_shor_measurement_probability_difference")


if __name__ == "__main__":
    program = unittest.main(exit=False)
    print(json.dumps(EVIDENCE, indent=2))
    raise SystemExit(0 if program.result.wasSuccessful() else 1)
