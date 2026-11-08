"""Run: python -m unittest research.circuit_optimizer.equivalence_tests -v"""

import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate, Parameter
from qiskit.circuit.library import RCCXGate
from qiskit.quantum_info import Operator, Statevector

from . import gf2_synthesis as gf2
from .commutation_rules import cancel_inverses
from .qft_relabeling import (inverse_qft, absorb_input_reversal, absorb_output_reversal,
                            split_boundary_reversal, conjugate_wires)
from .mcx_benchmark import budget_candidates, verify_mcx, corrected_relative_toffoli


def exact(first, second):
    np.testing.assert_allclose(Operator(first).data, Operator(second).data, atol=1e-10, rtol=0)


def measured_probabilities(state, mapping, classical_width):
    result = np.zeros(1 << classical_width)
    for basis, probability in enumerate(state.probabilities()):
        bits = sum(((basis >> q) & 1) << c for q, c in mapping.items())
        result[bits] += probability
    return result


class GF2Tests(unittest.TestCase):
    def test_all_invertible_three_wire_maps_and_basis_amplitudes(self):
        accepted = 0
        for bits in range(512):
            matrix = np.array([(bits >> j) & 1 for j in range(9)]).reshape(3, 3)
            try:
                circuit = gf2.synthesize(matrix)
            except ValueError:
                continue
            accepted += 1
            np.testing.assert_array_equal(gf2.extract_matrix(circuit), matrix)
            expected = np.zeros((8, 8))
            for x in range(8):
                vector = np.array([(x >> j) & 1 for j in range(3)])
                output = (matrix @ vector) % 2
                expected[sum(int(output[j]) << j for j in range(3)), x] = 1
            np.testing.assert_allclose(Operator(circuit).data, expected, atol=1e-12, rtol=0)
        self.assertEqual(accepted, 168)

    def test_random_maps_global_phase_and_regression_guard(self):
        rng = np.random.default_rng(931)
        for width in range(2, 7):
            for _ in range(8):
                circuit = QuantumCircuit(width, global_phase=0.37)
                for _ in range(24):
                    c, t = rng.choice(width, 2, replace=False)
                    circuit.cx(int(c), int(t))
                candidate, _ = gf2.optimize(circuit)
                exact(circuit, candidate)
                self.assertLessEqual(candidate.size(), circuit.size())
                self.assertLessEqual(candidate.depth(), circuit.depth())
        minimal = QuantumCircuit(3)
        minimal.cx(0, 1)
        self.assertFalse(gf2.optimize(minimal)[1])

    def test_rejects_ineligible_and_singular(self):
        for gate in (RCCXGate(), Gate("cx", 3, [])):
            circuit = QuantumCircuit(3)
            circuit.append(gate, range(3))
            with self.assertRaises(ValueError):
                gf2.extract_matrix(circuit)
        for value in ([[1, 0], [0, 0]], [[1, 2], [0, 1]], [1, 0]):
            with self.assertRaises(ValueError):
                gf2.synthesize(value)


class QFTTests(unittest.TestCase):
    def test_fourier_sign_all_columns(self):
        for width in range(1, 5):
            size = 1 << width
            indices = np.arange(size)
            expected = np.exp(-2j * np.pi * np.outer(indices, indices) / size) / np.sqrt(size)
            np.testing.assert_allclose(Operator(inverse_qft(width)).data, expected,
                                       atol=1e-12, rtol=0)

    def test_input_plan_all_columns_and_complex_state(self):
        for register in ((0, 1, 2), (0, 2, 4)):
            width = max(register) + 2
            prefix = QuantumCircuit(width, global_phase=0.23)
            prefix.h(register)
            prefix.ry(0.71, width - 1)
            for j, q in enumerate(register):
                prefix.cp(0.31 * (2 ** j), q, width - 1)
            # An explicit borrowed-wire operation: all its qargs must map.
            prefix.ccx(register[0], width - 1, register[-1])
            transform = QuantumCircuit(width)
            transform.compose(inverse_qft(len(register)), register, inplace=True)
            plan = absorb_input_reversal(prefix, transform, register)
            reversal = QuantumCircuit(width)
            reversal.swap(register[0], register[-1])
            original = prefix.compose(transform)
            exact(plan.circuit, reversal.compose(original))
            np.testing.assert_allclose(Statevector.from_instruction(original).data,
                                       Statevector.from_instruction(plan.circuit).data, atol=1e-11, rtol=0)
            rng = np.random.default_rng(81)
            vector = rng.normal(size=1 << width) + 1j * rng.normal(size=1 << width)
            initial = Statevector(vector / np.linalg.norm(vector))
            np.testing.assert_allclose(initial.evolve(original).data,
                                       initial.evolve(reversal).evolve(plan.circuit).data,
                                       atol=1e-11, rtol=0)
            self.assertGreater(np.linalg.norm(initial.evolve(original).data -
                                              initial.evolve(plan.circuit).data), 0.1)

    def test_output_mapping_high_and_low_classical_bits(self):
        transform = QuantumCircuit(4)
        # Disjoint two-qubit forward-QFT cores, then their boundary reversals.
        for register in ((0, 1), (2, 3)):
            full = inverse_qft(2).inverse()
            core, _ = split_boundary_reversal(full, (0, 1), "output")
            transform.compose(core, register, inplace=True)
        transform.swap(0, 1)
        transform.swap(2, 3)
        original_map = {0: 4, 1: 5, 2: 0, 3: 1}
        core, mapping = absorb_output_reversal(transform, (2, 3), original_map)
        core, mapping = absorb_output_reversal(core, (0, 1), mapping)
        states = [Statevector.from_int(j, 16) for j in range(16)]
        vector = np.arange(1, 17) + 1j * np.arange(16)
        states.append(Statevector(vector / np.linalg.norm(vector)))
        for state in states:
            np.testing.assert_allclose(
                measured_probabilities(state.evolve(transform), original_map, 6),
                measured_probabilities(state.evolve(core), mapping, 6), atol=1e-12, rtol=0)
        self.assertGreater(np.max(np.abs(
            measured_probabilities(states[-1].evolve(transform), original_map, 6) -
            measured_probabilities(states[-1].evolve(core), original_map, 6))), 1e-3)
        # Explicit asymmetric display: high two logical Z bits=10, low X=01.
        basis = Statevector.from_int((1 << 1) | (1 << 2), 16)
        self.assertEqual(format(np.argmax(measured_probabilities(basis, original_map, 6)), "06b"), "100001")
        measured = QuantumCircuit(4, 6)
        measured.compose(core, inplace=True)
        for q, c in mapping.items():
            measured.measure(q, c)
        self.assertEqual({measured.find_bit(i.qubits[0]).index: measured.find_bit(i.clbits[0]).index
                          for i in measured.data if i.operation.name == "measure"}, mapping)

    def test_rejects_incomplete_hidden_and_nonunitary_boundaries(self):
        bad = QuantumCircuit(4)
        bad.swap(0, 3)
        bad.h(1)
        with self.assertRaises(ValueError):
            split_boundary_reversal(bad, range(4))
        opaque = QuantumCircuit(3)
        opaque.append(inverse_qft(3).to_gate(), range(3))
        with self.assertRaises(ValueError):
            split_boundary_reversal(opaque, range(3))
        measured = QuantumCircuit(2, 2)
        measured.measure(range(2), range(2))
        with self.assertRaises(ValueError):
            conjugate_wires(measured, (1, 0))


