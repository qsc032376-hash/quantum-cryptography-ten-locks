"""Tier 6 unit checks with artificial measurements and mocked cipher calls."""

from contextlib import contextmanager
import math
import sys
from types import ModuleType
import unittest
from unittest import mock

from qiskit import QuantumCircuit

from submissions.team3.tier06 import solution


CLASSICAL_MODULE = "submissions.team3.toy_cipher_classical"


class MeasurementTests(unittest.TestCase):
    def test_fourteen_bit_order_and_leading_zeroes(self):
        for measured, expected in (
            ("00000000000000", 0),
            ("00000000000001", 1),
            ("10000000000000", 8192),
            ("00100101101001", 2409),
            ("11111111111111", 16383),
        ):
            with self.subTest(measured=measured):
                self.assertEqual(solution.measurement_to_key(measured), expected)

    def test_rejects_non_string_measurements(self):
        for measured in (None, True, 1, 1.5, b"0" * 14, [0] * 14):
            with self.subTest(input_type=type(measured).__name__):
                with self.assertRaises(ValueError):
                    solution.measurement_to_key(measured)

    def test_rejects_malformed_register_strings(self):
        for measured in (
            "", "0" * 13, "0" * 15, "0" * 13 + "2", "0" * 13 + "a",
            " " + "0" * 14, "0" * 14 + "\n", "0" * 7 + " " + "0" * 7,
        ):
            with self.subTest(measured=repr(measured)):
                with self.assertRaises(ValueError):
                    solution.measurement_to_key(measured)


class CandidateTests(unittest.TestCase):
    def test_checks_each_measured_key_once_and_counts_all_shots(self):
        ciphertext = b"\x91\x23\x45\x67"
        counts = {
            "00000000000101": 10,
            "10000000000000": 5,
            "11111111111111": 2,
        }
        instances = {}

        def cipher_for(key, width):
            self.assertEqual(width, 14)
            instance = mock.Mock()
            instance.decrypt_byte.return_value = ord("Q") if key in {5, 16383} else ord("R")
            instances[key] = instance
            return instance

        with mock.patch.object(solution, "ToyCipher", side_effect=cipher_for) as cipher:
            candidates, report = solution.deduplicate_candidates(counts, ciphertext)

        self.assertCountEqual(candidates, [5, 16383])
        self.assertEqual(len(candidates), 2)
        self.assertEqual(cipher.call_count, 3)
        self.assertEqual({call.args for call in cipher.call_args_list}, {(5, 14), (8192, 14), (16383, 14)})
        for instance in instances.values():
            instance.decrypt_byte.assert_called_once()
            self.assertEqual(instance.decrypt_byte.call_args.args[0], ciphertext[0])
            instance.decrypt.assert_not_called()
        self.assertEqual(report["measured_unique"], 3)
        self.assertEqual(report["prefix_candidates"], 2)
        self.assertEqual(report["prefix_shots"], 12)
        self.assertEqual(report["total_shots"], 17)
        self.assertNotIn("keys", report)
        self.assertNotIn("counts", report)

    def test_nonmatching_measured_keys_produce_no_candidates(self):
        with mock.patch.object(solution, "ToyCipher") as cipher:
            cipher.return_value.decrypt_byte.return_value = ord("R")
            candidates, report = solution.deduplicate_candidates(
                {"00100101101001": 128}, b"\x91\x23"
            )
        self.assertEqual(candidates, [])
        cipher.assert_called_once_with(2409, 14)
        self.assertEqual(report["measured_unique"], 1)
        self.assertEqual(report["prefix_candidates"], 0)
        self.assertEqual(report["prefix_shots"], 0)
        self.assertEqual(report["total_shots"], 128)

    def test_rejects_invalid_frequencies(self):
        for count in (-1, True, 1.5, "1"):
            with self.subTest(count=count):
                with mock.patch.object(solution, "ToyCipher") as cipher:
                    with self.assertRaises((TypeError, ValueError, RuntimeError)):
                        solution.deduplicate_candidates({"0" * 14: count}, b"\x91")
                cipher.assert_not_called()

    def test_zero_frequency_entries_are_not_checked(self):
        with mock.patch.object(solution, "ToyCipher") as cipher:
            candidates, report = solution.deduplicate_candidates({"0" * 14: 0}, b"\x91")
        cipher.assert_not_called()
        self.assertEqual(candidates, [])
        self.assertEqual(report["measured_unique"], 0)
        self.assertEqual(report["total_shots"], 0)

    def test_rejects_malformed_measured_keys(self):
        for measured in ("0" * 13, "0" * 13 + "2", 1):
            with self.subTest(measured=measured):
                with mock.patch.object(solution, "ToyCipher") as cipher:
                    with self.assertRaises((TypeError, ValueError)):
                        solution.deduplicate_candidates({measured: 1}, b"\x91")
                cipher.assert_not_called()


