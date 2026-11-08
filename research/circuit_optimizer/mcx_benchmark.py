"""Budget-aware exact MCX survey on small synthetic control counts.

No large historical MCX sweeps or production circuits are rerun. Clean
contracts are checked on zero-ancilla columns; dirty contracts on all columns.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RCCXGate, DiagonalGate
from qiskit.quantum_info import Operator
from qiskit.synthesis import (
    synth_mcx_1_clean_kg24, synth_mcx_2_clean_kg24,
    synth_mcx_1_dirty_kg24, synth_mcx_2_dirty_kg24,
    synth_mcx_noaux_hp24,
)

from .metrics import compile_metrics

FAMILIES = {
    "noaux_hp24": ("none", 0, synth_mcx_noaux_hp24),
    "one_clean_kg24": ("clean", 1, synth_mcx_1_clean_kg24),
    "two_clean_kg24": ("clean", 2, synth_mcx_2_clean_kg24),
    "one_dirty_kg24": ("dirty", 1, synth_mcx_1_dirty_kg24),
    "two_dirty_kg24": ("dirty", 2, synth_mcx_2_dirty_kg24),
}


def budget_candidates(controls, clean_budget=0, dirty_budget=0):
    if type(controls) is not int or not 3 <= controls <= 5:
        raise ValueError("Research survey is bounded to 3..5 controls")
    if any(type(x) is not int or x < 0 for x in (clean_budget, dirty_budget)):
        raise ValueError("Ancilla budgets must be nonnegative integers")
    for name, (kind, budget, builder) in FAMILIES.items():
        if (kind == "clean" and budget > clean_budget) or (kind == "dirty" and budget > dirty_budget):
            continue
        circuit = builder(controls)
        workspace = circuit.num_qubits - controls - 1
        if workspace > budget:
            raise AssertionError("Pinned synthesis exceeded its declared workspace")
        yield name, kind, workspace, circuit


def verify_mcx(circuit, controls, clean=False):
    if circuit.num_qubits > 8:
        raise ValueError("Dense verification capped at eight qubits")
    matrix = Operator(circuit).data
    columns = range(1 << (controls + 1)) if clean else range(len(matrix))
    maximum = 0.0
    for column in columns:
        row = column ^ ((1 << controls) if column & ((1 << controls) - 1) == (1 << controls) - 1 else 0)
        expected = np.zeros(len(matrix), dtype=complex)
        expected[row] = 1
        maximum = max(maximum, float(np.max(np.abs(matrix[:, column] - expected))))
    if maximum > 1e-10:
        raise AssertionError(f"MCX amplitude/restoration mismatch: {maximum}")
    return maximum


def corrected_relative_toffoli():
    """RCCX then an explicit output phase correction, in little-endian order.

    This deliberately measures the cost of correcting relative phase; it
    does not assume that the cheaper uncorrected RCCX is an exact CCX.
    """
    circuit = QuantumCircuit(3)
    circuit.append(RCCXGate(), range(3))
    circuit.append(DiagonalGate([1, 1, 1, 1j, 1, -1, 1, -1j]), range(3))
    return circuit


def survey():
    records = []
    for controls in (3, 4, 5):
        for name, kind, workspace, circuit in budget_candidates(controls, 2, 2):
            if name == "one_clean_kg24" and controls in (4, 5):
                # These standalone resource comparisons already appear in
                # the Tier 9 report. Keep the API tests, skip duplicate runs.
                continue
            error = verify_mcx(circuit, controls, clean=kind == "clean")
            compiled, measured = compile_metrics(circuit)
            compiled_error = verify_mcx(compiled, controls, clean=kind == "clean")
            records.append({"controls": controls, "family": name, "ancilla_contract": kind,
                            "workspace": workspace, "max_amplitude_error": max(error, compiled_error),
                            **measured})
    return records
