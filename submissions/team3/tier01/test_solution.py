"""Unit tests using synthetic data and an opaque, artificial Oracle only."""

from collections import Counter
import sys
from types import ModuleType
import unittest
from unittest import mock

from qiskit import QuantumCircuit

from . import solution


CLASSICAL_MODULE = f"{__package__}.classical"


class MeasurementToKeyTests(unittest.TestCase):
    def test_bit_order_and_leading_zeroes(self):
        cases = (
            ("000000000000000000000000", 0),
            ("000000000000000000000001", 1),
            ("100000000000000000000000", 1 << 23),
            ("000100101010010111110000", 0x12A5F0),
        )
        for measured, expected in cases:
            with self.subTest(measured=measured):
                self.assertEqual(solution.measurement_to_key(measured), expected)

    def test_rejects_non_strings(self):
        for measured in (None, 24, 1.5, True, b"0" * 24, [0] * 24):
            with self.subTest(input_type=type(measured).__name__):
                with self.assertRaises(TypeError):
                    solution.measurement_to_key(measured)

    def test_rejects_wrong_length_or_non_binary_characters(self):
        cases = (
            "",
            "0" * 23,
            "0" * 25,
            "0" * 23 + "2",
            "0" * 23 + "a",
            " " + "0" * 24,
            "0" * 24 + "\n",
            "0" * 12 + " " + "0" * 12,
        )
        for measured in cases:
            with self.subTest(measured=repr(measured)):
                with self.assertRaises(ValueError):
                    solution.measurement_to_key(measured)


class BuildCircuitTests(unittest.TestCase):
    def test_layout_and_single_oracle_use(self):
        artificial_oracle = QuantumCircuit(25, name=solution.helper.ORACLE_NAME)
        with mock.patch.object(
            solution.helper, "build_oracle", return_value=artificial_oracle
        ) as build_oracle:
            circuit = solution.build_circuit()

        build_oracle.assert_called_once_with()
        self.assertIsInstance(circuit, QuantumCircuit)
        self.assertEqual(solution.N_INPUT_QUBITS, 24)
        self.assertEqual((circuit.num_qubits, circuit.num_clbits), (25, 24))
        self.assertEqual(len(circuit.cregs), 1)
        self.assertEqual(circuit.cregs[0].size, 24)
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
            index
            for index, (name, _, _) in enumerate(operations)
            if name == solution.helper.ORACLE_NAME
        ]
        self.assertEqual(len(oracle_positions), 1)
        oracle_index = oracle_positions[0]
        self.assertEqual(operations[oracle_index][1], tuple(range(25)))

        before = operations[:oracle_index]
        after = operations[oracle_index + 1 :]
        self.assertEqual([qubits for name, qubits, _ in before if name == "x"], [(24,)])
        self.assertEqual(
            Counter(qubits for name, qubits, _ in before if name == "h"),
            Counter((index,) for index in range(25)),
        )
        self.assertEqual(
            Counter(qubits for name, qubits, _ in after if name == "h"),
            Counter((index,) for index in range(24)),
        )
        self.assertFalse(any(name == "measure" for name, _, _ in before))
        self.assertEqual(
            [(qubits, clbits) for name, qubits, clbits in after if name == "measure"],
            [((index,), (index,)) for index in range(24)],
        )
        x_position = next(index for index, (name, _, _) in enumerate(before) if name == "x")
        auxiliary_h_position = next(
            index
            for index, (name, qubits, _) in enumerate(before)
            if name == "h" and qubits == (24,)
        )
        self.assertLess(x_position, auxiliary_h_position)
        final_h_positions = [index for index, (name, _, _) in enumerate(after) if name == "h"]
        measurement_positions = [
            index for index, (name, _, _) in enumerate(after) if name == "measure"
        ]
        self.assertLess(max(final_h_positions), min(measurement_positions))


class RecoverKeyTests(unittest.TestCase):
    def test_runs_one_shot_with_mock_simulator(self):
        artificial_circuit = QuantumCircuit(25, 24)
        result = mock.Mock(success=True)
        result.get_counts.return_value = {"000100101010010111110000": 1}
        simulator = mock.Mock()
        simulator.run.return_value.result.return_value = result

        with (
            mock.patch.object(
                solution, "build_circuit", return_value=artificial_circuit
            ) as build_circuit,
            mock.patch.object(solution, "AerSimulator", return_value=simulator) as aer,
            mock.patch.object(
                solution, "transpile", return_value=mock.sentinel.compiled
            ) as transpile,
        ):
            self.assertEqual(solution.recover_key(), 0x12A5F0)

        build_circuit.assert_called_once_with()
        aer.assert_called_once()
        self.assertEqual(aer.call_args.kwargs["method"], "statevector")
        transpile.assert_called_once()
        self.assertEqual(transpile.call_args.args, (artificial_circuit, simulator))
        simulator.run.assert_called_once_with(mock.sentinel.compiled, shots=1)
        result.get_counts.assert_called_once_with(mock.sentinel.compiled)

    def test_rejects_failed_simulation(self):
        result = mock.Mock(success=False)
        simulator = mock.Mock()
        simulator.run.return_value.result.return_value = result
        with (
            mock.patch.object(solution, "build_circuit"),
            mock.patch.object(solution, "AerSimulator", return_value=simulator),
            mock.patch.object(solution, "transpile"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Aer"):
                solution.recover_key()
        result.get_counts.assert_not_called()

    def test_rejects_unexpected_measurement_counts(self):
        cases = (
            {},
            {"0" * 24: 2},
            {"0" * 24: 1, "0" * 23 + "1": 1},
        )
        for counts in cases:
            with self.subTest(counts=counts):
                result = mock.Mock(success=True)
                result.get_counts.return_value = counts
                simulator = mock.Mock()
                simulator.run.return_value.result.return_value = result
                with (
                    mock.patch.object(solution, "build_circuit"),
                    mock.patch.object(solution, "AerSimulator", return_value=simulator),
                    mock.patch.object(solution, "transpile"),
                ):
                    with self.assertRaises(RuntimeError):
                        solution.recover_key()


class SolveTests(unittest.TestCase):
    def test_missing_classical_module_fails_before_quantum_execution(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "recover_key") as recover_key,
        ):
            with self.assertRaises(ModuleNotFoundError):
                solution.solve()
        recover_key.assert_not_called()

    def test_delegates_to_classical_module_using_synthetic_values(self):
        artificial_classical = ModuleType(CLASSICAL_MODULE)
        artificial_classical.decrypt_tier1 = mock.Mock(return_value="synthetic result")
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: artificial_classical}),
            mock.patch.object(solution, "recover_key", return_value=0x12A5F0) as recover_key,
            mock.patch.object(
                solution, "load_locked", return_value={"ciphertext_hex": "010203"}
            ) as load_locked,
        ):
            self.assertEqual(solution.solve(), "synthetic result")

        recover_key.assert_called_once_with()
        load_locked.assert_called_once_with(1)
        artificial_classical.decrypt_tier1.assert_called_once_with(0x12A5F0, "010203")


if __name__ == "__main__":
    unittest.main()
