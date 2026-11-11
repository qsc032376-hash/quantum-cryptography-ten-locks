"""Exact 256x256 operator verification of the selected Tier 9 multiplier blocks."""
import json
import sys
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Operator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from search import MODULUS, WIDTH, emit  # noqa: E402
from submissions.team3.tier08.modular import permutation_table  # noqa: E402


def ideal(multiplier):
    table = permutation_table(multiplier, MODULUS, WIDTH)
    size = 1 << (WIDTH + 1)
    matrix = np.zeros((size, size), dtype=complex)
    for control in (0, 1):
        for x in range(1 << WIDTH):
            y = table[x] if control else x
            matrix[control + (y << 1), control + (x << 1)] = 1
    return matrix


def main():
    data = json.loads((Path(__file__).with_name("search.json")).read_text())
    candidate = data["candidate"]
    worst = 0.0
    for key, ops in candidate.items():
        circuit = emit([tuple(op) for op in ops], WIDTH)
        matrix = Operator(circuit).data
        reference = ideal(int(key))
        error = float(np.max(np.abs(matrix - reference)))
        inverse_error = float(np.max(np.abs(Operator(circuit.inverse()).data - reference.conj().T)))
        worst = max(worst, error, inverse_error)
        print(
            f"multiplier {key}: forward_max_error={error:.3e} "
            f"inverse_max_error={inverse_error:.3e}"
        )
    print("worst", f"{worst:.3e}")


if __name__ == "__main__":
    main()
