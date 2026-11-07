"""Synthetic N=15/N=21 cases only; no challenge modulus is factored here."""

import unittest

from submissions.team3.tier08.order import (
    InsufficientMeasurements,
    factors_from_order,
    measurement_to_integer,
    recover_order,
)


def counts_for(*pairs):
    """Encode artificial twelve-bit readouts and their frequencies."""
    return {format(measured, "012b"): frequency for measured, frequency in pairs}


class MeasurementTests(unittest.TestCase):
    def test_direct_binary_order_and_leading_zeroes(self):
        for bits, expected in (
            ("000000000000", 0), ("000000000001", 1),
            ("100000000000", 2048), ("001001011010", 602),
        ):
            with self.subTest(bits=bits):
                self.assertEqual(measurement_to_integer(bits), expected)
        self.assertEqual(measurement_to_integer("00101", phase_bits=5), 5)

    def test_rejects_nonbinary_or_wrong_width_data(self):
        for bits in ("", "0" * 11, "0" * 13, "0" * 11 + "2", "0" * 12 + "\n"):
            with self.subTest(bits=repr(bits)):
                with self.assertRaises(ValueError):
                    measurement_to_integer(bits)
        for value in (None, True, 1, b"0" * 12):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    measurement_to_integer(value)

    def test_rejects_invalid_width(self):
        for width in (0, -1, True, 12.0):
            with self.subTest(width=width):
                with self.assertRaises((TypeError, ValueError)):
                    measurement_to_integer("0" * 12, phase_bits=width)


class OrderRecoveryTests(unittest.TestCase):
    def test_exact_synthetic_phase_recovers_certified_order(self):
        order, report = recover_order(counts_for((1024, 8), (0, 2)), 2, 15)
        self.assertEqual(order, 4)
        self.assertEqual(report["measured_shots"], 10)
        self.assertEqual(report["distinct_outcomes"], 2)
        self.assertEqual(report["nonzero_shots"], 8)
        self.assertEqual(report["accepted_phase_shots"], 8)
        self.assertEqual(report["accepted_denominator_count"], 1)
        self.assertEqual(report["verified_order"], 4)
        self.assertTrue(report["minimal_order_verified"])
        self.assertEqual(report["minimality_prime_checks"], 1)
        for forbidden in ("p", "q", "factors", "counts", "raw_counts", "bitstrings", "denominators"):
            self.assertNotIn(forbidden, report)

    def test_nonexact_phase_tails_use_exact_continued_fractions(self):
        order, report = recover_order(counts_for((1023, 7), (1025, 5)), 2, 15)
        self.assertEqual(order, 4)
        self.assertEqual(report["distinct_outcomes"], 2)
        self.assertEqual(report["accepted_phase_shots"], 12)
        self.assertEqual(report["accepted_denominator_count"], 1)

    def test_partial_denominators_cannot_invent_unobserved_multiples(self):
        for measured in (2048, 1365):
            with self.subTest(measured=measured):
                with self.assertRaises(InsufficientMeasurements) as caught:
                    recover_order(counts_for((measured, 20)), 2, 21)
                self.assertEqual(caught.exception.diagnostics["lcm_candidate_count"], 1)
                self.assertFalse(caught.exception.diagnostics["minimal_order_verified"])

    def test_lcm_combines_measured_partial_denominators(self):
        order, report = recover_order(counts_for((2048, 7), (1365, 5)), 2, 21)
        self.assertEqual(order, 6)
        self.assertEqual(report["accepted_denominator_count"], 2)
        self.assertEqual(report["lcm_candidate_count"], 3)
        self.assertEqual(report["minimality_prime_checks"], 2)

    def test_outlier_does_not_poison_all_lcm_candidates(self):
        order, report = recover_order(counts_for((2048, 7), (1365, 5), (819, 3), (0, 4)), 2, 21)
        self.assertEqual(order, 6)
        self.assertEqual(report["accepted_denominator_count"], 3)
        self.assertEqual(report["lcm_candidate_count"], 6)
        self.assertLessEqual(report["lcm_candidate_count"], 20)
        self.assertEqual(report["measured_shots"], 19)
        self.assertEqual(report["accepted_phase_shots"], 15)

    def test_verified_observed_multiple_is_minimized_with_a_certificate(self):
        order, report = recover_order(counts_for((341, 9)), 2, 21)
        self.assertEqual(report["verified_period_multiple"], 12)
        self.assertEqual(order, 6)
        self.assertTrue(report["minimal_order_verified"])
        self.assertEqual(report["minimality_prime_checks"], 2)

    def test_zero_empty_or_uninformative_samples_need_more_evidence(self):
        for counts in ({}, counts_for((0, 64)), counts_for((1, 32)),
                       counts_for((4095, 32)), counts_for((1024, 0))):
            with self.subTest(counts=counts):
                with self.assertRaises(InsufficientMeasurements) as caught:
                    recover_order(counts, 2, 15)
                self.assertIsInstance(caught.exception, RuntimeError)
                self.assertIsNone(caught.exception.diagnostics["verified_order"])

    def test_failed_modular_verification_is_insufficient_evidence(self):
        with self.assertRaises(InsufficientMeasurements):
            recover_order(counts_for((512, 32)), 2, 21)

    def test_duplicate_frequency_changes_statistics_not_denominator_count(self):
        order, report = recover_order(counts_for((1024, 100), (3072, 25)), 2, 15)
        self.assertEqual(order, 4)
        self.assertEqual(report["accepted_denominator_count"], 1)
        self.assertEqual(report["accepted_phase_shots"], 125)

    def test_bad_inputs_are_not_resampling_requests(self):
        for counts, base, modulus, width in (
            ({"0" * 12: -1}, 2, 15, 12),
            ({"0" * 12: True}, 2, 15, 12),
            ({"0" * 12: 1.5}, 2, 15, 12),
            ({"0" * 11: 1}, 2, 15, 12),
            ({"0" * 12: 1}, True, 15, 12),
            ({"0" * 12: 1}, 2, True, 12),
            ({"0" * 12: 1}, 1, 15, 12),
            ({"0" * 12: 1}, 3, 15, 12),
            ({"0" * 12: 1}, 2, 15, 0),
            ([], 2, 15, 12),
        ):
            with self.subTest(base=base, modulus=modulus, width=width):
                with self.assertRaises((TypeError, ValueError)):
                    recover_order(counts, base, modulus, width)


class FactorPostprocessingTests(unittest.TestCase):
    def test_factors_from_measured_synthetic_orders(self):
        first_order, _ = recover_order(counts_for((1024, 16)), 2, 15)
        self.assertEqual(factors_from_order(2, 15, first_order), (3, 5))
        second_order, _ = recover_order(counts_for((2048, 8), (1365, 8)), 2, 21)
        self.assertEqual(factors_from_order(2, 21, second_order), (3, 7))

    def test_nonminimal_order_multiple_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not minimal"):
            factors_from_order(2, 15, 8)

    def test_odd_order_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "odd order"):
            factors_from_order(4, 21, 3)

    def test_trivial_half_order_power_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "half-order"):
            factors_from_order(5, 21, 6)

    def test_invalid_period_or_noncoprime_base_is_rejected(self):
        for base, modulus, order in ((2, 15, 3), (3, 15, 4), (2, 15, 0), (2, 15, True)):
            with self.subTest(base=base, modulus=modulus, order=order):
                with self.assertRaises((TypeError, ValueError)):
                    factors_from_order(base, modulus, order)


if __name__ == "__main__":
    unittest.main()
