"""Isolated synthetic Tier 10 experiment; imports immutable baseline files via git.

Run from the repository root: python -B experiments/tier10_optimization_prototype.py
No challenge ciphertext or submitted implementation is modified or executed.
"""
from contextlib import contextmanager
from math import pi
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator, Statevector, partial_trace

ROOT = Path(__file__).resolve().parents[1]
REF = "0cd8adc025e89fa190836e9295f6b5ffa482e17a"
FILES = ("classical_keystream.py", "rsa_classical.py", "dh_classical.py",
         "tier07/qpe.py", "tier08/modular.py", "tier09/modular.py",
         "tier10/circuit.py", "tier10/readout.py")
sys.path.insert(0, str(ROOT))


@contextmanager
def baseline_modules():
    # Baseline is a Git object, not a mutable checkout or a copied submission.
    with tempfile.TemporaryDirectory() as tmp:
        parent = Path(tmp)
        team = parent / "reference_team"
        for file in FILES:
            path = team / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(
                ["git", "show", f"{REF}:submissions/team3/{file}"], cwd=ROOT))
        sys.path.insert(0, tmp)
        try:
            from reference_team.tier10 import circuit, readout
            from reference_team import dh_classical
            yield circuit, readout, dh_classical
        finally:
            sys.path.remove(tmp)


