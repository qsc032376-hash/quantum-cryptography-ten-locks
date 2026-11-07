"""Synthetic GF(2) tests; no oracle data, key recovery, or quantum execution."""

import unittest

from submissions.team3.tier04.gf2 import recover_unique_nonzero, row_reduce


def orthogonal_basis(period, width):
    """Construct width-1 independent synthetic rows perpendicular to period.

    Give every non-anchor column its own coefficient and cancel its dot
    product with a chosen nonzero period column. No candidates are enumerated.
    """
    anchor = next(column for column in range(width) if period & (1 << column))
    return [
        (1 << column) | ((1 << anchor) if period & (1 << column) else 0)
        for column in range(width)
        if column != anchor
    ]


class RowReductionTests(unittest.TestCase):
    def test_known_rref_and_little_endian_column_numbers(self):
        # x1+x2=0, x1+x3=0, and their redundant sum x2+x3=0.
        reduced, pivots = row_reduce([0b0110, 0b1010, 0b1100], n_bits=4)
        self.assertEqual(reduced, [0b1010, 0b1100])
        self.assertEqual(pivots, [1, 2])

    def test_empty_and_zero_rows(self):
        self.assertEqual(row_reduce([]), ([], []))
        self.assertEqual(row_reduce([0, 0, 0]), ([], []))

    def test_rref_uses_pivot_order_instead_of_integer_value_order(self):
        rows = [0b1010, 0b0001, 0b0100, 0, 0b1010, 0b0101]
        self.assertEqual(row_reduce(rows, 4), ([0b0001, 0b1010, 0b0100], [0, 1, 2]))
        self.assertEqual(recover_unique_nonzero(rows, 4), 0b1010)

    def test_duplicate_zero_and_reordered_equations_have_same_rref(self):
        original = [0b0110, 0b1010, 0b1100]
        variants = (
            list(reversed(original)),
            [0, original[2], original[0], original[2], 0, original[1]],
        )
        for rows in variants:
            with self.subTest(rows=rows):
                self.assertEqual(row_reduce(rows, 4), ([0b1010, 0b1100], [1, 2]))

    def test_accepts_generators_without_mutating_input_lists(self):
        rows = [0b0110, 0b1010, 0b1100]
        before = list(rows)
        expected = row_reduce(rows, 4)
        self.assertEqual(rows, before)
        self.assertEqual(row_reduce((row for row in rows), 4), expected)


class NullVectorRecoveryTests(unittest.TestCase):
    def test_ten_bit_asymmetric_period_from_rank_nine(self):
        synthetic_period = 0b1010010110
        rows = orthogonal_basis(synthetic_period, 10)
        reduced, pivots = row_reduce(rows)
        self.assertEqual(len(reduced), 9)
        self.assertEqual(len(pivots), 9)
        recovered = recover_unique_nonzero(rows)
        self.assertEqual(recovered, synthetic_period)
        self.assertTrue(all((row & recovered).bit_count() % 2 == 0 for row in rows))

    def test_recovery_preserves_bit_positions_and_leading_zeroes(self):
        for period in (1, 1 << 9, 0b0001001011):
            with self.subTest(period=period):
                self.assertEqual(recover_unique_nonzero(orthogonal_basis(period, 10)), period)

    def test_recovery_ignores_zero_duplicate_and_reordered_rows(self):
        period = 0b1010010110
        rows = orthogonal_basis(period, 10)
        equations = [0, *reversed(rows), rows[0], rows[4], 0]
        self.assertEqual(recover_unique_nonzero(iter(equations)), period)

    def test_underdetermined_systems_are_rejected(self):
        for rows in ([], [0, 0], [1 << column for column in range(8)]):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "Underdetermined"):
                recover_unique_nonzero(rows)

    def test_full_rank_has_no_nonzero_null_vector(self):
        rows = [1 << column for column in range(10)]
        with self.assertRaisesRegex(ValueError, "full rank"):
            recover_unique_nonzero(rows)

    def test_one_bit_boundary(self):
        self.assertEqual(row_reduce([], 1), ([], []))
        self.assertEqual(recover_unique_nonzero([], 1), 1)
        self.assertEqual(recover_unique_nonzero([0, 0], 1), 1)
        self.assertEqual(row_reduce([0, 1, 1], 1), ([1], [0]))
        with self.assertRaisesRegex(ValueError, "full rank"):
            recover_unique_nonzero([1], 1)


class InputValidationTests(unittest.TestCase):
    def test_rejects_noninteger_or_boolean_width(self):
        for function in (row_reduce, recover_unique_nonzero):
            for width in (True, False, 10.0, "10", None):
                with self.subTest(function=function.__name__, width=width):
                    with self.assertRaises(TypeError):
                        function([], width)

    def test_rejects_nonpositive_width(self):
        for function in (row_reduce, recover_unique_nonzero):
            for width in (0, -1):
                with self.subTest(function=function.__name__, width=width):
                    with self.assertRaises(ValueError):
                        function([], width)

    def test_rejects_noninteger_or_boolean_rows(self):
        for function in (row_reduce, recover_unique_nonzero):
            for row in (True, False, 1.0, "1", None, [1]):
                with self.subTest(function=function.__name__, row=row):
                    with self.assertRaises(TypeError):
                        function([row])

    def test_rejects_negative_or_out_of_range_rows(self):
        for function in (row_reduce, recover_unique_nonzero):
            for row in (-1, 1 << 10, (1 << 10) + 1):
                with self.subTest(function=function.__name__, row=row):
                    with self.assertRaises(ValueError):
                        function([row])


if __name__ == "__main__":
    unittest.main()
