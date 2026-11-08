"""Synthetic, secret-free checks for Tier 7 inverse-QFT wire relabeling."""

from math import pi
from pathlib import Path
import sys
import unittest

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "submissions" / "team3"))
from tier07 import qpe  # noqa: E402


def original_qpe(unitary, eigenstate, width):
    circuit = qpe._build_phase_register(unitary, eigenstate, width, "original")
    circuit.append(qpe.build_inverse_qft(width).to_gate(), range(width))
    circuit.measure(range(width), range(width))
    return circuit


class QftRelabelingTests(unittest.TestCase):
    def test_all_small_inverse_qft_basis_states(self):
        for width in range(1, 5):
            full = qpe.build_inverse_qft(width)
            core = qpe.build_inverse_qft(width, reverse_input=False)
            reversal = QuantumCircuit(width)
            for bit in range(width // 2):
                reversal.swap(bit, width - 1 - bit)
            np.testing.assert_allclose(
                Operator(full).data, Operator(core.compose(reversal, front=True)).data,
                atol=1e-12,
            )
            for value in range(1 << width):
                basis = Statevector.from_int(value, 1 << width)
                expected = basis.evolve(full)
                actual = basis.evolve(reversal).evolve(core)
                np.testing.assert_allclose(expected.data, actual.data, atol=1e-12)

    def test_full_qpe_state_including_target_and_relative_phase(self):
        for width in (2, 3, 4):
            for phase in (0, 1, (1 << width) - 1):
                unitary = QuantumCircuit(1)
                unitary.p(2 * pi * phase / (1 << width), 0)
                unitary.global_phase = pi / 7
                eigenstate = QuantumCircuit(1)
                eigenstate.x(0)
                original = original_qpe(unitary, eigenstate, width)
                candidate = qpe.build_qpe_circuit(unitary, eigenstate, width)
                expected = Statevector.from_instruction(original.remove_final_measurements(inplace=False))
                actual = Statevector.from_instruction(candidate.remove_final_measurements(inplace=False))
                np.testing.assert_allclose(expected.data, actual.data, atol=1e-11)
                self.assertEqual(
                    [(original.find_bit(item.qubits[0]).index, original.find_bit(item.clbits[0]).index)
                     for item in original.data if item.operation.name == "measure"],
                    [(candidate.find_bit(item.qubits[0]).index, candidate.find_bit(item.clbits[0]).index)
                     for item in candidate.data if item.operation.name == "measure"],
                )

    def test_nondiagonal_unitary_and_superposed_target(self):
        for width in (2, 3):
            unitary = QuantumCircuit(1)
            unitary.h(0)
            unitary.p(2 * pi / 7, 0)
            unitary.h(0)
            unitary.global_phase = pi / 9
            preparation = QuantumCircuit(1)
            preparation.h(0)
            original = original_qpe(unitary, preparation, width)
            candidate = qpe.build_qpe_circuit(unitary, preparation, width)
            np.testing.assert_allclose(
                Statevector.from_instruction(original.remove_final_measurements(inplace=False)).data,
                Statevector.from_instruction(candidate.remove_final_measurements(inplace=False)).data,
                atol=1e-11,
            )

    def test_synthetic_exact_phase_counts_have_canonical_endianness(self):
        width, phase = 4, 3
        unitary = QuantumCircuit(1)
        unitary.p(2 * pi * phase / (1 << width), 0)
        eigenstate = QuantumCircuit(1)
        eigenstate.x(0)
        simulator = AerSimulator(method="statevector")
        for circuit in (original_qpe(unitary, eigenstate, width),
                        qpe.build_qpe_circuit(unitary, eigenstate, width)):
            compiled = transpile(circuit, basis_gates=["rz", "sx", "x", "cx"],
                                 optimization_level=1, seed_transpiler=12345)
            counts = simulator.run(compiled, shots=32, seed_simulator=707).result().get_counts()
            self.assertEqual(counts, {format(phase, "04b"): 32})


if __name__ == "__main__":
    unittest.main()
