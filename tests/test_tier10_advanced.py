"""Public modular specifications only; no exponent, samples, key, or plaintext."""
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate, CXGate, MCXGate
from qiskit.quantum_info import Operator, Statevector

from common import load_locked
from submissions.team3.tier07.qpe import build_inverse_qft
from submissions.team3.tier10.circuit import build_exponent_mapping, build_qpe_circuit
from submissions.team3.tier10.shared_control import fanout_multiplier
from submissions.team3.tier10.synthesis import _guard, _short_predicates


def specification(d, p, width):
    col = np.arange(1 << (width + 1))
    x = col >> 1
    return (np.where((col & 1 == 1) & (x < p), d*x % p, x) << 1) | (col & 1)


class SynthesisTests(unittest.TestCase):
    def test_guard_is_minimum_size(self):
        for available in range(32):
            for row in range(available + 1):
                mask = _guard(available, row)
                self.assertEqual(mask & available, mask)
                self.assertGreaterEqual(mask, row)
                self.assertEqual(mask.bit_count(), min(m.bit_count() for m in range(row, available+1)
                                                       if m & available == m))

    def test_forward_and_reverse_work_permutations(self):
        rng = np.random.default_rng(34)
        for size in (4, 8, 16):
            for _ in range(10):
                table = rng.permutation(size)
                for reverse in (False, True):
                    for clear in (False, True):
                        ops = _short_predicates(list(map(int, np.argsort(table) if reverse else table)), clear)
                        values = np.arange(size)
                        for m, t in (reversed(ops) if reverse else ops):
                            values ^= ((values & m) == m).astype(int) << t
                        np.testing.assert_array_equal(values, table)

    def test_small_blocks_all_complex_columns(self):
        for p, width in ((5,3), (11,4)):
            for d in range(1,p):
                compiled = fanout_multiplier(d,p,width)
                self.assertEqual(compiled.num_qubits,1+width)
                # Column i has its +1 at row spec[i].
                expected = np.eye(1 << (width+1))[:,specification(d,p,width)]
                np.testing.assert_allclose(Operator(compiled).data,expected,rtol=0,atol=1e-12)

    def test_every_official_block_all_branches(self):
        public = load_locked(10)["public_parameters"]
        for base in (public["g"], public["A"]):
            for j in range(6):
                d = pow(base,1<<j,public["p"])
                circ = fanout_multiplier(d,public["p"],7)
                self.assertEqual((circ.num_qubits,float(circ.global_phase)), (8,0.0))
                basis = np.arange(256)
                for item in circ.data:
                    self.assertIsInstance(item.operation,(CXGate,CCXGate,MCXGate))
                    wires = [circ.find_bit(q).index for q in item.qubits]
                    self.assertEqual(item.operation.ctrl_state, (1 << (len(wires)-1))-1)
                    mask = sum(1 << wire for wire in wires[:-1])
                    basis ^= ((basis & mask)==mask).astype(int) << wires[-1]
                np.testing.assert_array_equal(basis,specification(d,public["p"],7))

    def test_two_register_complex_state_and_readout(self):
        p,g,A,t,w = 11,2,7,3,4
        reference = QuantumCircuit(2*t+w)
        reference.x(2*t)
        reference.h(range(2*t))
        reference.compose(build_exponent_mapping(p,g,A,t,w), inplace=True)
        for start in (0,t):
            reference.append(build_inverse_qft(t).to_gate(),range(start,start+t))
        candidate = build_qpe_circuit(p,g,A,t,w)
        measurement = [(candidate.find_bit(i.qubits[0]).index,candidate.find_bit(i.clbits[0]).index)
                       for i in candidate.data if i.operation.name=="measure"]
        self.assertEqual(measurement,[(j,j) for j in range(2*t)])
        states = [Statevector.from_instruction(c) for c in
                  (reference,candidate.remove_final_measurements(inplace=False))]
        np.testing.assert_allclose(states[0].data,states[1].data,rtol=0,atol=1e-12)
        np.testing.assert_allclose(states[0].probabilities(range(2*t)),states[1].probabilities(range(2*t)),
                                   rtol=0,atol=1e-12)
