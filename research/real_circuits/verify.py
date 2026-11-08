"""Actual-window and actual-clean-template equivalence, without full-tier states."""
import importlib
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch
import numpy as np
from qiskit.quantum_info import Operator, Statevector
from qiskit.synthesis import synth_mcx_2_clean_kg24
from research.real_circuits.experiments import ROOT, REF58, snapshot, gf2_runs
from research.circuit_optimizer.metrics import compile_metrics


def run():
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='real-verify-') as folder:
        snapshot(REF58, folder, 'verified58')
        module = importlib.import_module('verified58.tier05.solution')
        original, _ = compile_metrics(module.build_circuit())
        candidate, stats, certificates = gf2_runs(original)
        worst = 0.0
        for old, new in certificates:
            assert old.num_qubits <= 5
            error = float(np.max(np.abs(Operator(old).data - Operator(new).data)))
            assert error < 1e-12
            worst = max(worst, error)
        assert original.global_phase == candidate.global_phase
        def measurements(c):
            return [(c.find_bit(i.qubits[0]).index, c.find_bit(i.clbits[0]).index)
                    for i in c.data if i.operation.name == 'measure']
        assert measurements(original) == measurements(candidate) == [(j,j) for j in range(10)]
        # Every non-CX operation and its wire arguments remains unchanged.
        def non_cx(c):
            return [(i.operation, tuple(c.find_bit(q).index for q in i.qubits),
                     tuple(c.find_bit(b).index for b in i.clbits))
                    for i in c.data if i.operation.name != 'cx']
        assert non_cx(original) == non_cx(candidate)
        with patch.object(module.oracle, 'synth_mcx_n_clean_m15', synth_mcx_2_clean_kg24):
            combined_original, _ = compile_metrics(module.build_circuit())
        combined, combined_stats, combined_certificates = gf2_runs(combined_original)
        for old, new in combined_certificates:
            assert old.num_qubits <= 5
            np.testing.assert_allclose(Operator(old).data, Operator(new).data, atol=0, rtol=0)
        assert measurements(combined_original) == measurements(combined)
        assert non_cx(combined_original) == non_cx(combined)
        assert combined_original.global_phase == combined.global_phase
    # Actual nine-control diffuser replacement: all 2^10 data columns on clean ancillas.
    gate = synth_mcx_2_clean_kg24(9)
    assert gate.num_qubits == 12
    maximum = 0.0
    for column in range(1 << 10):
        expected = column ^ (1 << 9 if column & 511 == 511 else 0)
        actual = Statevector.from_int(column, 1 << 12).evolve(gate).data
        target = np.zeros(1 << 12, dtype=complex)
        target[expected] = 1
        error = float(np.max(np.abs(actual-target)))
        assert error < 1e-10
        maximum = max(maximum, error)
    return {'gf2_windows': stats, 'exhaustive_operator_windows': len(certificates),
            'combined_gf2_windows': combined_stats,
            'combined_exhaustive_operator_windows': len(combined_certificates),
            'max_gf2_operator_error': worst, 'same_non_cx_operations': True,
            'measurement_mapping_preserved': True, 'global_phase_preserved': True,
            'mcx9_clean_basis_columns': 1024, 'mcx9_ancillas': 2,
            'max_mcx9_amplitude_error': maximum, 'seconds': time.perf_counter()-started}

if __name__ == '__main__':
    result = run()
    path = ROOT/'research/real_circuits/results/equivalence.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
