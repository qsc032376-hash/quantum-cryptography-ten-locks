"""Small synthetic phase-sensitive regression tests for Tier 10 variants."""
import sys
from pathlib import Path
import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.tier10_full_candidates import baseline_circuit
from submissions.team3.tier09.modular import build_controlled_multiplier
from submissions.team3.tier10.shared_control import shared_multiplier, shared_circuit
from submissions.team3.tier10.circuit import build_qpe_circuit
from submissions.team3.tier10.readout import measurement_from_counts
from submissions.team3.dh_classical import decrypt_from_counts
from common import keystream, xor_bytes

class FullOptimizationTests(unittest.TestCase):
    def test_controlled_multiplier_all_columns(self):
        for modulus, width, ds in ((5,3,(1,2,3,4)), (7,3,(1,2,3,4,5,6)), (11,4,(3,6,7,8,9))):
            for d in ds:
                if modulus == 11:
                    trial = shared_multiplier(d,modulus,width)
                    self.assertTrue(any(trial.find_bit(bit).index == width + 1 for item in trial.data for bit in item.qubits))
                old = Operator(build_controlled_multiplier(d,modulus,width)).data
                new = Operator(shared_multiplier(d,modulus,width)).data
                dim = old.shape[0]
                # Last wire is the most significant auxiliary; compare each
                # column, including padding, all relative phases and q=0.
                np.testing.assert_allclose(new[:dim,:dim], old, atol=1e-12,rtol=0)
                np.testing.assert_allclose(new[dim:,:dim], 0, atol=1e-12,rtol=0)

    def test_complete_prepared_state_and_distribution(self):
        for t in (1,2,3):
            a = Statevector.from_instruction(baseline_circuit(5,2,4,t,3).remove_final_measurements(inplace=False))
            b = Statevector.from_instruction(build_qpe_circuit(5,2,4,t,3).remove_final_measurements(inplace=False))
            c = Statevector.from_instruction(shared_circuit(5,2,4,t,3).remove_final_measurements(inplace=False))
            np.testing.assert_allclose(a.data,b.data,atol=1e-12,rtol=0)
            np.testing.assert_allclose(c.data[:len(a.data)],a.data,atol=1e-12,rtol=0)
            np.testing.assert_allclose(c.data[len(a.data):],0,atol=1e-12,rtol=0)
            np.testing.assert_allclose(a.probabilities(range(2*t)),b.probabilities(range(2*t)),atol=1e-12,rtol=0)
            np.testing.assert_allclose(a.probabilities(range(2*t)),c.probabilities(range(2*t)),atol=1e-12,rtol=0)
            for circuit in (build_qpe_circuit(5,2,4,t,3),shared_circuit(5,2,4,t,3)):
                measurements=[x for x in circuit.data if x.operation.name=='measure']
                self.assertEqual([(circuit.find_bit(x.qubits[0]).index,circuit.find_bit(x.clbits[0]).index) for x in measurements],[(j,j) for j in range(2*t)])

    def test_shared_complete_state_with_active_window(self):
        # This multiplier has at least one three-target shared window.
        multiplier = shared_multiplier(3,11,4)
        self.assertTrue(any(multiplier.find_bit(q).index == 5
                            for item in multiplier.data for q in item.qubits))
        old = Statevector.from_instruction(baseline_circuit(11,3,9,2,4).remove_final_measurements(inplace=False))
        new = Statevector.from_instruction(shared_circuit(11,3,9,2,4).remove_final_measurements(inplace=False))
        np.testing.assert_allclose(new.data[:len(old.data)], old.data, atol=1e-12, rtol=0)
        np.testing.assert_allclose(new.data[len(old.data):], 0, atol=1e-12, rtol=0)
        np.testing.assert_allclose(new.probabilities(range(4)), old.probabilities(range(4)), atol=1e-12, rtol=0)

    def test_qft_sign(self):
        from math import pi
        from submissions.team3.tier07.qpe import build_inverse_qft
        for width in (1,2,3):
            n = 1 << width
            expected = np.array([[np.exp(-2j*pi*x*y/n)/np.sqrt(n) for x in range(n)] for y in range(n)])
            np.testing.assert_allclose(Operator(build_inverse_qft(width)).data, expected, atol=1e-12, rtol=0)

    def test_classical_synthetic_interface(self):
        key=f'{26:06b}{13:06b}'
        self.assertEqual(measurement_from_counts(key,5),(3,1))
        params={'p':11,'g':3,'order':5,'A':9,'B':4,'key_width_bits':4}
        text='QC-10: synthetic test'; payload=text.encode()
        cipher=xor_bytes(payload,keystream(format(pow(4,2,11),'04b'),len(payload))).hex()
        self.assertEqual(decrypt_from_counts(key,params,cipher),text)

if __name__ == '__main__': unittest.main(verbosity=2)
