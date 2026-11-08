"""Exact public-permutation and synthetic Shor checks for Tier 9 v2.

No real solve(), Checker, locked data, period or factor recovery is invoked.
The only real-modulus check evaluates public emitted gates on basis states;
their exact complex primitive matrices are checked separately, so a truth
table comparison is not mistaken for a phase-equivalence test.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
from itertools import permutations
import json
from pathlib import Path
import resource
import sys
import time
import unittest
from unittest.mock import patch

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from submissions.team3.tier09 import global_permutation, modular, shared_controls, solution


V5_COMMIT = "41c7c6775b8fc499c2acdd878b4829bd17e1210d"
V5_FIXTURE_BLOB = "db357e024da96731702669d51d00516964d2efd0"
UNCHANGED_MODULAR_BLOB = "99201381a71205f519f4da5e6d7856f656f4f35f"
FIXTURE_PATH = Path(__file__).with_name("fixtures") / "tier09_v5_shared_controls.py"
# Preserve the original package so '.modular' resolves to the UNCHANGED v5
# compiler, not to the new global compiler being tested.
spec = importlib.util.spec_from_file_location(
    "submissions.team3.tier09._v5_shared_controls_fixture", FIXTURE_PATH,
)
v5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v5)

# One explicitly included clean workspace is part of the final whole circuit;
# the logical controlled multiplier still has exactly 1 + work_bits wires.
EXPECTED_WORKSPACE_QUBITS = 1

EVIDENCE = {
    "baseline_commit": V5_COMMIT,
    "fixture_git_blob": V5_FIXTURE_BLOB,
    "arbitrary_small_permutations_checked": 0,
    "all_width_two_permutations_checked": 0,
    "cases_with_changed_synthesis_sequence": 0,
    "synthetic_modular_cases_checked": 0,
    "public_n77_distinct_multipliers_checked": 0,
    "public_n77_block_implementations_checked": 0,
    "public_n77_basis_cases_checked": 0,
    "native_control_sizes_checked": [],
    "max_operator_absolute_error": 0.0,
    "max_native_gate_absolute_error": 0.0,
    "max_shor_amplitude_difference": 0.0,
    "max_shor_measurement_probability_difference": 0.0,
    "max_clean_workspace_leakage_probability": 0.0,
    "small_basis_operations_touching_clean_workspace": 0,
    "small_official_basis_shor_qubits": 0,
    "max_dense_operator_qubits": 0,
    "artificial_aer_run_calls": 0,
    "artificial_aer_circuits": 0,
    "aer_threads": 2,
    "aer_memory_limit_mb": 512,
    "real_tier09_executions": 0,
}


def git_blob(path):
    data = Path(path).read_bytes()
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def exact_matrix(destinations):
    matrix = np.zeros((len(destinations), len(destinations)), dtype=complex)
    matrix[destinations, np.arange(len(destinations))] = 1
    return matrix


def controlled_destinations(table):
    return np.asarray([
        ((table[index >> 1] << 1) | 1) if index & 1 else index
        for index in range(2 * len(table))
    ], dtype=np.int64)


def public_modular_destinations(multiplier, modulus, work_bits):
    table = [multiplier * value % modulus if value < modulus else value
             for value in range(1 << work_bits)]
    return controlled_destinations(table)


def complex_close(test, actual, expected, key, tolerance=1e-9):
    difference = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    EVIDENCE[key] = max(EVIDENCE[key], difference)
    test.assertLessEqual(difference, tolerance, "Exact complex comparison failed; global phase is not fitted")


def from_table(emitter, compiler, table, width):
    operations = compiler._positive_control_operations(table, width)
    with patch.object(emitter, "_compiled_operations", return_value=operations):
        circuit = emitter.build_controlled_multiplier(1, 1 << width, width)
    return circuit, operations


def gate_basis_action(circuit):
    """Execute the ACTUAL emitted native gates on every basis input in parallel."""
    values = np.arange(1 << circuit.num_qubits, dtype=np.int64)
    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name not in {"cx", "ccx", "mcx"}:
            raise AssertionError("Unexpected primitive: phase proof needs an explicit exact-gate check")
        wires = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        controls, target = wires[:-1], wires[-1]
        if len(set(wires)) != len(wires) or operation.num_ctrl_qubits != len(controls):
            raise AssertionError("Invalid native controlled-X wire assignment")
        if operation.ctrl_state != (1 << len(controls)) - 1:
            raise AssertionError("This compiler must emit positive controls")
        mask = sum(1 << control for control in controls)
        selected = (values & mask) == mask
        values ^= selected.astype(np.int64) << target
    return values


def artificial_shor(*, use_v5, modulus=15, phase_bits=6, work_bits=4):
    with patch.object(solution, "load_locked", side_effect=AssertionError("No locked data in synthetic tests")):
        if use_v5:
            with patch.object(solution, "build_controlled_multiplier", new=v5.build_controlled_multiplier):
                return solution.build_circuit(modulus=modulus, base=2, phase_bits=phase_bits, work_bits=work_bits)
        return solution.build_circuit(modulus=modulus, base=2, phase_bits=phase_bits, work_bits=work_bits)


class ExactPublicPermutationTests(unittest.TestCase):
    def test_v5_fixture_and_dependency_are_exact_and_use_the_old_compiler(self):
        self.assertEqual(git_blob(FIXTURE_PATH), V5_FIXTURE_BLOB)
        self.assertEqual(git_blob(modular.__file__), UNCHANGED_MODULAR_BLOB)
        self.assertIs(v5._compiled_operations, modular._compiled_operations)
        self.assertIs(shared_controls._compiled_operations, global_permutation._compiled_operations)

    def test_all_width_two_and_bounded_wider_permutations_as_complex_operators(self):
        cases = [(2, list(table)) for table in permutations(range(4))]
        rng = np.random.default_rng(20261109)
        for width in (3, 4, 5):
            size = 1 << width
            tables = [list(range(size)), list(reversed(range(size)))]
            tables.extend(rng.permutation(size).tolist() for _ in range(12))
            cases.extend((width, table) for table in tables)
        for width, table in cases:
            with self.subTest(width=width, case=EVIDENCE["arbitrary_small_permutations_checked"]):
                new, new_operations = from_table(shared_controls, global_permutation, table, width)
                old, old_operations = from_table(v5, modular, table, width)
                self.assertEqual((new.num_qubits, new.num_clbits), (width + 1, 0))
                self.assertEqual(float(new.global_phase), 0.0)
                self.assertEqual(new.num_ancillas, 0)
                expected = exact_matrix(controlled_destinations(table))
                new_matrix, old_matrix = Operator(new).data, Operator(old).data
                complex_close(self, new_matrix, expected, "max_operator_absolute_error")
                complex_close(self, old_matrix, expected, "max_operator_absolute_error")
                complex_close(self, new_matrix, old_matrix, "max_operator_absolute_error")
                EVIDENCE["arbitrary_small_permutations_checked"] += 1
                EVIDENCE["all_width_two_permutations_checked"] += int(width == 2)
                EVIDENCE["cases_with_changed_synthesis_sequence"] += int(new_operations != old_operations)
                EVIDENCE["max_dense_operator_qubits"] = max(EVIDENCE["max_dense_operator_qubits"], width + 1)
        self.assertEqual(EVIDENCE["all_width_two_permutations_checked"], 24)
        self.assertGreater(EVIDENCE["cases_with_changed_synthesis_sequence"], 0)

    def test_small_modular_control_padding_bit_order_and_inverse_are_exact(self):
        for multiplier, modulus, width in ((2, 5, 3), (3, 7, 3), (2, 9, 4), (2, 15, 4), (2, 21, 5)):
            with self.subTest(modulus=modulus, width=width):
                new = shared_controls.build_controlled_multiplier(multiplier, modulus, width)
                old = v5.build_controlled_multiplier(multiplier, modulus, width)
                expected = exact_matrix(public_modular_destinations(multiplier, modulus, width))
                self.assertEqual((new.num_qubits, new.num_clbits, new.num_ancillas), (width + 1, 0, 0))
                new_matrix, old_matrix = Operator(new).data, Operator(old).data
                complex_close(self, new_matrix, expected, "max_operator_absolute_error")
                complex_close(self, old_matrix, expected, "max_operator_absolute_error")
                complex_close(self, new_matrix, old_matrix, "max_operator_absolute_error")
                inverse_expected = exact_matrix(public_modular_destinations(pow(multiplier, -1, modulus), modulus, width))
                complex_close(self, Operator(new.inverse()).data, inverse_expected, "max_operator_absolute_error")
                EVIDENCE["synthetic_modular_cases_checked"] += 1

    def test_every_real_public_power_block_basis_action_and_primitive_phases(self):
        # These are the public coefficients used to BUILD the oracle. No cycle
        # lengths, multiplicative order, factors, or measured key are computed.
        multipliers = sorted({pow(2, 1 << bit, 77) for bit in range(14)})
        primitives = {}
        for multiplier in multipliers:
            expected = public_modular_destinations(multiplier, 77, 7)
            for emitter in (v5, shared_controls):
                circuit = emitter.build_controlled_multiplier(multiplier, 77, 7)
                self.assertEqual((circuit.num_qubits, circuit.num_clbits, circuit.num_ancillas), (8, 0, 0))
                self.assertEqual(float(circuit.global_phase), 0.0)
                self.assertTrue(np.array_equal(gate_basis_action(circuit), expected))
                for instruction in circuit.data:
                    operation = instruction.operation
                    primitives.setdefault((type(operation), operation.num_ctrl_qubits, operation.ctrl_state), operation)
                EVIDENCE["public_n77_block_implementations_checked"] += 1
                EVIDENCE["public_n77_basis_cases_checked"] += 256
        # Each actual primitive must have exactly real +1 permutation entries.
        # Together with zero circuit global phase, this upgrades the full basis
        # action check to an exact complex-unitary proof for these emitted blocks.
        for (_, controls, control_state), operation in primitives.items():
            self.assertEqual(control_state, (1 << controls) - 1)
            values = np.arange(1 << (controls + 1), dtype=np.int64)
            selected = (values & ((1 << controls) - 1)) == (1 << controls) - 1
            expected = exact_matrix(values ^ (selected.astype(np.int64) << controls))
            complex_close(self, Operator(operation).data, expected, "max_native_gate_absolute_error")
            EVIDENCE["max_dense_operator_qubits"] = max(EVIDENCE["max_dense_operator_qubits"], controls + 1)
        EVIDENCE["native_control_sizes_checked"] = sorted({key[1] for key in primitives})
        EVIDENCE["public_n77_distinct_multipliers_checked"] = len(multipliers)

    def test_public_register_layout_and_shot_parameters_are_unchanged(self):
        self.assertEqual((solution.BASE, solution.PHASE_BITS, solution.WORK_BITS), (2, 14, 7))
        self.assertEqual(solution.SYNTHESIS_WORK_BITS, EXPECTED_WORKSPACE_QUBITS)
        self.assertEqual((solution.SHOTS_PER_BATCH, solution.MAX_BATCHES, solution.MAX_SHOTS), (64, 2, 128))
        self.assertEqual((solution.SEED_TRANSPILER, solution.SEED_SIMULATOR), (12345, 909))
        expected_queries = {
            "controlled_power_blocks": 14,
            "equivalent_base_multiplications": 16383,
            "exponents": [1 << bit for bit in range(14)],
        }
        for old in (True, False):
            circuit = artificial_shor(use_v5=old, modulus=15, phase_bits=14, work_bits=7)
            self.assertEqual((circuit.num_qubits, circuit.num_clbits), (21 + EXPECTED_WORKSPACE_QUBITS, 14))
            self.assertEqual(solution.count_modular_powers(circuit), expected_queries)
            self.assertEqual(
                [circuit.find_bit(item.qubits[0]).index for item in circuit.data if item.operation.name == "x"], [14]
            )
            self.assertEqual(
                [circuit.find_bit(item.qubits[0]).index for item in circuit.data if item.operation.name == "h"], list(range(14))
            )
            mapping = [
                (circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index)
                for item in circuit.data if item.operation.name == "measure"
            ]
            self.assertEqual(mapping, [(bit, bit) for bit in range(14)])
            iqfts = [item for item in circuit.data if item.operation.name == "tier07_inverse_qft"]
            self.assertEqual(len(iqfts), 1)
            self.assertEqual(iqfts[0].operation.definition, solution.build_inverse_qft(14))
            powers = [item for item in circuit.data if item.operation.name.startswith("tier09_controlled_modmul_power_")]
            for control, item in enumerate(powers):
                self.assertEqual(
                    [circuit.find_bit(qubit).index for qubit in item.qubits], [control, *range(14, 21)]
                )
            # Additional workspace is explicit and clean, never a hidden qubit
            # used by the logical multiplier or absent from the executed circuit.
            touched = {circuit.find_bit(qubit).index for item in circuit.data for qubit in item.qubits}
            self.assertEqual(touched, set(range(21)))


class SyntheticShorAerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = [(15, 6, 4), (21, 7, 5)]
        circuits = []
        for modulus, phase_bits, work_bits in cls.cases:
            for old in (True, False):
                raw = artificial_shor(use_v5=old, modulus=modulus, phase_bits=phase_bits, work_bits=work_bits)
                circuit = raw.remove_final_measurements(inplace=False)
                circuit.save_statevector(label="synthetic_full_state")
                circuits.append(circuit)
        # Follow the actual scorer's basis synthesis on one FULL synthetic
        # circuit, where the explicit workspace really begins in |0>. This
        # differs from the arbitrary-input primitive matrix tests above.
        basis_source = artificial_shor(use_v5=False, modulus=21, phase_bits=7, work_bits=5)
        basis_source = basis_source.remove_final_measurements(inplace=False)
        basis_compiled = transpile(
            basis_source, basis_gates=solution.BASIS_GATES, optimization_level=1,
            seed_transpiler=solution.SEED_TRANSPILER, num_processes=1,
        )
        cls.basis_workspace_uses = sum(
            any(basis_compiled.find_bit(qubit).index == 12 for qubit in item.qubits)
            for item in basis_compiled.data
        )
        if cls.basis_workspace_uses == 0:
            raise AssertionError("The synthetic basis test did not actually exercise clean-workspace synthesis")
        if basis_compiled.num_qubits != 13:
            raise AssertionError("The full synthetic basis circuit must include its clean workspace")
        EVIDENCE["small_basis_operations_touching_clean_workspace"] = cls.basis_workspace_uses
        EVIDENCE["small_official_basis_shor_qubits"] = basis_compiled.num_qubits
        basis_compiled.save_statevector(label="synthetic_full_state")
        circuits.append(basis_compiled)
        simulator = AerSimulator(
            method="statevector", max_memory_mb=512,
            max_parallel_threads=2, max_parallel_experiments=1,
        )
        compiled = transpile(circuits, simulator, optimization_level=0,
                             seed_transpiler=12345, num_processes=1, qubits_initially_zero=False)
        result = simulator.run(compiled, shots=1, seed_simulator=20261109).result()
        if not result.success:
            raise AssertionError("Synthetic Shor Aer execution failed")
        cls.states = [np.asarray(result.data(index)["synthetic_full_state"], dtype=complex)
                      for index in range(len(circuits))]
        EVIDENCE["artificial_aer_run_calls"] += 1
        EVIDENCE["artificial_aer_circuits"] += len(circuits)

    def test_full_complex_shor_state_and_phase_distribution_match_v5(self):
        for index, (_, phase_bits, work_bits) in enumerate(self.cases):
            with self.subTest(phase_bits=phase_bits, work_bits=work_bits):
                old, new = self.states[2 * index:2 * index + 2]
                complex_close(self, new, old, "max_shor_amplitude_difference")
                old_probabilities = (np.abs(old) ** 2).reshape(-1, 1 << phase_bits).sum(axis=0)
                new_probabilities = (np.abs(new) ** 2).reshape(-1, 1 << phase_bits).sum(axis=0)
                complex_close(self, new_probabilities, old_probabilities, "max_shor_measurement_probability_difference")
                self.assertAlmostEqual(float(new_probabilities.sum()), 1.0, places=10)
                if EXPECTED_WORKSPACE_QUBITS:
                    for state in (old, new):
                        leakage = float(np.vdot(state[1 << (phase_bits + work_bits):],
                                                state[1 << (phase_bits + work_bits):]).real)
                        EVIDENCE["max_clean_workspace_leakage_probability"] = max(
                            EVIDENCE["max_clean_workspace_leakage_probability"], leakage,
                        )
                        self.assertLessEqual(leakage, 1e-12)

    def test_actual_basis_synthesis_matches_v5_and_restores_its_clean_workspace(self):
        # State 2 is the padded v5 N=21 reference; state 4 is the same full
        # candidate after the official-basis transpilation, using clean q12.
        old, compiled = self.states[2], self.states[4]
        self.assertGreater(self.basis_workspace_uses, 0)
        self.assertEqual(len(compiled), 1 << 13)
        complex_close(self, compiled, old, "max_shor_amplitude_difference")
        old_probabilities = (np.abs(old) ** 2).reshape(-1, 128).sum(axis=0)
        compiled_probabilities = (np.abs(compiled) ** 2).reshape(-1, 128).sum(axis=0)
        complex_close(self, compiled_probabilities, old_probabilities,
                      "max_shor_measurement_probability_difference")
        leakage = float(np.vdot(compiled[1 << 12:], compiled[1 << 12:]).real)
        EVIDENCE["max_clean_workspace_leakage_probability"] = max(
            EVIDENCE["max_clean_workspace_leakage_probability"], leakage,
        )
        self.assertLessEqual(leakage, 1e-12)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--evidence-output", type=Path)
    args, remaining = parser.parse_known_args()
    started = time.perf_counter()
    program = unittest.main(argv=[sys.argv[0], *remaining], exit=False)
    EVIDENCE.update({
        "tests_run": program.result.testsRun,
        "successful": program.result.wasSuccessful(),
        "test_wall_seconds": round(time.perf_counter() - started, 6),
        "process_peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 6),
        "qiskit": importlib.metadata.version("qiskit"),
        "qiskit_aer": importlib.metadata.version("qiskit-aer"),
        "workspace_qubits": EXPECTED_WORKSPACE_QUBITS,
    })
    if args.evidence_output:
        destination = args.evidence_output.expanduser().resolve()
        if destination.is_relative_to(ROOT):
            raise ValueError("Keep the temporary evidence JSON outside the repository")
        destination.write_text(json.dumps(EVIDENCE, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(EVIDENCE, indent=2))
    raise SystemExit(0 if program.result.wasSuccessful() else 1)