class MarkedCountEstimationTests(unittest.TestCase):
    def test_estimate_comes_from_measured_hits_not_fixed_sixty_four(self):
        smaller = solution.estimate_marked_count(72, 2048)
        larger = solution.estimate_marked_count(96, 2048)
        self.assertEqual(smaller["p_hat"], 72 / 2048)
        self.assertEqual(larger["p_hat"], 96 / 2048)
        self.assertGreater(larger["marked_estimate"], smaller["marked_estimate"])
        self.assertLess(larger["iterations"], smaller["iterations"])
        self.assertGreater(smaller["marked_estimate"], 64)
        self.assertLess(smaller["marked_estimate"], 66)

    def test_probability_inversion_and_confidence_interval(self):
        report = solution.estimate_marked_count(72, 2048)
        theta = math.asin(math.sqrt(report["marked_estimate"] / 16384))
        self.assertAlmostEqual(math.sin(3 * theta) ** 2, 72 / 2048, places=12)
        lower, upper = report["marked_interval95"]
        self.assertLess(lower, report["marked_estimate"])
        self.assertGreater(upper, report["marked_estimate"])
        self.assertGreater(lower, 0)
        self.assertLess(upper, 16384 / 4)
        self.assertLess(lower, 64)
        self.assertGreater(upper, 64)

    def test_larger_pilot_sample_tightens_interval_at_same_rate(self):
        smaller = solution.estimate_marked_count(72, 2048)
        larger = solution.estimate_marked_count(144, 4096)
        self.assertAlmostEqual(smaller["marked_estimate"], larger["marked_estimate"])
        small_interval = smaller["marked_interval95"]
        large_interval = larger["marked_interval95"]
        self.assertLess(large_interval[1] - large_interval[0], small_interval[1] - small_interval[0])

    def test_iteration_and_search_budgets_and_conservative_probability(self):
        for hits in (40, 72, 96):
            with self.subTest(hits=hits):
                report = solution.estimate_marked_count(hits, 2048)
                iterations = report["iterations"]
                self.assertIs(type(iterations), int)
                self.assertGreaterEqual(iterations, 1)
                self.assertLessEqual(iterations, 24)
                self.assertIs(type(report["planned_search_shots"]), int)
                self.assertGreaterEqual(report["planned_search_shots"], 1)
                self.assertLessEqual(report["planned_search_shots"], 1024)
                self.assertGreater(report["target_marked_draws"], 0)
                lower_probability = report["predicted_success_lower95"]
                self.assertGreater(lower_probability, 0)
                self.assertLessEqual(lower_probability, report["predicted_success_probability"] + 1e-12)
                theta = math.asin(math.sqrt(report["marked_estimate"] / 16384))
                self.assertAlmostEqual(
                    report["predicted_success_probability"],
                    math.sin((2 * iterations + 1) * theta) ** 2,
                    places=12,
                )
                lower, upper = report["marked_interval95"]
                for fraction in (0, 0.25, 0.5, 0.75, 1):
                    marked = lower + fraction * (upper - lower)
                    angle = math.asin(math.sqrt(marked / 16384))
                    probability = math.sin((2 * iterations + 1) * angle) ** 2
                    self.assertLessEqual(lower_probability, probability + 1e-12)

    def test_rejects_zero_all_or_invalid_pilot_hits(self):
        for hits, shots in (
            (0, 512), (512, 512), (-1, 512), (513, 512), (1, 0),
            (True, 512), (1, True), (1.5, 512), (1, 512.0),
        ):
            with self.subTest(hits=hits, shots=shots):
                with self.assertRaises((TypeError, ValueError, RuntimeError)):
                    solution.estimate_marked_count(hits, shots)

    def test_rejects_estimates_exceeding_iteration_or_coverage_budget(self):
        for hits in (1, 2047):
            with self.subTest(hits=hits):
                with self.assertRaises(ValueError):
                    solution.estimate_marked_count(hits, 2048)


