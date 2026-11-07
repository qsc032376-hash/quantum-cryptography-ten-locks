"""Synthetic measurement arithmetic only; no real public-key verification."""

import unittest

from submissions.team3.tier10.readout import (
    InconsistentSample,
    candidate_evidence,
    equation_from_counts,
    measurement_from_counts,
    round_frequency,
)


def readout(y_x, y_z, bits=6):
    """Encode artificial raw register readings in printed Z/X order."""
    return format(y_z, f"0{bits}b") + format(y_x, f"0{bits}b")


class FrequencyTests(unittest.TestCase):
    def test_half_integer_uses_upward_not_bankers_rounding(self):
        self.assertEqual(round_frequency(32, 41), 21)
        self.assertEqual(round_frequency(0, 41), 0)
        self.assertEqual(round_frequency(63, 41), 40)

    def test_frequency_wraps_on_the_circle(self):
        self.assertEqual(round_frequency(63, 7), 0)
        self.assertEqual(round_frequency(4, 7, register_bits=3), 4)
        self.assertEqual(round_frequency(7, 1, register_bits=3), 0)

    def test_invalid_raw_reading_or_parameters_are_rejected(self):
        for raw, order, bits in (
            (-1, 41, 6), (64, 41, 6), (True, 41, 6), (1.0, 41, 6),
            (1, 0, 6), (1, -1, 6), (1, True, 6), (1, 41, 0), (1, 41, 6.0),
        ):
            with self.subTest(raw=raw, order=order, bits=bits):
                with self.assertRaises((TypeError, ValueError)):
                    round_frequency(raw, order, bits)


class MappingTests(unittest.TestCase):
    def test_left_z_right_x_without_reversing_either_half(self):
        # Public synthetic example: raw X=5, Z=41 gives u=3, v=26.
        self.assertEqual(measurement_from_counts("101001000101", 41), (15, 3))

    def test_first_component_is_negative_z_frequency(self):
        self.assertEqual(measurement_from_counts(readout(1, 2, 3), 7, 3), (5, 1))
        self.assertEqual(measurement_from_counts(readout(2, 1, 3), 7, 3), (6, 2))

    def test_rejects_unconfirmed_layout_instead_of_guessing(self):
        for layout in ("zx", "auto", None):
            with self.subTest(layout=layout):
                with self.assertRaises(ValueError):
                    measurement_from_counts("0" * 12, 41, layout=layout)

    def test_requires_full_width_binary_counts_keys(self):
        for value in ("", "0" * 11, "0" * 13, "0" * 11 + "2", "0" * 6 + " " + "0" * 6):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    measurement_from_counts(value, 41)
        for value in (None, True, 1, b"0" * 12):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    measurement_from_counts(value, 41)


class CongruenceTests(unittest.TestCase):
    def test_noninvertible_coefficient_returns_partial_congruence(self):
        # u=4, v=8, so 4*a=8 mod 12 becomes a=2 mod 3.
        self.assertEqual(equation_from_counts(readout(21, 43), 12), (2, 3))

    def test_gcd_divisibility_failure_is_an_inconsistent_sample(self):
        # u=4, v=6: gcd(4,12) does not divide 6.
        with self.assertRaises(InconsistentSample):
            equation_from_counts(readout(21, 32), 12)

    def test_zero_equation_is_uninformative_and_zero_coefficient_can_contradict(self):
        self.assertIsNone(equation_from_counts(readout(0, 0), 12))
        self.assertIsNone(equation_from_counts(readout(7, 7, 3), 1, 3))
        with self.assertRaises(InconsistentSample):
            equation_from_counts(readout(0, 5), 12)

    def test_coprime_coefficient_gives_one_full_modulus_candidate(self):
        # u=5, v=10, so a=2 mod 12; no residue-class enumeration is needed.
        self.assertEqual(equation_from_counts(readout(27, 53), 12), (2, 12))