class CancellationTests(unittest.TestCase):
    def test_random_native_circuits_preserve_exact_operator(self):
        rng = np.random.default_rng(990)
        for _ in range(30):
            circuit = QuantumCircuit(4, global_phase=0.11)
            for _ in range(30):
                c, t = map(int, rng.choice(4, 2, replace=False))
                operation = int(rng.integers(7))
                if operation == 0: circuit.cx(c, t)
                elif operation == 1: circuit.h(c)
                elif operation == 2: circuit.x(c)
                elif operation == 3: circuit.z(c)
                elif operation == 4: circuit.rz(0.25 if c % 2 else -0.25, c)
                elif operation == 5: circuit.s(c)
                else: circuit.sdg(c)
            candidate, _ = cancel_inverses(circuit)
            exact(circuit, candidate)

    def test_commutable_inverse_and_phase_counterexamples(self):
        circuit = QuantumCircuit(3)
        circuit.cx(0, 1); circuit.cx(0, 2); circuit.z(0); circuit.cx(0, 1)
        candidate, removed = cancel_inverses(circuit)
        self.assertEqual(removed, 2)
        exact(circuit, candidate)
        rotations = QuantumCircuit(2)
        rotations.cx(0, 1); rotations.rz(0.31, 0); rotations.rx(0.42, 1); rotations.cx(0, 1)
        candidate, removed = cancel_inverses(rotations)
        self.assertEqual(removed, 2)
        exact(rotations, candidate)
        for sequence in ("anticommuting", "rotation", "crossed_cx"):
            bad = QuantumCircuit(2)
            if sequence == "anticommuting": bad.x(0); bad.z(0); bad.x(0)
            elif sequence == "rotation": bad.rx(np.pi, 0); bad.rx(np.pi, 0)
            else: bad.cx(0, 1); bad.cx(1, 0); bad.cx(0, 1)
            self.assertEqual(cancel_inverses(bad)[1], 0)

    def test_symbolic_opaque_measurement_reset_and_barriers_stop_motion(self):
        for name in ("opaque", "measure", "reset", "barrier", "symbol"):
            circuit = QuantumCircuit(2, 1)
            circuit.x(0)
            if name == "opaque": circuit.append(Gate("x", 1, []), [1])
            elif name == "measure": circuit.measure(1, 0)
            elif name == "reset": circuit.reset(1)
            elif name == "barrier": circuit.barrier()
            else: circuit.rz(Parameter("theta"), 1)
            circuit.x(0)
            candidate, removed = cancel_inverses(circuit)
            self.assertEqual(removed, 0)
            self.assertEqual(candidate, circuit)


class MCXTests(unittest.TestCase):
    def test_budget_contracts_and_full_amplitudes(self):
        for controls in (3, 4, 5):
            for _, kind, _, circuit in budget_candidates(controls, 2, 2):
                verify_mcx(circuit, controls, clean=kind == "clean")
        self.assertEqual([name for name, *_ in budget_candidates(4)], ["noaux_hp24"])
        self.assertFalse(any(kind == "clean" for _, kind, _, _ in budget_candidates(4, 0, 2)))

    def test_corrected_relative_phase_and_external_control(self):
        corrected = corrected_relative_toffoli()
        reference = QuantumCircuit(3)
        reference.ccx(0, 1, 2)
        exact(corrected, reference)
        self.assertGreater(np.max(np.abs(Operator(RCCXGate()).data - Operator(reference).data)), 1)
        a, b = QuantumCircuit(4), QuantumCircuit(4)
        a.append(corrected.to_gate().control(), range(4))
        b.append(reference.to_gate().control(), range(4))
        exact(a, b)


if __name__ == "__main__":
    unittest.main()