class CircuitLayoutTests(unittest.TestCase):
    def test_search_and_calibration_measure_different_registers(self):
        with (
            mock.patch.object(solution, "build_phase_oracle", return_value=QuantumCircuit(22)),
            mock.patch.object(solution, "build_diffuser", return_value=QuantumCircuit(22)),
            mock.patch.object(solution, "build_bit_oracle", return_value=QuantumCircuit(23)),
            mock.patch.object(solution, "load_locked") as load_locked,
        ):
            search = solution.build_circuit(12, ciphertext=b"\x91\x23")
            calibration = solution.build_calibration_circuit(ciphertext=b"\x91\x23")
        load_locked.assert_not_called()
        self.assertEqual((search.num_qubits, search.num_clbits), (22, 14))
        self.assertEqual(solution.count_oracle_calls(search), {"phase": 12, "bit_predicate": 0})
        self.assertEqual((calibration.num_qubits, calibration.num_clbits), (23, 1))
        self.assertEqual(solution.count_oracle_calls(calibration), {"phase": 1, "bit_predicate": 1})
        self.assertEqual(
            [(search.find_bit(item.qubits[0]).index, search.find_bit(item.clbits[0]).index)
             for item in search.data if item.operation.name == "measure"],
            [(index, index) for index in range(14)],
        )
        self.assertEqual(
            [(calibration.find_bit(item.qubits[0]).index, calibration.find_bit(item.clbits[0]).index)
             for item in calibration.data if item.operation.name == "measure"],
            [(22, 0)],
        )


class RecoveryTests(unittest.TestCase):
    @contextmanager
    def fake_recovery(self, search_counts, *, target=40, planned_shots=64):
        estimate = {
            "iterations": 12, "planned_search_shots": planned_shots,
            "target_marked_draws": target, "predicted_success_lower95": 0.8,
            "marked_interval95": [1, 100],
        }
        pilot = {"0": 1976, "1": 72}
        instances = {}

        def cipher_for(key, width):
            self.assertEqual(width, 14)
            instance = mock.Mock()
            instance.decrypt_byte.return_value = ord("Q") if key in {5, 16383} else ord("R")
            instances[key] = instance
            return instance

        with (
            mock.patch.object(solution, "_public_inputs", return_value=(b"\x91\x23", 42)),
            mock.patch.object(solution, "AerSimulator") as aer,
            mock.patch.object(
                solution, "build_calibration_circuit", return_value=mock.sentinel.calibration
            ) as calibration,
            mock.patch.object(solution, "build_circuit", return_value=mock.sentinel.search) as build,
            mock.patch.object(
                solution, "count_oracle_calls",
                side_effect=[{"phase": 1, "bit_predicate": 1}, {"phase": 12, "bit_predicate": 0}],
            ),
            mock.patch.object(solution, "estimate_marked_count", return_value=estimate) as estimate_call,
            mock.patch.object(solution, "_simulate", side_effect=[pilot, *search_counts]) as simulate,
            mock.patch.object(solution, "ToyCipher", side_effect=cipher_for) as cipher,
        ):
            yield {
                "aer": aer, "calibration": calibration, "build": build,
                "estimate": estimate_call, "simulate": simulate,
                "cipher": cipher, "instances": instances,
            }

    def test_one_pilot_and_one_successful_search_batch(self):
        with self.fake_recovery([{"00000000000101": 48, "10000000000000": 16}]) as run:
            result = solution.recover_candidates_with_diagnostics()
        self.assertEqual(result.candidates, [5])
        self.assertEqual(run["simulate"].call_count, 2)
        run["estimate"].assert_called_once_with(72, 2048)
        self.assertEqual([call.args[2] for call in run["simulate"].call_args_list], [2048, 64])
        self.assertEqual(result.diagnostics["search_shots"], 64)
        self.assertEqual(result.diagnostics["aer_run_calls"], 2)
        self.assertEqual(result.diagnostics["phase_queries_shot_weighted"], 2048 + 12 * 64)
        self.assertEqual(result.diagnostics["bit_predicate_queries_shot_weighted"], 2048)
        self.assertTrue(result.diagnostics["coverage_target_draws_reached"])
        self.assertFalse(result.diagnostics["complete_candidate_coverage_proven"])
        self.assertNotIn("candidates=", repr(result))
        self.assertNotIn("counts=", repr(result))

    def test_one_bounded_supplement_checks_each_unique_key_only_once(self):
        batches = [
            {"00000000000101": 48, "10000000000000": 16},
            {"00000000000101": 20, "11111111111111": 44},
        ]
        with self.fake_recovery(batches, target=80) as run:
            result = solution.recover_candidates_with_diagnostics()
        self.assertEqual(result.candidates, [5, 16383])
        self.assertEqual(run["simulate"].call_count, 3)
        self.assertEqual([call.args[2] for call in run["simulate"].call_args_list], [2048, 64, 64])
        self.assertEqual(run["cipher"].call_count, 3)
        self.assertEqual([call.args[0] for call in run["cipher"].call_args_list].count(5), 1)
        self.assertEqual(result.counts["00000000000101"], 68)
        self.assertEqual(result.diagnostics["public_prefix_shots"], 112)
        self.assertEqual(result.diagnostics["classical_unique_candidates_checked"], 3)
        self.assertEqual(result.diagnostics["aer_run_calls"], 3)

    def test_failed_amplification_does_not_start_another_batch(self):
        with self.fake_recovery([{"00000000000101": 16, "10000000000000": 48}]) as run:
            with self.assertRaisesRegex(RuntimeError, "amplification"):
                solution.recover_candidates_with_diagnostics()
        self.assertEqual(run["simulate"].call_count, 2)

    def test_total_shots_remain_bounded_even_when_coverage_target_is_missed(self):
        batches = [
            {"00000000000101": 600, "10000000000000": 360},
            {"00000000000101": 64},
        ]
        with self.fake_recovery(batches, target=1000, planned_shots=960) as run:
            result = solution.recover_candidates_with_diagnostics()
        self.assertEqual(run["simulate"].call_count, 3)
        self.assertEqual([call.args[2] for call in run["simulate"].call_args_list], [2048, 960, 64])
        self.assertEqual(result.diagnostics["search_shots"], 1024)
        self.assertFalse(result.diagnostics["coverage_target_draws_reached"])
        self.assertFalse(result.diagnostics["complete_candidate_coverage_proven"])

    def test_simulator_failure_is_not_retried(self):
        with self.fake_recovery([]) as run:
            run["simulate"].side_effect = RuntimeError("artificial simulator failure")
            with self.assertRaisesRegex(RuntimeError, "artificial simulator failure"):
                solution.recover_candidates_with_diagnostics()
        run["simulate"].assert_called_once()
        run["build"].assert_not_called()
        run["cipher"].assert_not_called()

    def test_supplement_is_skipped_when_another_batch_would_exceed_time_budget(self):
        clock = [0.0]

        def simulate(_simulator, circuit, _shots, _seed):
            if circuit is mock.sentinel.calibration:
                return {"0": 1976, "1": 72}
            clock[0] = 60.0
            return {"00000000000101": 48, "10000000000000": 16}

        with self.fake_recovery([], target=80) as run:
            run["simulate"].side_effect = simulate
            with mock.patch.object(solution.time, "perf_counter", side_effect=lambda: clock[0]):
                result = solution.recover_candidates_with_diagnostics()
        self.assertEqual(run["simulate"].call_count, 2)
        self.assertTrue(result.diagnostics["supplemental_batch_skipped_for_time"])
        self.assertFalse(result.diagnostics["coverage_target_draws_reached"])
        self.assertEqual(result.diagnostics["search_shots"], 64)