def inverse_qft(width, with_swaps):
    qc = QuantumCircuit(width)
    if with_swaps:
        for bit in range(width // 2):
            qc.swap(bit, width - 1 - bit)
    for target in range(width):
        for earlier in range(target):
            qc.cp(-pi / (1 << (target - earlier)), target, earlier)
        qc.h(target)
    return qc


def sampling_circuit(mapping, t, work_bits, rewired, prepare_plus=True, basis=0, bad=False):
    """For basis tests apply S to optimized input, as required by D S U = D U' S."""
    qc = QuantumCircuit(2 * t + work_bits)
    if prepare_plus:
        qc.h(range(2 * t))
    else:
        for j in range(2 * t):
            if basis >> j & 1:
                physical = (j // t) * t + (t - 1 - (j % t) if rewired else j % t)
                qc.x(physical)
    qc.x(2 * t)  # synthetic work = 1
    wires = list(range(2 * t + work_bits))
    if rewired:
        wires = [*(range(t - 1, -1, -1)), *(range(2*t - 1, t - 1, -1)),
                 *(range(2*t, 2*t + work_bits))]
    qc.compose(mapping, qubits=wires, inplace=True)
    for offset in (0, t):
        qc.compose(inverse_qft(t, not (rewired or bad)),
                   qubits=range(offset, offset + t), inplace=True)
    return qc


def shared_predicate(optimized, include_unused=True):
    # controls 0,1,2; targets 3,4,5; clean auxiliary 6.
    qc = QuantumCircuit(7 if optimized or include_unused else 6)
    controls, targets, ancilla = [0, 1, 2], [3, 4, 5], 6
    if optimized:
        qc.mcx(controls, ancilla)
        for target in targets:
            qc.cx(ancilla, target)
        qc.mcx(controls, ancilla)
    else:
        for target in targets:
            qc.mcx(controls, target)
    return qc


def metrics(qc):
    result = transpile(qc, basis_gates=["rz", "sx", "x", "cx"],
                       coupling_map=None, optimization_level=1, seed_transpiler=12345)
    counts = result.count_ops()
    active = len({q for item in result.data for q in item.qubits})
    return {"cx": int(counts.get("cx", 0)), "total": int(result.size()),
            "depth": int(result.depth()), "active": active}


class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = baseline_modules()
        cls.circuit, cls.readout, cls.dh = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_inverse_qft_sign_and_full_matrix(self):
        for t in (1, 2, 3):
            n = 1 << t
            target = np.array([[np.exp(-2j*pi*x*y/n)/np.sqrt(n)
                                for x in range(n)] for y in range(n)])
            np.testing.assert_allclose(Operator(inverse_qft(t, True)).data, target, atol=1e-12, rtol=0)
            from reference_team.tier07.qpe import build_inverse_qft
            np.testing.assert_allclose(Operator(build_inverse_qft(t)).data, target, atol=1e-12, rtol=0)

    def test_mapping_every_basis_and_superpositions(self):
        # Public toy group mod 5, width 3; A=4 distinct from g=2.
        for t in (1, 2, 3):
            mapping = self.circuit.build_exponent_mapping(5, 2, 4, t, 3)
            for basis in range(1 << (2*t)):
                a = Statevector.from_instruction(sampling_circuit(mapping, t, 3, False, False, basis))
                b = Statevector.from_instruction(sampling_circuit(mapping, t, 3, True, False, basis))
                np.testing.assert_allclose(a.data, b.data, atol=1e-12, rtol=0)
                np.testing.assert_allclose(a.probabilities(range(2*t)), b.probabilities(range(2*t)), atol=1e-12, rtol=0)
            a = Statevector.from_instruction(sampling_circuit(mapping, t, 3, False))
            b = Statevector.from_instruction(sampling_circuit(mapping, t, 3, True))
            np.testing.assert_allclose(a.data, b.data, atol=1e-12, rtol=0)
            np.testing.assert_allclose(a.probabilities(range(2*t)), b.probabilities(range(2*t)), atol=1e-12, rtol=0)
        # An asymmetric complex superposition, with the optimized input relabeled S.
        t = 2
        mapping = self.circuit.build_exponent_mapping(5, 2, 4, t, 3)
        amplitudes = np.arange(1, 17) + 1j * np.arange(16, 0, -1)
        amplitudes = amplitudes / np.linalg.norm(amplitudes)
        output = []
        for rewired in (False, True):
            qc = QuantumCircuit(7)
            count_wires = [1, 0, 3, 2] if rewired else [0, 1, 2, 3]
            qc.initialize(amplitudes, count_wires)
            qc.x(4)
            qc.compose(mapping, count_wires + [4, 5, 6], inplace=True)
            for offset in (0, 2):
                qc.compose(inverse_qft(2, not rewired), [offset, offset+1], inplace=True)
            output.append(Statevector.from_instruction(qc))
        np.testing.assert_allclose(output[0].data, output[1].data, atol=1e-12, rtol=0)
        mapping = self.circuit.build_exponent_mapping(5, 2, 4, 2, 3)
        a = Statevector.from_instruction(sampling_circuit(mapping, 2, 3, False))
        wrong = Statevector.from_instruction(sampling_circuit(mapping, 2, 3, False, bad=True))
        self.assertGreater(np.max(np.abs(a.data-wrong.data)), 1e-3)
        self.assertGreater(np.max(np.abs(a.probabilities(range(4))-wrong.probabilities(range(4)))), 1e-3)

    def test_layout_and_decrypt_from_counts(self):
        # Produce an asymmetric, exactly peaked two-register Fourier state.
        # It is an interface test, not a full 6+6+work Tier 10 execution.
        t, x, z = 6, 13, 26
        qc = QuantumCircuit(2*t, 2*t)
        for offset, value in ((0, x), (t, z)):
            for j in range(t):
                q = offset + t-1-j
                qc.h(q); qc.p(2*pi*value*(1 << j)/(1 << t), q)
            qc.compose(inverse_qft(t, False), range(offset, offset+t), inplace=True)
        state = Statevector.from_instruction(qc.remove_final_measurements(inplace=False))
        key = f'{z:06b}{x:06b}'
        self.assertAlmostEqual(state.probabilities_dict()[key], 1.0, places=12)
        qc.measure(range(2*t), range(2*t))
        for j, item in enumerate(qc.data[-2*t:]):
            self.assertEqual(qc.find_bit(item.qubits[0]).index, j)
            self.assertEqual(qc.find_bit(item.clbits[0]).index, j)
        self.assertEqual(self.readout.measurement_from_counts(key, 5), (3, 1))
        self.assertEqual(self.dh.measurement_from_counts(key, 5), (3, 1))
        from common import keystream, xor_bytes
        params = {"p": 11, "g": 3, "order": 5, "A": 9, "B": 4, "key_width_bits": 4}
        text = "QC-10: synthetic prototype"
        secret = pow(params['B'], 2, params['p'])
        payload = text.encode()
        encrypted = xor_bytes(payload, keystream(format(secret, '04b'), len(payload))).hex()
        self.assertEqual(self.dh.decrypt_from_counts(key, params, encrypted), text)

    def test_shared_control_exact_clean_subspace(self):
        orig, opt = Operator(shared_predicate(False)).data, Operator(shared_predicate(True)).data
        np.testing.assert_allclose(orig[:, :64], opt[:, :64], atol=1e-12, rtol=0)
        self.assertGreater(np.max(np.abs(orig[:, 64:] - opt[:, 64:])), 0.5)
        # Entangle an external reference (wire 7) with controls and targets.
        prep = QuantumCircuit(8)
        prep.h(7); prep.cx(7, 0); prep.h(1); prep.h(2); prep.cx(7, 3)
        outputs = []
        for optimized in (False, True):
            qc = prep.copy(); qc.compose(shared_predicate(optimized), range(7), inplace=True)
            outputs.append(Statevector.from_instruction(qc))
        np.testing.assert_allclose(outputs[0].data, outputs[1].data, atol=1e-12, rtol=0)
        self.assertAlmostEqual(partial_trace(outputs[1], [0,1,2,3,4,5,7]).data[0,0].real, 1.0)

    def test_print_prototype_metrics(self):
        mapping = self.circuit.build_exponent_mapping(5, 2, 4, 2, 3)
        print('\nQiskit', qiskit.__version__)
        for name, qc in (
            ('toy QFT full', sampling_circuit(mapping, 2, 3, False)),
            ('toy QFT rewired', sampling_circuit(mapping, 2, 3, True)),
            ('predicate original', shared_predicate(False, include_unused=False)),
            ('predicate shared', shared_predicate(True))):
            print(name, metrics(qc))


if __name__ == '__main__':
    unittest.main(verbosity=2)
