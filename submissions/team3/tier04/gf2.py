"""Integer-row linear algebra over GF(2), with bit j representing column j.

The functions perform Gaussian elimination, never enumerate candidate vectors.
Inputs may contain zero, repeated, or arbitrarily ordered equations. Caller-owned
lists are not modified; input iterables are consumed once and copied for reduction.
"""


def _validated_rows(rows, n_bits):
    if type(n_bits) is not int:
        raise TypeError("n_bits must be an integer, not bool")
    if n_bits < 1:
        raise ValueError("n_bits must be positive")

    limit = 1 << n_bits
    validated = []
    for row in rows:
        if type(row) is not int:
            raise TypeError("Every row must be an integer, not bool")
        if not 0 <= row < limit:
            raise ValueError("Each row must satisfy 0 <= row < 2**n_bits")
        validated.append(row)
    return validated


def _reduce_validated(rows, n_bits):
    reduced = list(rows)
    pivot_columns = []
    rank = 0
    for column in range(n_bits):
        mask = 1 << column
        pivot_index = next(
            (index for index in range(rank, len(reduced)) if reduced[index] & mask),
            None,
        )
        if pivot_index is None:
            continue
        reduced[rank], reduced[pivot_index] = reduced[pivot_index], reduced[rank]
        pivot_row = reduced[rank]
        for index in range(len(reduced)):
            if index != rank and reduced[index] & mask:
                reduced[index] ^= pivot_row
        pivot_columns.append(column)
        rank += 1
        if rank == len(reduced):
            break
    return reduced[:rank], pivot_columns


def row_reduce(rows, n_bits=10) -> tuple[list[int], list[int]]:
    """Return nonzero RREF rows and their ascending pivot-column indices.

    Rows are integers in [0, 2**n_bits). Column 0 is the least significant
    bit. A pivot is eliminated from every other row, not just later rows.
    Empty and all-zero systems return ([], []). Booleans are not integers
    for this interface, for either rows or the positive width.
    """
    return _reduce_validated(_validated_rows(rows, n_bits), n_bits)


def recover_unique_nonzero(rows, n_bits=10) -> int:
    """Recover the only nonzero vector s satisfying row dot s == 0 mod 2.

    Rank n_bits-1 leaves exactly one free variable. Setting it to one and
    substituting into the RREF determines s; setting it to zero gives only
    the zero vector. Lower rank is underdetermined, and full rank has no
    nonzero solution. Every original equation is checked before returning.
    """
    original = _validated_rows(rows, n_bits)
    reduced, pivot_columns = _reduce_validated(original, n_bits)
    rank = len(pivot_columns)
    if rank == n_bits:
        raise ValueError("No nonzero null vector: the system has full rank")
    if rank < n_bits - 1:
        raise ValueError(
            "Underdetermined system: rank must equal n_bits - 1 "
            "for a unique nonzero vector"
        )

    pivots = set(pivot_columns)
    free_column = next(column for column in range(n_bits) if column not in pivots)
    free_mask = 1 << free_column
    solution = free_mask
    for row, pivot_column in zip(reduced, pivot_columns):
        if row & free_mask:
            solution |= 1 << pivot_column

    if solution == 0 or any((row & solution).bit_count() % 2 for row in original):
        raise ArithmeticError("GF(2) null-vector verification failed")
    return solution
