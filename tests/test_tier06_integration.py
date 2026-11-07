"""Synthetic checks of the Tier 6 classical handoff and bounded supplement."""

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch, sentinel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from submissions.team3.tier06 import solution


class Tier06IntegrationTests(unittest.TestCase):
    def test_multiple_checksum_hits_are_disambiguated_by_full_hash(self):
        incorrect = "QC-06: synthetic checksum collision"
        correct = "QC-06: synthetic confirmed"
        filter_candidates = Mock(return_value=[incorrect, correct])

        def recover(*, confirm_candidates):
            self.assertTrue(confirm_candidates([5, 12]))
            return solution.CandidateRecovery([5, 12], {}, {"search_shots": 64})

        with (patch.object(solution, "_load_filter", return_value=filter_candidates),
              patch.object(solution, "_public_inputs", return_value=(b"\x91\x23", 42)),
              patch.object(solution, "recover_candidates_with_diagnostics", new=recover),
              patch.object(solution, "is_correct", side_effect=lambda tier, text: text == correct) as check):
            text, metrics = solution._solve_with_diagnostics()

        self.assertEqual(text, correct)
        filter_candidates.assert_called_once_with(6, [5, 12], "9123", 42)
        self.assertEqual(check.call_count, 2)
        self.assertEqual((metrics["checksum_utf8_passes"], metrics["hash_passes"]), (2, 1))

    def test_missing_space_or_wrong_tier_is_rejected_even_with_mocked_hash_hit(self):
        for text in ("QC-06:no space", "QC-05: wrong tier", "Q only"):
            with self.subTest(text=text):
                def recover(*, confirm_candidates):
                    self.assertFalse(confirm_candidates([5]))
                    return solution.CandidateRecovery([5], {}, {"search_shots": 64})

                with (patch.object(solution, "_load_filter", return_value=Mock(return_value=[text])),
                      patch.object(solution, "_public_inputs", return_value=(b"\x91", 42)),
                      patch.object(solution, "recover_candidates_with_diagnostics", new=recover),
                      patch.object(solution, "is_correct", return_value=True),
                      self.assertRaisesRegex(RuntimeError, "one hash-confirmed")):
                    solution.solve()

    def test_missed_hash_uses_one_remaining_batch_without_rechecking_old_keys(self):
        first_key, second_key = "00000000000101", "00000000001001"
        measurements = [{"0": 1976, "1": 72}, {first_key: 64}, {first_key: 16, second_key: 48}]
        estimate = {
            "iterations": 12, "planned_search_shots": 64, "target_marked_draws": 40,
            "predicted_success_lower95": 0.8, "marked_interval95": [1, 100],
        }
        correct = "QC-06: synthetic second batch"
        filter_candidates = Mock(side_effect=[[], [correct]])

        with (patch.object(solution, "_load_filter", return_value=filter_candidates),
              patch.object(solution, "_public_inputs", return_value=(b"\x91", 42)),
              patch.object(solution, "is_correct", side_effect=lambda tier, text: text == correct),
              patch.object(solution, "MAX_SEARCH_SHOTS", 128),
              patch.object(solution, "AerSimulator"),
              patch.object(solution, "build_calibration_circuit", return_value=sentinel.pilot) as pilot,
              patch.object(solution, "build_circuit", return_value=sentinel.search) as search,
              patch.object(solution, "count_oracle_calls", side_effect=[
                  {"phase": 1, "bit_predicate": 1}, {"phase": 12, "bit_predicate": 0},
              ]),
              patch.object(solution, "estimate_marked_count", return_value=estimate),
              patch.object(solution, "_simulate", side_effect=measurements) as run,
              patch.object(solution, "ToyCipher") as cipher):
            cipher.return_value.decrypt_byte.return_value = ord("Q")
            text, metrics = solution._solve_with_diagnostics()

        self.assertEqual(text, correct)
        pilot.assert_called_once()
        search.assert_called_once()
        self.assertEqual([call.args[2] for call in run.call_args_list], [2048, 64, 64])
        self.assertEqual([call.args[1] for call in filter_candidates.call_args_list], [[5], [9]])
        self.assertTrue(metrics["hash_supplement_requested"])
        self.assertEqual(metrics["search_shots"], 128)


if __name__ == "__main__":
    unittest.main()
