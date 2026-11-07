"""Simon circuit and sampling tests using synthetic rows and mock Aer only."""

from collections import Counter
from contextlib import contextmanager
import sys
from types import ModuleType
import unittest
from unittest import mock

from qiskit import QuantumCircuit

from submissions.team3.tier04 import solution


CLASSICAL_MODULE = "submissions.team3.classical_keystream"


def synthetic_counts(rows, shots=32):
    counts = {format(row, "010b"): 1 for row in rows}
    remainder = shots - sum(counts.values())
    if remainder:
        counts["0000000000"] = counts.get("0000000000", 0) + remainder
    return counts


@contextmanager
def mock_sampler(*batches, success=True):
    simulator = mock.Mock()
    jobs = []
    for counts in batches:
        result = mock.Mock(success=success)
        result.get_counts.return_value = counts
        job = mock.Mock()
        job.result.return_value = result
        jobs.append(job)
    simulator.run.side_effect = jobs
    with (
        mock.patch.object(solution, "build_circuit", return_value=mock.sentinel.circuit),
        mock.patch.object(solution, "count_oracle_calls", return_value=1),
        mock.patch.object(solution, "AerSimulator", return_value=simulator),
        mock.patch.object(solution, "transpile", return_value=mock.sentinel.compiled),
    ):
        yield simulator


class MeasurementToEquationTests(unittest.TestCase):
    def test_significance_order_and_leading_zeroes(self):
        cases = (("0000000000", 0), ("0000000001", 1),
                 ("1000000000", 512), ("0010110101", 0x0B5))
        for measured, expected in cases:
            with self.subTest(measured=measured):
                self.assertEqual(solution.measurement_to_equation(measured), expected)

    def test_rejects_wrong_types_and_noncanonical_strings(self):
        for measured in (None, 1, True, b"0" * 10):
            with self.subTest(measured=measured), self.assertRaises(TypeError):
                solution.measurement_to_equation(measured)
        for measured in ("", "0" * 9, "0" * 11, "0000000002", "0" * 5 + " " + "0" * 5):
            with self.subTest(measured=measured), self.assertRaises(ValueError):
                solution.measurement_to_equation(measured)


class CircuitTests(unittest.TestCase):
    def test_input_only_preparation_and_readout_with_one_opaque_block(self):
        artificial_oracle = QuantumCircuit(20, name="artificial_simon")
        with mock.patch.object(solution.helper, "build_oracle", return_value=artificial_oracle):
            circuit = solution.build_circuit()
        self.assertEqual((circuit.num_qubits, circuit.num_clbits), (20, 10))
        self.assertEqual(len(circuit.cregs), 1)
        self.assertEqual(solution.count_oracle_calls(circuit), 1)
        operations = [
            (item.operation.name,
             tuple(circuit.find_bit(q).index for q in item.qubits),
             tuple(circuit.find_bit(c).index for c in item.clbits))
            for item in circuit.data
        ]
        oracle_positions = [i for i, (name, _, _) in enumerate(operations)
                            if name == solution.ORACLE_NAME]
        self.assertEqual(len(oracle_positions), 1)
        oracle_index = oracle_positions[0]
        self.assertEqual(operations[oracle_index][1], tuple(range(20)))
        before, after = operations[:oracle_index], operations[oracle_index + 1:]
        self.assertEqual(Counter(before), Counter(("h", (i,), ()) for i in range(10)))
        self.assertEqual(Counter(after), Counter(
            [("h", (i,), ()) for i in range(10)]
            + [("measure", (i,), (i,)) for i in range(10)]
        ))
        self.assertTrue(all(q < 10 for _, qubits, _ in before + after for q in qubits))
        final_h = [i for i, (name, _, _) in enumerate(after) if name == "h"]
        measurements = [i for i, (name, _, _) in enumerate(after) if name == "measure"]
        self.assertLess(max(final_h), min(measurements))

    def test_counter_does_not_traverse_an_artificial_nested_definition(self):
        inner = QuantumCircuit(20, name=solution.ORACLE_NAME)
        wrapper = QuantumCircuit(20, name="unnamed_outer_wrapper")
        wrapper.append(inner.to_gate(), range(20))
        circuit = QuantumCircuit(20)
        circuit.append(wrapper.to_gate(), range(20))
        self.assertEqual(solution.count_oracle_calls(circuit), 0)


