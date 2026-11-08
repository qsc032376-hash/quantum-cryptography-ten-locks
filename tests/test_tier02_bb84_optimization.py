"""Synthetic BB84 correctness tests; never access the official hidden link data."""
import json
import math
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator

from submissions.team3.tier02 import solution

SHOTS = 4096
TOL = 0.05
observations = {}


def prepare(bit, basis):
    """Public synthetic sender: bit first, then optional X-basis rotation."""
    qc = QuantumCircuit(1)
    if bit:
        qc.x(0)
    if basis:
        qc.h(0)
    return qc


def experiment(bit, alice_basis, bob_basis, eve_basis=None):
    qc = QuantumCircuit(1, 2)
    qc.compose(prepare(bit, alice_basis), inplace=True)
    if eve_basis is not None:
        if eve_basis:
            qc.h(0)
        qc.measure(0, 1)
        if eve_basis:
            qc.h(0)  # measured eigenstate resent in Eve's basis
    qc.compose(solution.build_circuit(bob_basis), qubits=[0], clbits=[0], inplace=True)
    return qc


def error_rate(counts, bit):
    return sum(n for bits, n in counts.items() if int(bits[-1]) != bit) / SHOTS


class BB84Tests(unittest.TestCase):
    def test_four_public_sender_states(self):
        expected = {(0, 0): [1, 0], (1, 0): [0, 1],
                    (0, 1): np.array([1, 1])/math.sqrt(2),
                    (1, 1): np.array([1, -1])/math.sqrt(2)}
        for pair, state in expected.items():
            np.testing.assert_allclose(Statevector.from_instruction(prepare(*pair)).data,
                                       state, atol=1e-12, rtol=0)

    def test_bob_measurement_projectors_and_wire_order(self):
        H = np.array([[1, 1], [1, -1]]) / math.sqrt(2)
        for basis in (0, 1):
            circ = solution.build_circuit(basis)
            self.assertEqual(circ.data[-1].operation.name, "measure")
            self.assertEqual(circ.find_bit(circ.data[-1].clbits[0]).index, 0)
            self.assertEqual(circ.find_bit(circ.data[-1].qubits[0]).index, 0)
            U = Operator(circ.remove_final_measurements(inplace=False)).data
            for b in (0, 1):
                z = np.eye(2)[:, b]
                state = (H if basis else np.eye(2)) @ z
                np.testing.assert_allclose(U.conj().T @ np.outer(z,z) @ U,
                                           np.outer(state,state), atol=1e-12, rtol=0)

    def test_real_aer_same_and_different_basis(self):
        inputs = [(bit,a,b) for bit in range(2) for a in range(2) for b in range(2)]
        for seed in (207, 208):
            result = AerSimulator().run([experiment(*x) for x in inputs], shots=SHOTS,
                                        seed_simulator=seed).result()
            self.assertTrue(result.success)
            cross = []
            for i,(bit,a,b) in enumerate(inputs):
                rate = error_rate(result.get_counts(i),bit)
                if a == b:
                    self.assertEqual(rate, 0)
                else:
                    cross.append(rate)
                    self.assertLessEqual(abs(rate - 0.5), TOL)
            observations[f"mismatched_basis_{seed}"] = cross

    def test_intercept_resend_disturbs_matching_checks(self):
        inputs = [(bit,b,e) for bit in range(2) for b in range(2) for e in range(2)]
        circuits = [experiment(bit,b,b,e) for bit,b,e in inputs]
        result = AerSimulator().run(circuits, shots=SHOTS, seed_simulator=209).result()
        self.assertTrue(result.success)
        rates = [error_rate(result.get_counts(i),bit) for i,(bit,b,e) in enumerate(inputs)]
        for rate,(_,b,e) in zip(rates,inputs):
            if b == e:
                self.assertEqual(rate,0)
            else:
                self.assertLessEqual(abs(rate-0.5),TOL)
        qber = sum(rates)/len(rates)
        self.assertLessEqual(abs(qber-.25),TOL/2)
        observations["synthetic_intercept_qber"] = qber
        errors = round(qber*len(rates)*SHOTS)
        reports = {name:dict(check_errors=value, check_samples=len(rates)*SHOTS)
                   for name,value in [("clean",0),("intercepted",errors)]}
        self.assertEqual(solution.choose_clean_link(reports), "clean")

    def test_all_basis_draws_precede_any_channel_measurement(self):
        # Stop before any measurement; exercise only the basis-choice boundary.
        class BlindSelectionObserved(Exception):
            pass

        for seed in (300, 301):
            draws = []
            expected_rng = random.Random(seed)
            expected = [expected_rng.getrandbits(1) for _ in range(24)]

            class TracedRandom(random.Random):
                def getrandbits(self, k):
                    value = super().getrandbits(k)
                    draws.append(value)
                    return value

            class PublicChannel:
                log = []
                n_qubits = 12

                def __init__(channel, name):
                    channel.name = name

                def receive_all(channel, circuits):
                    self.assertEqual(draws, expected)
                    observed = [int(c.data[0].operation.name == "h") for c in circuits]
                    self.assertEqual(observed, expected[:12])
                    raise BlindSelectionObserved

                def finish(channel):
                    self.fail("Disclosure preceded blind basis selection")

            with (patch.object(solution.helper, "Channel", PublicChannel),
                  patch.object(solution, "random", SimpleNamespace(Random=TracedRandom)),
                  patch.object(solution, "BASIS_SEED", seed),
                  self.assertRaises(BlindSelectionObserved)):
                solution.recover_key_with_diagnostics()

    def test_sift_checks_only_matches_and_keeps_original_indices(self):
        bits, stats = solution.analyze_link([0,0,1,0,1,0],[1,0,0,1,1,1],
                {"alice_bases":[0,1,1,0,0,0],"check_bits":{"0":1,"1":1,"3":0}})
        self.assertEqual(bits,{2:0,5:1})
        self.assertEqual((stats["check_samples"],stats["check_errors"],stats["qber"]),(2,1,.5))
        with self.assertRaisesRegex(RuntimeError,"tied"):
            solution.choose_clean_link({"a":dict(check_samples=2,check_errors=1),
                                        "b":dict(check_samples=4,check_errors=2)})


if __name__ == "__main__":
    import sys
    # Run with python -m unittest discover from the repository root, or
    # python -m tests.test_tier02_bb84_optimization to print synthetic data.
    run = unittest.main(exit=False)
    print(json.dumps(observations, sort_keys=True))
    sys.exit(not run.result.wasSuccessful())
