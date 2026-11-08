"""Phase-sensitive tests of the complete clean-MCX synthesis contract.

The one- and two-clean KG24 templates are compared against an analytic MCX
on every input column whose auxiliary bits start at zero. Equality of these
complex columns covers arbitrary coherent data states and entanglement with
an external reference, while also proving auxiliary restoration. No phase
is fitted or discarded. No claim is made about auxiliary inputs equal to one.

Only synthetic primitive matrices are constructed: no Aer, challenge data,
modular arithmetic, order finding, factor recovery, or production solve().
"""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
import unittest

import numpy as np
from qiskit.quantum_info import Operator
from qiskit.synthesis import synth_mcx_1_clean_kg24, synth_mcx_2_clean_kg24


TOLERANCE = 1e-10
CONTROL_COUNTS = (3, 5, 7)
EVIDENCE = {
    "contract": "Exact complex operator columns for every clean-auxiliary-zero input",
    "auxiliary_one_inputs_claimed": False,
    "global_phase_fitted": False,
    "tolerance": TOLERANCE,
    "cases": [],
    "max_operator_absolute_error": 0.0,
    "max_auxiliary_nonzero_amplitude": 0.0,
    "max_dense_operator_qubits": 0,
    "max_dense_operator_bytes": 0,
    "aer_run_calls": 0,
    "real_tier09_executions": 0,
}


class CleanWorkspaceTests(unittest.TestCase):
    def _assert_clean_subspace(self, factory, controls, auxiliary_bits):
        circuit = factory(controls)
        data_qubits = controls + 1
        self.assertEqual(circuit.num_qubits, data_qubits + auxiliary_bits)
        self.assertEqual(circuit.num_clbits, 0)
        self.assertLessEqual(circuit.num_qubits, 10)

        # Qiskit uses controls q0..q(c-1), target qc, then clean auxiliaries.
        # Thus the first 2**(c+1) input columns are precisely ancilla=0.
        matrix = Operator(circuit).data
        data_dimension = 1 << data_qubits
        actual = matrix[:, :data_dimension]
        inputs = np.arange(data_dimension, dtype=np.int64)
        control_mask = (1 << controls) - 1
        all_controls_one = (inputs & control_mask) == control_mask
        outputs = inputs ^ np.where(all_controls_one, 1 << controls, 0)
        expected = np.zeros(actual.shape, dtype=np.complex128)
        expected[outputs, inputs] = 1.0

        error = float(np.max(np.abs(actual - expected)))
        leakage = float(np.max(np.abs(actual[data_dimension:, :])))
        EVIDENCE["cases"].append({
            "template": factory.__name__,
            "controls": controls,
            "clean_auxiliary_bits": auxiliary_bits,
            "operator_qubits": circuit.num_qubits,
            "input_columns_checked": data_dimension,
            "max_absolute_error": error,
            "max_auxiliary_nonzero_amplitude": leakage,
        })
        EVIDENCE["max_operator_absolute_error"] = max(
            EVIDENCE["max_operator_absolute_error"], error,
        )
        EVIDENCE["max_auxiliary_nonzero_amplitude"] = max(
            EVIDENCE["max_auxiliary_nonzero_amplitude"], leakage,
        )
        EVIDENCE["max_dense_operator_qubits"] = max(
            EVIDENCE["max_dense_operator_qubits"], circuit.num_qubits,
        )
        EVIDENCE["max_dense_operator_bytes"] = max(
            EVIDENCE["max_dense_operator_bytes"], matrix.nbytes,
        )

        # In particular, an overall phase or an input-dependent relative phase
        # is a failure, even if every computational-basis probability is right.
        np.testing.assert_allclose(actual, expected, rtol=0, atol=TOLERANCE)
        self.assertLessEqual(leakage, TOLERANCE)

    def test_one_clean_complete_template(self):
        for controls in CONTROL_COUNTS:
            with self.subTest(controls=controls):
                self._assert_clean_subspace(synth_mcx_1_clean_kg24, controls, 1)

    def test_two_clean_complete_template(self):
        for controls in CONTROL_COUNTS:
            with self.subTest(controls=controls):
                self._assert_clean_subspace(synth_mcx_2_clean_kg24, controls, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Optional safe aggregate JSON path")
    args = parser.parse_args()
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CleanWorkspaceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        **EVIDENCE,
        "elapsed_seconds": time.perf_counter() - started,
        "test_methods_run": result.testsRun,
        "test_failures": len(result.failures),
        "test_errors": len(result.errors),
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "qiskit_version": importlib.metadata.version("qiskit"),
        "numpy_version": np.__version__,
        "test_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    if args.report is not None:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"],
        "cases": len(report["cases"]),
        "elapsed_seconds": report["elapsed_seconds"],
        "max_operator_absolute_error": report["max_operator_absolute_error"],
        "max_auxiliary_nonzero_amplitude": report["max_auxiliary_nonzero_amplitude"],
        "max_dense_operator_qubits": report["max_dense_operator_qubits"],
    }, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
