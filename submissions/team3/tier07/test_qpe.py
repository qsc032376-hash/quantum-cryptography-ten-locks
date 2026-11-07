"""Synthetic QPE checks: exact phases, global phase, and non-basis eigenstates.

These tests never import the Tier 7 helper or load challenge circuit files.
All phases and eigenstates are constructed from public artificial constants.
The quantum cases share one Aer batch; no unknown phase is classically solved.
"""

import math
import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from submissions.team3.tier07 import qpe


def synthetic_inputs(phase, width, global_units):
    """Build U=e^(i gamma) V diag(1,e^(i delta)) V† and |psi>=V|1>."""
    dimension = 1 << width
    gamma = 2 * math.pi * global_units / dimension
    delta = 2 * math.pi * (phase - global_units) / dimension
    rotation = QuantumCircuit(1, name="artificial_rotation")
    rotation.ry(0.73, 0)
    rotation.rz(-0.41, 0)

    unitary = QuantumCircuit(1, name="artificial_unitary")
    unitary.compose(rotation.inverse(), inplace=True)
    unitary.p(delta, 0)
    unitary.compose(rotation, inplace=True)
    unitary.global_phase = gamma
    eigenstate = QuantumCircuit(1, name="artificial_eigenstate")
    eigenstate.x(0)
    eigenstate.compose(rotation, inplace=True)
    return unitary, eigenstate


def with_known_phase_snapshot(circuit, known_phase, width):
    """Keep original measurements; insert only a two-amplitude synthetic probe."""
    instrumented = circuit.copy_empty_like()
    saved = False
    for instruction in circuit.data:
        if instruction.operation.name == "measure" and not saved:
            instrumented.save_amplitudes(
                [known_phase, known_phase | (1 << width)],
                label="known_phase_support",
            )
            saved = True
        instrumented.append(instruction)
    if not saved:
        raise AssertionError("The QPE circuit must include final measurements")
    return instrumented


class SyntheticQPETests(unittest.TestCase):
    SHOTS = 32
    PHASES = (0, 1, 0x12A5, 1 << 13, (1 << 14) - 1)

    @classmethod
    def setUpClass(cls):
        circuits = []
        for phase in cls.PHASES:
            unitary, eigenstate = synthetic_inputs(phase, 14, global_units=311)
            circuit = qpe.build_qpe_circuit(unitary, eigenstate, phase_bits=14)
            circuits.append(with_known_phase_snapshot(circuit, phase, 14))

        # Correct phase, an adjacent wrong phase, and a wrong bit-reversed
        # phase. Only the first phase-check circuit may produce all zeros.
        unitary, eigenstate = synthetic_inputs(5, 4, global_units=3)
        for candidate in (5, 6, 10):
            circuits.append(qpe.build_phase_check_circuit(
                unitary, eigenstate, phase=candidate, phase_bits=4
            ))

        simulator = AerSimulator(
            method="statevector", max_memory_mb=512,
            max_parallel_threads=2, max_parallel_experiments=1,
        )
        compiled = transpile(circuits, simulator, optimization_level=0, seed_transpiler=12345)
        cls.result = simulator.run(
            compiled, shots=cls.SHOTS, seed_simulator=12345
        ).result()
        if not cls.result.success:
            raise AssertionError("Synthetic QPE Aer batch failed")

    def test_exact_phases_preserve_global_phase_and_probability_distribution(self):
        self.assertEqual(qpe.PHASE_BITS, 14)
        for index, phase in enumerate(self.PHASES):
            with self.subTest(case=index):
                counts = self.result.get_counts(index)
                expected = {format(phase, "014b"): self.SHOTS}
                self.assertTrue(counts == expected, "Artificial QPE histogram differs")
                amplitudes = np.asarray(
                    self.result.data(index)["known_phase_support"], dtype=complex
                )
                self.assertAlmostEqual(
                    float(np.vdot(amplitudes, amplitudes).real), 1.0, places=8,
                    msg="The exact artificial phase does not have unit probability",
                )

    def test_phase_check_accepts_only_the_correct_artificial_candidate(self):
        offset = len(self.PHASES)
        self.assertTrue(
            self.result.get_counts(offset) == {"0000": self.SHOTS},
            "Correct artificial phase must give all-zero phase-check output",
        )
        for index in (offset + 1, offset + 2):
            with self.subTest(case=index - offset):
                counts = self.result.get_counts(index)
                self.assertEqual(sum(counts.values()), self.SHOTS)
                self.assertEqual(counts.get("0000", 0), 0)

    def test_inverse_qft_matches_small_analytic_inverse_dft(self):
        for width in (3, 4):
            with self.subTest(width=width):
                dimension = 1 << width
                indices = np.arange(dimension)
                expected = np.exp(-2j * np.pi * np.outer(indices, indices) / dimension)
                expected /= math.sqrt(dimension)
                actual = Operator(qpe.build_inverse_qft(width)).data
                self.assertTrue(
                    np.allclose(actual, expected, rtol=1e-10, atol=1e-10),
                    "Inverse QFT differs from the analytic little-endian inverse DFT",
                )

    def test_controlled_integer_powers_query_count_and_measurement_layout(self):
        width = 4
        unitary, eigenstate = synthetic_inputs(5, width, global_units=3)
        circuit = qpe.build_qpe_circuit(unitary, eigenstate, phase_bits=width)
        self.assertEqual((circuit.num_qubits, circuit.num_clbits), (5, 4))
        self.assertEqual(len(circuit.cregs), 1)
        stats = qpe.count_controlled_powers(circuit)
        self.assertEqual(stats["controlled_power_blocks"], width)
        self.assertEqual(stats["equivalent_base_U_applications"], (1 << width) - 1)
        self.assertEqual(stats["exponents"], [1, 2, 4, 8])

        measured = [
            (circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index)
            for item in circuit.data if item.operation.name == "measure"
        ]
        self.assertEqual(measured, [(index, index) for index in range(width)])
        controlled = [
            item for item in circuit.data
            if item.operation.num_qubits == 2
            and circuit.qubits[width] in item.qubits
        ]
        self.assertEqual(len(controlled), width)
        full_unitary = Operator(unitary).data
        for control, item in enumerate(controlled):
            self.assertEqual(
                tuple(circuit.find_bit(bit).index for bit in item.qubits), (control, width)
            )
            expected = np.eye(4, dtype=complex)
            # Qiskit places the first qarg (the control) at the low bit.
            expected[np.ix_([1, 3], [1, 3])] = np.linalg.matrix_power(full_unitary, 1 << control)
            actual = Operator(item.operation).data
            self.assertTrue(
                np.allclose(actual, expected, rtol=1e-10, atol=1e-10),
                "A controlled integer power dropped phase or used the wrong exponent",
            )


if __name__ == "__main__":
    unittest.main()
