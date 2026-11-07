"""Synthetic two-register Fourier sampling tests, without challenge data.

Every exponent used here is chosen in advance for an artificial instance.
The finite-grid example uses A=81, not the challenge's public A. No helper,
locked file, hidden exponent, or ciphertext is loaded by this test module.
"""

from collections import Counter
from math import gcd, sqrt
import unittest

import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Operator
from qiskit_aer import AerSimulator

from submissions.team3.tier10 import circuit as quantum_circuit


SCORING_BASIS = ["rz", "sx", "x", "cx"]


def artificial_mapping_matrix(p, g, A, register_bits, work_bits, *, inverse=False):
    dimension = 1 << (2 * register_bits + work_bits)
    mask = (1 << register_bits) - 1
    expected = np.zeros((dimension, dimension), dtype=complex)
    for basis in range(dimension):
        x = basis & mask
        z = (basis >> register_bits) & mask
        work = basis >> (2 * register_bits)
        multiplier = pow(g, x, p) * pow(A, z, p) % p
        if inverse:
            multiplier = pow(multiplier, -1, p)
        output = work * multiplier % p if work < p else work
        mapped = x | (z << register_bits) | (output << (2 * register_bits))
        expected[mapped, basis] = 1
    return expected


class TwoRegisterCircuitTests(unittest.TestCase):
    sampling_summary = []

    def test_complete_small_mapping_preserves_controls_padding_and_exact_phase(self):
        mapping = quantum_circuit.build_exponent_mapping(7, 2, 4, register_bits=2, work_bits=3)
        self.assertEqual((mapping.num_qubits, mapping.num_clbits), (7, 0))
        expected = artificial_mapping_matrix(7, 2, 4, 2, 3)
        actual = Operator(mapping).data
        self.assertTrue(
            np.allclose(actual, expected, rtol=1e-10, atol=1e-10),
            "The complete artificial mapping changed a control, padding value, or phase",
        )
        self.assertTrue(np.allclose(actual.conj().T @ actual, np.eye(128), atol=1e-10))
        expected_inverse = artificial_mapping_matrix(7, 2, 4, 2, 3, inverse=True)
        self.assertTrue(np.allclose(Operator(mapping.inverse()).data, expected_inverse, atol=1e-10))

        simulator = AerSimulator(method="statevector", max_parallel_threads=2)
        # This is a reusable subroutine on ARBITRARY inputs. The default
        # qubits_initially_zero=True lets HLS borrow not-yet-used controls as
        # clean ancillas and therefore does not promise full-unitary equality.
        native = transpile(
            mapping, simulator, optimization_level=0, seed_transpiler=12345,
            qubits_initially_zero=False,
        )
        scored = transpile(
            mapping, basis_gates=SCORING_BASIS, optimization_level=1, seed_transpiler=12345,
            qubits_initially_zero=False,
        )
        self.assertTrue(np.allclose(Operator.from_circuit(native).data, expected, atol=1e-9))
        self.assertTrue(np.allclose(Operator.from_circuit(scored).data, expected, atol=1e-9))
        self.assertEqual(native.num_qubits, 7)
        self.assertEqual(scored.num_qubits, 7)

        # The complete sampling circuit explicitly prepares all its inputs,
        # so the normal scoring compiler's all-zero initial-state assumption
        # is valid. Compare that prepared-state output without another Aer run.
        full = quantum_circuit.build_qpe_circuit(7, 2, 4, register_bits=2, work_bits=3)
        full = full.remove_final_measurements(inplace=False)
        full_scored = transpile(
            full, basis_gates=SCORING_BASIS, optimization_level=1, seed_transpiler=12345,
            qubits_initially_zero=True,
        )
        self.assertTrue(np.allclose(
            Operator.from_circuit(full_scored).data[:, 0], Operator(full).data[:, 0], atol=1e-9
        ))

    def test_default_layout_has_two_complete_inverse_qfts_and_direct_measurement(self):
        # Known artificial exponent 4 gives A=81. This is not the challenge instance.
        circuit = quantum_circuit.build_qpe_circuit(83, 3, 81)
        self.assertEqual((circuit.num_qubits, circuit.num_clbits), (19, 12))
        self.assertEqual(len(circuit.cregs), 1)
        self.assertEqual((quantum_circuit.REGISTER_BITS, quantum_circuit.WORK_BITS), (6, 7))
        stats = quantum_circuit.count_group_powers(circuit)
        self.assertEqual(stats["controlled_power_blocks"], 12)
        self.assertEqual(stats["g_exponents"], [1, 2, 4, 8, 16, 32])
        self.assertEqual(stats["A_exponents"], [1, 2, 4, 8, 16, 32])
        self.assertEqual(stats["equivalent_base_multiplications"], 126)

        measurements = []
        outer_x = []
        outer_h = []
        power_controls = []
        inverse_qfts = []
        for item in circuit.data:
            wires = tuple(circuit.find_bit(bit).index for bit in item.qubits)
            if item.operation.name == "measure":
                measurements.append((wires[0], circuit.find_bit(item.clbits[0]).index))
            elif item.operation.name == "x":
                outer_x.append(wires)
            elif item.operation.name == "h":
                outer_h.append(wires)
            elif len(wires) == 8:
                self.assertEqual(wires[1:], tuple(range(12, 19)))
                power_controls.append(wires[0])
            elif len(wires) == 6:
                inverse_qfts.append((wires, item.operation))
        self.assertEqual(measurements, [(i, i) for i in range(12)])
        self.assertEqual(outer_x, [(12,)])
        self.assertEqual(Counter(outer_h), Counter((i,) for i in range(12)))
        self.assertEqual(Counter(power_controls), Counter(range(12)))
        self.assertEqual([wires for wires, _ in inverse_qfts], [tuple(range(6)), tuple(range(6, 12))])
        indices = np.arange(64)
        inverse_dft = np.exp(-2j * np.pi * np.outer(indices, indices) / 64) / sqrt(64)
        for _, gate in inverse_qfts:
            self.assertTrue(
                np.allclose(Operator(gate).data, inverse_dft, rtol=1e-10, atol=1e-10),
                "An inverse QFT has the wrong sign or omitted bit-order swaps",
            )

    def test_invalid_mapping_parameters_are_rejected(self):
        invalid = (
            (7, 2, 4, 0, 3), (7, 2, 4, 2, 2), (9, 3, 2, 2, 4),
            (7, 0, 4, 2, 3), (7, 2, 7, 2, 3),
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                quantum_circuit.build_exponent_mapping(*arguments)
        for arguments in ((True, 2, 4, 2, 3), (7, 2, 4, True, 3), (7, 2.0, 4, 2, 3)):
            with self.subTest(arguments=arguments), self.assertRaises(TypeError):
                quantum_circuit.build_exponent_mapping(*arguments)

    def test_synthetic_aer_samples_support_known_exponents_after_finite_grid_rounding(self):
        # Orders and exponents are supplied artificial constants. They are
        # never recovered by scanning group elements or the real instance.
        cases = (
            ("small_r3", 7, 2, 3, 2, 3),
            ("small_r5", 11, 3, 5, 2, 4),
            ("finite_grid_41", 83, 3, 41, 4, 7),
        )
        shots, register_bits, grid = 128, 6, 64
        circuits = [
            quantum_circuit.build_qpe_circuit(
                p, g, pow(g, exponent, p), register_bits=register_bits, work_bits=work_bits
            )
            for _, p, g, _, exponent, work_bits in cases
        ]
        simulator = AerSimulator(
            method="statevector", max_memory_mb=1024,
            max_parallel_threads=2, max_parallel_experiments=1,
        )
        compiled = transpile(circuits, simulator, optimization_level=0, seed_transpiler=12345)
        self.assertTrue(any(c.count_ops().get("mcx", 0) for c in compiled))
        result = simulator.run(compiled, shots=shots, seed_simulator=12345).result()
        self.assertTrue(result.success, "Artificial two-register Aer sampling failed")

        summaries = []
        for index, (label, p, g, order, exponent, _) in enumerate(cases):
            with self.subTest(case=label):
                counts = result.get_counts(index)
                self.assertEqual(sum(counts.values()), shots)
                informative = verified = 0
                accepted = set()
                for bitstring, frequency in counts.items():
                    self.assertEqual(len(bitstring), 2 * register_bits)
                    self.assertTrue(set(bitstring).issubset({"0", "1"}))
                    # Qiskit shows high classical bits at left: Z then X.
                    y_z = int(bitstring[:register_bits], 2)
                    y_x = int(bitstring[register_bits:], 2)
                    # Exact integer half-up rounding, not Python banker rounding.
                    u = ((2 * order * y_x + grid) // (2 * grid)) % order
                    v = ((2 * order * y_z + grid) // (2 * grid)) % order
                    if gcd(u, order) != 1:
                        continue
                    informative += frequency
                    candidate = v * pow(u, -1, order) % order
                    if pow(g, candidate, p) == pow(g, exponent, p):
                        accepted.add(candidate)
                        verified += frequency
                self.assertGreater(informative, 0)
                self.assertEqual(accepted, {exponent})
                # Finite grids have side lobes; do not demand every rounded
                # sample be exact. Require substantial signal, not one lucky
                # candidate drawn from an otherwise unrelated distribution.
                self.assertGreaterEqual(verified / informative, 0.4)
                summaries.append({
                    "case": label, "shots": shots,
                    "informative_samples": informative,
                    "publicly_verified_samples": verified,
                })
        type(self).sampling_summary = summaries


if __name__ == "__main__":
    unittest.main()