class SamplingTests(unittest.TestCase):
    def test_stops_as_soon_as_rank_nine_is_observed(self):
        # These artificial rows describe exactly the nonzero period s = 1.
        with mock_sampler(synthetic_counts(1 << j for j in range(1, 10))) as simulator:
            period, report = solution.recover_period_with_diagnostics()
        self.assertEqual(period, 1)
        self.assertEqual(report["rank"], 9)
        self.assertEqual(report["nullity"], 1)
        self.assertEqual(report["shots"], 32)
        self.assertEqual(report["oracle_queries_including_shots"], 32)
        self.assertTrue(report["all_observed_equations_satisfied"])
        simulator.run.assert_called_once_with(mock.sentinel.compiled, shots=32)

    def test_accumulates_independent_equations_across_batches(self):
        first = synthetic_counts(1 << j for j in range(1, 9))
        second = {format(1 << 9, "010b"): 32}
        with mock_sampler(first, second) as simulator:
            period, report = solution.recover_period_with_diagnostics()
        self.assertEqual(period, 1)
        self.assertEqual([item["rank"] for item in report["rank_history"]], [8, 9])
        self.assertEqual(report["shots"], 64)
        self.assertEqual(simulator.run.call_count, 2)

    def test_zero_or_repeated_rows_stop_at_budget_without_returning_a_period(self):
        for row, expected_rank in ((0, 0), (2, 1)):
            with self.subTest(row=row):
                counts = {format(row, "010b"): 32}
                with mock_sampler(counts, counts) as simulator:
                    with self.assertRaises(solution.SamplingLimitError) as caught:
                        solution.recover_period_with_diagnostics(max_shots=64)
                self.assertEqual((caught.exception.rank, caught.exception.shots), (expected_rank, 64))
                self.assertEqual(simulator.run.call_count, 2)

    def test_final_batch_is_trimmed_to_remaining_budget(self):
        with mock_sampler({"0000000000": 32}, {"0000000000": 8}) as simulator:
            with self.assertRaises(solution.SamplingLimitError) as caught:
                solution.recover_period_with_diagnostics(batch_shots=32, max_shots=40)
        self.assertEqual(caught.exception.shots, 40)
        self.assertEqual([call.kwargs["shots"] for call in simulator.run.call_args_list], [32, 8])

    def test_hard_budget_is_checked_before_build_or_simulation(self):
        with mock.patch.object(solution, "build_circuit") as build:
            for kwargs in ({"max_shots": 129}, {"max_shots": 8}, {"batch_shots": 0}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    solution.recover_period_with_diagnostics(**kwargs)
            with self.assertRaises(TypeError):
                solution.recover_period_with_diagnostics(max_shots=True)
        build.assert_not_called()

    def test_full_rank_is_rejected_instead_of_accepting_zero_period(self):
        with mock_sampler(synthetic_counts(1 << j for j in range(10))) as simulator:
            with self.assertRaisesRegex(RuntimeError, "Full-rank"):
                solution.recover_period_with_diagnostics()
        self.assertEqual(simulator.run.call_count, 1)

    def test_invalid_frequencies_or_bitstrings_stop_without_retry(self):
        invalid = ({}, {"0000000000": 31}, {"0000000000": 0},
                   {"0000000000": True}, {"0000000000": -1}, {"000000000x": 32})
        for counts in invalid:
            with self.subTest(counts=counts), mock_sampler(counts) as simulator:
                with self.assertRaises((RuntimeError, ValueError)):
                    solution.recover_period_with_diagnostics()
                self.assertEqual(simulator.run.call_count, 1)

    def test_failed_simulator_result_is_not_retried(self):
        with mock_sampler({"0000000000": 32}, success=False) as simulator:
            with self.assertRaisesRegex(RuntimeError, "Aer"):
                solution.recover_period_with_diagnostics()
        self.assertEqual(simulator.run.call_count, 1)


class SolveTests(unittest.TestCase):
    def test_missing_classical_module_fails_before_quantum_recovery(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "recover_period") as recover,
        ):
            with self.assertRaisesRegex(NotImplementedError, "classical_keystream"):
                solution.solve()
        recover.assert_not_called()

    def test_delegates_artificial_period_and_ciphertext_to_classical_module(self):
        artificial = ModuleType(CLASSICAL_MODULE)
        artificial.decrypt_tier4 = mock.Mock(return_value="artificial line")
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: artificial}),
            mock.patch.object(solution, "recover_period", return_value=0x0B5) as recover,
            mock.patch.object(solution, "load_locked", return_value={"ciphertext_hex": "010203"}) as load,
        ):
            self.assertEqual(solution.solve(), "artificial line")
        recover.assert_called_once_with()
        load.assert_called_once_with(4)
        artificial.decrypt_tier4.assert_called_once_with(0x0B5, "010203")


if __name__ == "__main__":
    unittest.main()
