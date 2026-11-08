"""Exact basis action and coherent reduced-instance checks for Tier 9 synthesis."""
import unittest
from unittest.mock import patch

import numpy as np
from qiskit.circuit.library import CXGate, MCXGate, CCXGate
from qiskit.quantum_info import Statevector

from submissions.team3.tier09 import modular, shared_controls, solution


class MultiplierTests(unittest.TestCase):
    def test_public_blocks_all_basis_states_and_phases(self):
        # Every allowed primitive is an exact +1 permutation in the computational
        # basis. Track all 256 columns simultaneously, including inactive controls.
        for j in range(14):
            multiplier = pow(2, 1 << j, 77)
            circuit = shared_controls.build_controlled_multiplier(multiplier, 77, 7)
            self.assertEqual(circuit.num_qubits, 8)
            self.assertEqual(float(circuit.global_phase), 0.0)
            columns = np.arange(256)
            for item in circuit.data:
                gate = item.operation
                self.assertIsInstance(gate, (CXGate, CCXGate, MCXGate))
                wires = [circuit.find_bit(q).index for q in item.qubits]
                self.assertEqual(gate.ctrl_state, (1 << (len(wires) - 1)) - 1)
                mask = sum(1 << w for w in wires[:-1])
                columns ^= ((columns & mask) == mask).astype(int) << wires[-1]
            expected = []
            for basis in range(256):
                control, x = basis & 1, basis >> 1
                y = multiplier * x % 77 if control and x < 77 else x
                expected.append(control | (y << 1))
            np.testing.assert_array_equal(columns, expected)

    def test_coherent_reduced_order_finding(self):
        for base in (2, 4):
            params = dict(modulus=15, base=base, phase_bits=4, work_bits=4)
            with patch.object(solution, "build_controlled_multiplier", modular.build_controlled_multiplier):
                baseline = solution.build_circuit(**params)
            candidate = solution.build_circuit(**params)
            for circ in (baseline, candidate):
                mapping = [(circ.find_bit(i.qubits[0]).index, circ.find_bit(i.clbits[0]).index)
                           for i in circ.data if i.operation.name == "measure"]
                self.assertEqual(mapping, [(j, j) for j in range(4)])
            states = [Statevector.from_instruction(c.remove_final_measurements(inplace=False))
                      for c in (baseline, candidate)]
            np.testing.assert_allclose(states[0].data, states[1].data, atol=1e-12, rtol=0)
            np.testing.assert_allclose(states[0].probabilities(range(4)),
                                       states[1].probabilities(range(4)), atol=1e-12, rtol=0)