class CandidateEvidenceTests(unittest.TestCase):
    def test_weights_merge_identical_candidates_but_keep_conflicting_rows_separate(self):
        counts = {
            readout(1, 2, 3): 5,
            readout(2, 4, 3): 7,
            readout(1, 5, 3): 3,
            readout(0, 0, 3): 2,
            readout(0, 1, 3): 4,
            readout(7, 7, 3): 0,
        }
        weights, witnesses, diagnostics = candidate_evidence(counts, 7, 3)
        self.assertEqual(weights, {2: 12, 4: 3})
        self.assertEqual(witnesses, {2: (5, 1), 4: (3, 1)})
        self.assertEqual(diagnostics, {
            "total_shots": 21, "distinct_outcomes": 5,
            "informative_shots": 15, "uninformative_shots": 2,
            "inconsistent_shots": 4, "partial_equation_shots": 0,
        })
        observed_pairs = {
            measurement_from_counts(bits, 7, 3) for bits, frequency in counts.items() if frequency > 0
        }
        for candidate, pair in witnesses.items():
            self.assertIn(pair, observed_pairs)
            self.assertEqual((pair[0] + candidate * pair[1]) % 7, 0)

    def test_partial_equations_are_only_counted_and_all_categories_partition_shots(self):
        counts = {
            readout(27, 53): 6,
            readout(21, 43): 8,
            readout(21, 32): 3,
            readout(0, 0): 5,
        }
        weights, witnesses, diagnostics = candidate_evidence(counts, 12)
        self.assertEqual(weights, {2: 6})
        self.assertEqual(witnesses, {2: (2, 5)})
        self.assertEqual(diagnostics, {
            "total_shots": 22, "distinct_outcomes": 4,
            "informative_shots": 6, "uninformative_shots": 5,
            "inconsistent_shots": 3, "partial_equation_shots": 8,
        })
        self.assertEqual(
            diagnostics["total_shots"],
            sum(diagnostics[field] for field in (
                "informative_shots", "uninformative_shots", "inconsistent_shots", "partial_equation_shots"
            )),
        )

    def test_partial_only_data_never_expands_possible_exponents(self):
        weights, witnesses, diagnostics = candidate_evidence({readout(21, 43): 100}, 12)
        self.assertEqual(weights, {})
        self.assertEqual(witnesses, {})
        self.assertEqual(diagnostics["partial_equation_shots"], 100)
        self.assertEqual(diagnostics["informative_shots"], 0)

    def test_zero_can_be_a_complete_candidate_but_order_one_is_uninformative(self):
        weights, witnesses, diagnostics = candidate_evidence({readout(1, 0, 3): 3}, 7, 3)
        self.assertEqual(weights, {0: 3})
        self.assertEqual(witnesses, {0: (0, 1)})
        self.assertEqual(diagnostics["informative_shots"], 3)
        weights, witnesses, diagnostics = candidate_evidence({readout(7, 7, 3): 9}, 1, 3)
        self.assertEqual((weights, witnesses), ({}, {}))
        self.assertEqual(diagnostics["uninformative_shots"], 9)

    def test_empty_and_zero_frequency_counts_produce_no_candidates(self):
        for counts in ({}, {"0" * 12: 0}):
            with self.subTest(counts=counts):
                weights, witnesses, diagnostics = candidate_evidence(counts, 41)
                self.assertEqual(weights, {})
                self.assertEqual(witnesses, {})
                self.assertTrue(all(value == 0 for value in diagnostics.values()))

    def test_bad_counts_raise_format_errors_not_sample_classification(self):
        for counts in (
            {"0" * 12: -1}, {"0" * 12: True}, {"0" * 12: 1.5},
            {"0" * 11: 1}, {"0" * 11 + "2": 0}, {1: 1}, [],
        ):
            with self.subTest(counts=counts):
                with self.assertRaises((TypeError, ValueError)) as caught:
                    candidate_evidence(counts, 41)
                self.assertNotIsInstance(caught.exception, InconsistentSample)


if __name__ == "__main__":
    unittest.main()