class SolveTests(unittest.TestCase):
    def test_missing_classical_module_precedes_data_loading_and_quantum_work(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "_public_inputs") as public_inputs,
            mock.patch.object(solution, "recover_candidates") as recover,
        ):
            with self.assertRaisesRegex(NotImplementedError, "toy_cipher_classical"):
                solution.solve()
        public_inputs.assert_not_called()
        recover.assert_not_called()

    @contextmanager
    def fake_classical(self, plaintexts, verified_texts):
        classical = ModuleType(CLASSICAL_MODULE)
        classical.filter_candidates = mock.Mock(return_value=plaintexts)
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: classical}),
            mock.patch.object(solution, "_public_inputs", return_value=(b"\x91\x23", 42)),
            mock.patch.object(solution, "recover_candidates", return_value=[5, 16383]) as recover,
            mock.patch.object(
                solution, "is_correct", side_effect=lambda tier, text: text in verified_texts
            ) as is_correct,
        ):
            yield classical.filter_candidates, recover, is_correct

    def test_multiple_checksum_hits_require_one_hash_confirmed_plaintext(self):
        with self.fake_classical(
            ["synthetic checksum collision", "synthetic verified"], {"synthetic verified"}
        ) as (filter_candidates, recover, is_correct):
            self.assertEqual(solution.solve(), "synthetic verified")
        filter_candidates.assert_called_once_with(6, [5, 16383], "9123", 42)
        recover.assert_called_once_with()
        self.assertEqual(is_correct.call_count, 2)

    def test_no_or_multiple_hash_confirmed_plaintexts_fail(self):
        for plaintexts, verified in (
            ([], set()),
            (["synthetic collision"], set()),
            (["synthetic first", "synthetic second"], {"synthetic first", "synthetic second"}),
        ):
            with self.subTest(plaintexts=plaintexts):
                with self.fake_classical(plaintexts, verified):
                    with self.assertRaisesRegex(RuntimeError, "one hash-confirmed"):
                        solution.solve()

    def test_classical_contract_requires_a_list_of_strings(self):
        for plaintexts in ("synthetic text", [b"synthetic bytes"], None):
            with self.subTest(response_type=type(plaintexts).__name__):
                with self.fake_classical(plaintexts, set()) as (_, _, is_correct):
                    with self.assertRaises(TypeError):
                        solution.solve()
                is_correct.assert_not_called()


if __name__ == "__main__":
    unittest.main()
