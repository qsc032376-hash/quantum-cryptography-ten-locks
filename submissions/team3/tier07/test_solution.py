"""Artificial Tier 7 input, orchestration, and integration tests only."""

from contextlib import contextmanager
import sys
from types import ModuleType
import unittest
from unittest import mock

from qiskit import QuantumCircuit

from submissions.team3.tier07 import solution


CLASSICAL_MODULE = "submissions.team3.tier07_classical"
ARTIFICIAL_BITS = "00100101101001"
ARTIFICIAL_KEY = 2409
ZERO_BITS = "0" * 14


class MeasurementTests(unittest.TestCase):
    def test_canonical_fourteen_bit_order(self):
        for measured, expected in (
            (ZERO_BITS, 0),
            ("00000000000001", 1),
            ("10000000000000", 8192),
            (ARTIFICIAL_BITS, ARTIFICIAL_KEY),
            ("11111111111111", 16383),
        ):
            with self.subTest(measured=measured):
                self.assertEqual(solution.measurement_to_phase(measured), expected)

    def test_rejects_non_string_inputs(self):
        for value in (None, True, 1, 1.5, b"0" * 14, [0] * 14):
            with self.subTest(input_type=type(value).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    solution.measurement_to_phase(value)

    def test_rejects_wrong_width_and_non_binary_characters(self):
        for value in (
            "", "0" * 13, "0" * 15, "0" * 13 + "2", "0" * 13 + "a",
            " " + ZERO_BITS, ZERO_BITS + "\n", "0" * 7 + " " + "0" * 7,
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaises((TypeError, ValueError)):
                    solution.measurement_to_phase(value)


class PhaseResultTests(unittest.TestCase):
    def test_three_conversions_agree_and_diagnostics_contain_only_statistics(self):
        diagnostic_fields = {
            "shots", "distinct_outcomes", "dominant_count", "dominant_probability",
            "conversion_methods_agree", "leading_zero_width_preserved",
        }
        for measured, expected in (
            (ZERO_BITS, 0), ("00000000000001", 1),
            ("10000000000000", 8192), (ARTIFICIAL_BITS, ARTIFICIAL_KEY),
            ("11111111111111", 16383),
        ):
            with self.subTest(measured=measured):
                key, diagnostics = solution.phase_from_counts({measured: 64})
                self.assertEqual(key, expected)
                self.assertEqual(set(diagnostics), diagnostic_fields)
                self.assertEqual(diagnostics["shots"], 64)
                self.assertEqual(diagnostics["distinct_outcomes"], 1)
                self.assertEqual(diagnostics["dominant_count"], 64)
                self.assertEqual(diagnostics["dominant_probability"], 1.0)
                self.assertTrue(diagnostics["conversion_methods_agree"])
                self.assertTrue(diagnostics["leading_zero_width_preserved"])

    def test_zero_frequency_outcomes_do_not_create_a_second_observation(self):
        key, diagnostics = solution.phase_from_counts({ARTIFICIAL_BITS: 64, ZERO_BITS: 0})
        self.assertEqual(key, ARTIFICIAL_KEY)
        self.assertEqual(diagnostics["distinct_outcomes"], 1)

    def test_multiple_positive_outcomes_are_rejected_even_with_a_dominant_peak(self):
        for counts in (
            {ARTIFICIAL_BITS: 63, ZERO_BITS: 1},
            {ARTIFICIAL_BITS: 32, ZERO_BITS: 32},
        ):
            with self.subTest(counts=counts):
                with self.assertRaises((ValueError, RuntimeError)):
                    solution.phase_from_counts(counts)

    def test_rejects_invalid_counts_and_mismatched_shot_totals(self):
        for counts in (
            {}, {ARTIFICIAL_BITS: 0}, {ARTIFICIAL_BITS: -1},
            {ARTIFICIAL_BITS: True}, {ARTIFICIAL_BITS: 64.0},
            {ARTIFICIAL_BITS: 63}, {ARTIFICIAL_BITS: 65},
            {"0" * 13: 64}, {"0" * 13 + "2": 64}, {1: 64},
        ):
            with self.subTest(counts=counts):
                with self.assertRaises((TypeError, ValueError, RuntimeError)):
                    solution.phase_from_counts(counts)

    def test_expected_shots_must_be_a_positive_integer(self):
        for shots in (0, -1, True, 64.0, "64"):
            with self.subTest(shots=shots):
                with self.assertRaises((TypeError, ValueError)):
                    solution.phase_from_counts({ARTIFICIAL_BITS: 64}, expected_shots=shots)


    def test_integer_conversion_disagreement_is_rejected(self):
        with mock.patch.object(solution, "Counts") as counts_type:
            counts_type.return_value.int_outcomes.return_value = {ARTIFICIAL_KEY + 1: 64}
            with self.assertRaisesRegex(RuntimeError, "conversions disagree"):
                solution.phase_from_counts({ARTIFICIAL_BITS: 64})


class RecoveryTests(unittest.TestCase):
    @contextmanager
    def fake_recovery(self, *, qpe_counts=None, check_counts=None):
        if qpe_counts is None:
            qpe_counts = {ARTIFICIAL_BITS: 64}
        if check_counts is None:
            check_counts = {ZERO_BITS: 32}
        unitary = QuantumCircuit(1, name="artificial_unitary")
        eigenstate = QuantumCircuit(1, name="artificial_eigenstate")
        queries = {
            "controlled_power_blocks": 14,
            "equivalent_base_U_applications": 16383,
            "exponents": [1 << j for j in range(14)],
        }
        with (
            mock.patch.object(solution.helper, "build_unitary", return_value=unitary) as load_unitary,
            mock.patch.object(solution.helper, "build_eigenstate", return_value=eigenstate) as load_eigenstate,
            mock.patch.object(solution, "build_circuit", return_value=mock.sentinel.qpe) as build,
            mock.patch.object(
                solution, "build_phase_check_circuit", return_value=mock.sentinel.phase_check
            ) as build_check,
            mock.patch.object(solution, "count_controlled_powers", return_value=queries) as count_powers,
            mock.patch.object(solution, "AerSimulator", return_value=mock.sentinel.simulator) as aer,
            mock.patch.object(solution, "_simulate", side_effect=[qpe_counts, check_counts]) as simulate,
        ):
            yield {
                "unitary": unitary, "eigenstate": eigenstate,
                "load_unitary": load_unitary, "load_eigenstate": load_eigenstate,
                "build": build, "build_check": build_check, "count_powers": count_powers,
                "aer": aer, "simulate": simulate,
            }

    def test_one_qpe_batch_then_one_full_register_phase_check(self):
        with self.fake_recovery() as run:
            phase, diagnostics = solution.recover_phase_with_diagnostics()
        self.assertEqual(phase, ARTIFICIAL_KEY)
        run["load_unitary"].assert_called_once_with()
        run["load_eigenstate"].assert_called_once_with()
        run["build"].assert_called_once_with(unitary=run["unitary"], eigenstate=run["eigenstate"])
        run["build_check"].assert_called_once_with(
            run["unitary"], run["eigenstate"], ARTIFICIAL_KEY, phase_bits=14
        )
        run["simulate"].assert_has_calls([
            mock.call(mock.sentinel.simulator, mock.sentinel.qpe, 64, 707),
            mock.call(mock.sentinel.simulator, mock.sentinel.phase_check, 32, 708),
        ])
        self.assertEqual(run["simulate"].call_count, 2)
        self.assertEqual(diagnostics["total_shots"], 96)
        self.assertEqual(diagnostics["aer_run_calls"], 2)
        self.assertEqual(diagnostics["phase_check_all_zero_shots"], 32)
        self.assertTrue(diagnostics["phase_check_passed"])
        self.assertEqual(diagnostics["controlled_power_blocks_shot_weighted"], 14 * 96)
        self.assertEqual(diagnostics["equivalent_base_U_applications_shot_weighted"], 16383 * 96)
        self.assertFalse(diagnostics["plaintext_hash_verified"])
        self.assertFalse(diagnostics["secret_values_recorded"])
        for forbidden in ("key", "phase", "counts", "bitstring", "plaintext"):
            self.assertNotIn(forbidden, diagnostics)

    def test_nonexact_qpe_result_stops_before_phase_check(self):
        with self.fake_recovery(qpe_counts={ARTIFICIAL_BITS: 63, ZERO_BITS: 1}) as run:
            with self.assertRaises(RuntimeError):
                solution.recover_phase_with_diagnostics()
        run["simulate"].assert_called_once()
        run["build_check"].assert_not_called()

    def test_phase_check_mismatch_or_incomplete_counts_never_retry(self):
        for counts in (
            {"00000000000001": 32},
            {ZERO_BITS: 31, "00000000000001": 1},
            {ZERO_BITS: 31},
            {"0": 32},
        ):
            with self.subTest(counts=counts):
                with self.fake_recovery(check_counts=counts) as run:
                    with self.assertRaisesRegex(RuntimeError, "phase cancellation"):
                        solution.recover_phase_with_diagnostics()
                self.assertEqual(run["simulate"].call_count, 2)
                run["build_check"].assert_called_once()

    def test_simulator_failure_does_not_repeat_either_batch(self):
        for failure_in_check in (False, True):
            with self.subTest(failure_in_check=failure_in_check):
                with self.fake_recovery() as run:
                    failure = RuntimeError("artificial simulator failure")
                    run["simulate"].side_effect = (
                        [{ARTIFICIAL_BITS: 64}, failure] if failure_in_check else failure
                    )
                    with self.assertRaisesRegex(RuntimeError, "artificial simulator failure"):
                        solution.recover_phase_with_diagnostics()
                self.assertEqual(run["simulate"].call_count, 2 if failure_in_check else 1)

    def test_wrong_controlled_power_accounting_precedes_simulation(self):
        with self.fake_recovery() as run:
            run["count_powers"].return_value = {
                "controlled_power_blocks": 13,
                "equivalent_base_U_applications": 8191,
                "exponents": [1 << j for j in range(13)],
            }
            with self.assertRaisesRegex(RuntimeError, "controlled powers"):
                solution.recover_phase_with_diagnostics()
        run["simulate"].assert_not_called()

    def test_time_shortfall_stops_before_phase_check(self):
        clock = [0.0]

        def simulate(*_args):
            clock[0] = 101.0
            return {ARTIFICIAL_BITS: 64}

        with self.fake_recovery() as run:
            run["simulate"].side_effect = simulate
            with mock.patch.object(solution.time, "perf_counter", side_effect=lambda: clock[0]):
                with self.assertRaises(TimeoutError):
                    solution.recover_phase_with_diagnostics()
        run["simulate"].assert_called_once()
        run["build_check"].assert_not_called()

    def test_integer_adapter_returns_only_recovered_phase(self):
        with mock.patch.object(
            solution, "recover_phase_with_diagnostics", return_value=(ARTIFICIAL_KEY, {"shots": 96})
        ) as recover:
            self.assertEqual(solution.recover_phase(), ARTIFICIAL_KEY)
        recover.assert_called_once_with()


class SolveTests(unittest.TestCase):
    def test_missing_classical_module_precedes_data_loading_and_quantum_work(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "recover_phase") as recover,
            mock.patch.object(solution, "load_locked") as load_locked,
        ):
            with self.assertRaisesRegex(NotImplementedError, "tier07_classical"):
                solution.solve()
        recover.assert_not_called()
        load_locked.assert_not_called()

    @contextmanager
    def fake_classical(self, *, verified=True, plaintext="synthetic phase text"):
        classical = ModuleType(CLASSICAL_MODULE)
        classical.decrypt = mock.Mock(return_value=plaintext)
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: classical}),
            mock.patch.object(solution, "recover_phase", return_value=ARTIFICIAL_KEY) as recover,
            mock.patch.object(
                solution, "load_locked",
                return_value={"ciphertext_hex": "9123", "public_parameters": {"key_bits": 14}},
            ) as load_locked,
            mock.patch.object(solution, "is_correct", return_value=verified) as is_correct,
        ):
            yield classical.decrypt, recover, load_locked, is_correct

    def test_delegates_only_the_measured_integer_and_requires_hash_confirmation(self):
        with self.fake_classical() as (decrypt, recover, load_locked, is_correct):
            self.assertEqual(solution.solve(), "synthetic phase text")
        recover.assert_called_once_with()
        load_locked.assert_called_once_with(7)
        decrypt.assert_called_once_with(ARTIFICIAL_KEY, "9123")
        is_correct.assert_called_once_with(7, "synthetic phase text")

    def test_hash_mismatch_does_not_return_plaintext_or_repeat_recovery(self):
        with self.fake_classical(verified=False) as (decrypt, recover, _, is_correct):
            with self.assertRaises(RuntimeError):
                solution.solve()
        recover.assert_called_once_with()
        decrypt.assert_called_once()
        is_correct.assert_called_once()

    def test_classical_result_must_be_text(self):
        with self.fake_classical(plaintext=b"synthetic bytes") as (_, recover, _, is_correct):
            with self.assertRaises(RuntimeError):
                solution.solve()
        recover.assert_called_once_with()
        is_correct.assert_not_called()


if __name__ == "__main__":
    unittest.main()
