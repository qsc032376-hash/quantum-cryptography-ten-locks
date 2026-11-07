"""Tier 3 tests use artificial data and mocks, never real oracle files/Aer."""

from collections import Counter
import sys
from types import ModuleType
import unittest
from unittest import mock

from qiskit import QuantumCircuit

from submissions.team3.tier03 import solution


CLASSICAL_MODULE = "submissions.team3.classical_keystream"


class MeasurementClassificationTests(unittest.TestCase):
    def test_zero_is_constant_and_every_nonzero_position_is_balanced(self):
        self.assertEqual(solution.measurement_to_bit("000000"), "0")
        for position in range(6):
            measured = "0" * position + "1" + "0" * (5 - position)
            with self.subTest(position=position):
                self.assertEqual(solution.measurement_to_bit(measured), "1")
        self.assertEqual(solution.measurement_to_bit("101101"), "1")

    def test_rejects_non_strings(self):
        for value in (None, 0, True, b"000000", [0] * 6):
            with self.subTest(input_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    solution.measurement_to_bit(value)

    def test_rejects_malformed_strings(self):
        for value in ("", "00000", "0000000", "000002", " 00000", "000000\n", "000 000"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solution.measurement_to_bit(value)


class CircuitConstructionTests(unittest.TestCase):
    def test_layout_and_single_opaque_oracle(self):
        artificial = QuantumCircuit(7, name=solution.helper.ORACLE_NAME)
        with mock.patch.object(solution.helper, "build_oracle", return_value=artificial) as loader:
            circuit = solution.build_circuit(17)

        loader.assert_called_once_with(17)
        self.assertEqual((circuit.num_qubits, circuit.num_clbits), (7, 6))
        self.assertEqual(len(circuit.cregs), 1)
        self.assertEqual(solution.helper.count_oracle_calls(circuit), 1)
        operations = [
            (
                instruction.operation.name,
                tuple(circuit.find_bit(q).index for q in instruction.qubits),
                tuple(circuit.find_bit(c).index for c in instruction.clbits),
            )
            for instruction in circuit.data
        ]
        oracle_positions = [
            index for index, (name, _, _) in enumerate(operations)
            if name == solution.helper.ORACLE_NAME
        ]
        self.assertEqual(len(oracle_positions), 1)
        oracle_position = oracle_positions[0]
        self.assertEqual(operations[oracle_position][1], tuple(range(7)))
        before, after = operations[:oracle_position], operations[oracle_position + 1:]
        self.assertEqual([q for name, q, _ in before if name == "x"], [(6,)])
        self.assertEqual(
            Counter(q for name, q, _ in before if name == "h"),
            Counter((index,) for index in range(7)),
        )
        target_operations = [name for name, qubits, _ in before if qubits == (6,)]
        self.assertEqual(target_operations, ["x", "h"])
        self.assertEqual(
            Counter(q for name, q, _ in after if name == "h"),
            Counter((index,) for index in range(6)),
        )
        self.assertEqual(
            [(q, c) for name, q, c in after if name == "measure"],
            [((index,), (index,)) for index in range(6)],
        )

    def test_default_diagram_uses_oracle_zero(self):
        artificial = QuantumCircuit(7, name=solution.helper.ORACLE_NAME)
        with mock.patch.object(solution.helper, "build_oracle", return_value=artificial) as loader:
            solution.build_circuit()
        loader.assert_called_once_with(0)

    def test_rejects_invalid_index_before_loading(self):
        with mock.patch.object(solution.helper, "build_oracle") as loader:
            for index in (True, False, 1.0, "1", None):
                with self.subTest(index=index), self.assertRaises(TypeError):
                    solution.build_circuit(index)
            for index in (-1, 24, 100):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    solution.build_circuit(index)
        loader.assert_not_called()

    def test_rejects_wrong_oracle_shape_and_query_count(self):
        for artificial in (QuantumCircuit(6), QuantumCircuit(7, 1)):
            with mock.patch.object(solution.helper, "build_oracle", return_value=artificial):
                with self.assertRaises(ValueError):
                    solution.build_circuit()
        artificial = QuantumCircuit(7, name=solution.helper.ORACLE_NAME)
        for count in (0, 2):
            with (
                mock.patch.object(solution.helper, "build_oracle", return_value=artificial),
                mock.patch.object(solution.helper, "count_oracle_calls", return_value=count),
                self.assertRaises(ValueError),
            ):
                solution.build_circuit()


class QuantumRecoveryTests(unittest.TestCase):
    def mock_recovery(self, result):
        circuits = [QuantumCircuit(7, 6) for _ in range(24)]
        compiled = [mock.sentinel.compiled] * 24
        simulator = mock.Mock()
        simulator.run.return_value.result.return_value = result
        return circuits, compiled, simulator

    def test_preserves_oracle_order_and_leading_zeros_in_one_batch(self):
        artificial_bits = "001001101000010110100101"
        result = mock.Mock(success=True, results=[mock.sentinel.result] * 24)
        result.get_counts.side_effect = lambda index: {
            "000000" if artificial_bits[index] == "0" else "000001": 1
        }
        circuits, compiled, simulator = self.mock_recovery(result)
        with (
            mock.patch.object(solution, "build_circuit", side_effect=circuits) as builder,
            mock.patch.object(solution, "AerSimulator", return_value=simulator) as aer,
            mock.patch.object(solution, "transpile", return_value=compiled) as transpiler,
        ):
            self.assertEqual(solution.recover_key_bits(), artificial_bits)
        self.assertEqual(builder.call_args_list, [mock.call(index) for index in range(24)])
        aer.assert_called_once()
        self.assertEqual(aer.call_args.kwargs["method"], "statevector")
        self.assertEqual(transpiler.call_args.args, (circuits, simulator))
        self.assertEqual(transpiler.call_args.kwargs["basis_gates"], ["rz", "sx", "x", "cx"])
        self.assertEqual(transpiler.call_args.kwargs["optimization_level"], 1)
        simulator.run.assert_called_once_with(compiled, shots=1)
        self.assertEqual(result.get_counts.call_args_list, [mock.call(index) for index in range(24)])

    def test_rejects_failed_or_incomplete_batch_without_classification(self):
        cases = (
            mock.Mock(success=False, results=[mock.sentinel.result] * 24),
            mock.Mock(success=True, results=[mock.sentinel.result] * 23),
        )
        for result in cases:
            circuits, compiled, simulator = self.mock_recovery(result)
            with (
                mock.patch.object(solution, "build_circuit", side_effect=circuits),
                mock.patch.object(solution, "AerSimulator", return_value=simulator),
                mock.patch.object(solution, "transpile", return_value=compiled),
                self.assertRaises(RuntimeError),
            ):
                solution.recover_key_bits()
            result.get_counts.assert_not_called()

    def test_rejects_invalid_shot_counts(self):
        for counts in ({}, {"000000": 2}, {"000000": 1, "000001": 1}):
            result = mock.Mock(success=True, results=[mock.sentinel.result] * 24)
            result.get_counts.return_value = counts
            circuits, compiled, simulator = self.mock_recovery(result)
            with (
                mock.patch.object(solution, "build_circuit", side_effect=circuits),
                mock.patch.object(solution, "AerSimulator", return_value=simulator),
                mock.patch.object(solution, "transpile", return_value=compiled),
                self.assertRaises(RuntimeError),
            ):
                solution.recover_key_bits()


class SolveIntegrationTests(unittest.TestCase):
    def test_pending_classical_interface_does_not_execute_quantum_work(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "recover_key_bits") as recovery,
            mock.patch.object(solution, "AerSimulator") as aer,
            self.assertRaisesRegex(NotImplementedError, "classical_keystream"),
        ):
            solution.solve()
        recovery.assert_not_called()
        aer.assert_not_called()

    def test_delegates_to_verified_shared_interface_with_synthetic_values(self):
        artificial_bits = "001001101000010110100101"
        artificial_classical = ModuleType(CLASSICAL_MODULE)
        artificial_classical.decrypt = mock.Mock(return_value="synthetic result")
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: artificial_classical}),
            mock.patch.object(solution, "recover_key_bits", return_value=artificial_bits) as recovery,
            mock.patch.object(solution, "load_locked", return_value={"ciphertext_hex": "010203"}) as loader,
        ):
            self.assertEqual(solution.solve(), "synthetic result")
        recovery.assert_called_once_with()
        loader.assert_called_once_with(3)
        artificial_classical.decrypt.assert_called_once_with(3, artificial_bits, "010203")


if __name__ == "__main__":
    unittest.main()
