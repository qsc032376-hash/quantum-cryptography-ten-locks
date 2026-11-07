"""Artificial Tier 5 tests: no real locked data or Grover execution."""

from contextlib import contextmanager
import sys
from types import ModuleType
import unittest
from unittest import mock

from qiskit import QuantumCircuit

from common.toy_cipher import ToyCipher
from submissions.team3.tier05 import solution


CLASSICAL_MODULE = "submissions.team3.toy_cipher_classical"
SYNTHETIC_KEY = 150
SYNTHETIC_BITS = "0010010110"
OTHER_BITS = "1010101010"
SYNTHETIC_PREFIX = b"QC-05: "
SYNTHETIC_TEXT = b"QC-05: synthetic unit-test text"


def artificial_ciphertext():
    """Encrypt one chosen artificial example; never enumerate candidate keys."""
    return ToyCipher(SYNTHETIC_KEY, 10).encrypt(SYNTHETIC_TEXT)


class MeasurementTests(unittest.TestCase):
    def test_bit_order_and_leading_zeroes(self):
        for bitstring, expected in (
            ("0000000000", 0),
            ("0000000001", 1),
            ("1000000000", 512),
            (SYNTHETIC_BITS, SYNTHETIC_KEY),
            ("1111111111", 1023),
        ):
            with self.subTest(bitstring=bitstring):
                self.assertEqual(solution.measurement_to_key(bitstring), expected)

    def test_rejects_non_strings(self):
        for value in (None, True, 1, 1.5, b"0000000001", [0] * 10):
            with self.subTest(input_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    solution.measurement_to_key(value)

    def test_rejects_malformed_register_strings(self):
        for value in (
            "", "0" * 9, "0" * 11, "0" * 9 + "2", "0" * 9 + "a",
            " " + "0" * 10, "0" * 10 + "\n", "0" * 5 + " " + "0" * 5,
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    solution.measurement_to_key(value)


class TheoreticalProbabilityTests(unittest.TestCase):
    def test_single_marked_key_probability(self):
        self.assertAlmostEqual(solution.theoretical_success_probability(0), 1 / 1024)
        self.assertAlmostEqual(
            solution.theoretical_success_probability(25), 0.9994612447444079,
            places=14,
        )
        self.assertGreater(
            solution.theoretical_success_probability(25),
            solution.theoretical_success_probability(24),
        )
        self.assertGreater(
            solution.theoretical_success_probability(25),
            solution.theoretical_success_probability(26),
        )

    def test_rejects_invalid_theory_inputs(self):
        for value in (-1, True, 1.5, "25"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solution.theoretical_success_probability(value)


class BuildCircuitTests(unittest.TestCase):
    def test_key_only_measurement_and_iteration_layout(self):
        ciphertext = artificial_ciphertext()
        for iterations in (1, 25):
            with self.subTest(iterations=iterations):
                phase = QuantumCircuit(19, name=solution.oracle.ORACLE_NAME)
                diffuser = QuantumCircuit(19, name="artificial_diffuser")
                with (
                    mock.patch.object(
                        solution.oracle, "build_phase_oracle", return_value=phase
                    ) as build_phase,
                    mock.patch.object(
                        solution.oracle, "build_diffuser", return_value=diffuser
                    ),
                    mock.patch.object(solution, "load_locked") as load_locked,
                ):
                    circuit = solution.build_circuit(
                        ciphertext=ciphertext, iterations=iterations
                    )
                load_locked.assert_not_called()
                build_phase.assert_called_once_with(ciphertext)
                self.assertEqual((circuit.num_qubits, circuit.num_clbits), (19, 10))
                self.assertEqual(len(circuit.cregs), 1)
                self.assertEqual(solution.count_oracle_calls(circuit), iterations)
                operations = [item.operation.name for item in circuit.data]
                self.assertEqual(operations[:10], ["h"] * 10)
                self.assertEqual(
                    operations[10:-10],
                    [solution.oracle.ORACLE_NAME, "artificial_diffuser"] * iterations,
                )
                self.assertEqual(operations[-10:], ["measure"] * 10)
                self.assertEqual(
                    [circuit.find_bit(item.qubits[0]).index for item in circuit.data[:10]],
                    list(range(10)),
                )
                self.assertEqual(
                    [
                        (circuit.find_bit(item.qubits[0]).index,
                         circuit.find_bit(item.clbits[0]).index)
                        for item in circuit.data[-10:]
                    ],
                    [(index, index) for index in range(10)],
                )

    def test_invalid_iterations_fail_before_loading_oracle_inputs(self):
        for iterations in (0, -1, 26, True, 1.5, "25"):
            with self.subTest(iterations=iterations):
                with (
                    mock.patch.object(solution, "_public_inputs") as public_inputs,
                    mock.patch.object(solution.oracle, "build_phase_oracle") as phase,
                ):
                    with self.assertRaises((TypeError, ValueError)):
                        solution.build_circuit(iterations=iterations)
                public_inputs.assert_not_called()
                phase.assert_not_called()


class CandidateValidationTests(unittest.TestCase):
    def test_artificial_known_plaintext_prefix(self):
        ciphertext = artificial_ciphertext()
        self.assertTrue(solution.validate_candidate(SYNTHETIC_KEY, ciphertext, b"QC"))
        self.assertTrue(
            solution.validate_candidate(SYNTHETIC_KEY, ciphertext, SYNTHETIC_PREFIX)
        )
        self.assertFalse(solution.validate_candidate(SYNTHETIC_KEY, ciphertext, b"AB"))

    def test_decrypts_only_the_public_prefix_slice(self):
        ciphertext = artificial_ciphertext()
        with mock.patch.object(
            ToyCipher, "decrypt", autospec=True, return_value=SYNTHETIC_PREFIX
        ) as decrypt:
            self.assertTrue(
                solution.validate_candidate(SYNTHETIC_KEY, ciphertext, SYNTHETIC_PREFIX)
            )
        decrypt.assert_called_once()
        self.assertEqual(decrypt.call_args.args[1], ciphertext[:len(SYNTHETIC_PREFIX)])

    def test_rejects_invalid_candidate_inputs(self):
        ciphertext = artificial_ciphertext()
        for key in (-1, 1024, True, 1.5, "1"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    solution.validate_candidate(key, ciphertext, SYNTHETIC_PREFIX)
        for data, prefix in ((ciphertext.hex(), b"QC"), (ciphertext, "QC")):
            with self.subTest(input_type=type(prefix).__name__):
                with self.assertRaises(TypeError):
                    solution.validate_candidate(SYNTHETIC_KEY, data, prefix)
        for data, prefix in ((ciphertext, b""), (ciphertext, b"Q"), (b"x", b"QC")):
            with self.subTest(prefix_length=len(prefix)):
                with self.assertRaises(ValueError):
                    solution.validate_candidate(SYNTHETIC_KEY, data, prefix)


class RecoveryTests(unittest.TestCase):
    @contextmanager
    def fake_run(self, counts, *, valid_keys=(SYNTHETIC_KEY,), success=True):
        ciphertext = artificial_ciphertext()
        circuit = QuantumCircuit(19, 10)
        result = mock.Mock(success=success)
        result.get_counts.return_value = counts
        simulator = mock.Mock()
        simulator.run.return_value.result.return_value = result
        with (
            mock.patch.object(
                solution, "_public_inputs", return_value=(ciphertext, SYNTHETIC_PREFIX)
            ),
            mock.patch.object(solution, "build_circuit", return_value=circuit) as build,
            mock.patch.object(solution, "AerSimulator", return_value=simulator) as aer,
            mock.patch.object(
                solution, "transpile", return_value=mock.sentinel.compiled
            ) as transpile,
            mock.patch.object(
                solution, "validate_candidate",
                side_effect=lambda key, data, prefix: key in valid_keys,
            ) as validate,
        ):
            yield {
                "ciphertext": ciphertext, "circuit": circuit, "result": result,
                "simulator": simulator, "build": build, "aer": aer,
                "transpile": transpile, "validate": validate,
            }

    def test_checks_only_measured_candidates_and_reports_majority(self):
        with self.fake_run({SYNTHETIC_BITS: 96, OTHER_BITS: 32}) as run:
            key, report = solution.recover_key_with_diagnostics()
        self.assertEqual(key, SYNTHETIC_KEY)
        run["build"].assert_called_once_with(ciphertext=run["ciphertext"], iterations=25)
        run["transpile"].assert_called_once()
        run["simulator"].run.assert_called_once_with(mock.sentinel.compiled, shots=128)
        run["validate"].assert_has_calls([
            mock.call(SYNTHETIC_KEY, run["ciphertext"], SYNTHETIC_PREFIX),
            mock.call(682, run["ciphertext"], SYNTHETIC_PREFIX),
        ])
        self.assertEqual(run["validate"].call_count, 2)
        self.assertEqual(report["prefix_valid_candidates"], 1)
        self.assertEqual(report["prefix_success_shots"], 96)
        self.assertEqual(report["measured_success_rate"], 0.75)
        self.assertEqual(report["oracle_queries_including_shots"], 25 * 128)
        self.assertNotIn("key", report)
        self.assertNotIn("counts", report)

    def test_rejects_absent_ambiguous_or_nonmajority_valid_candidates(self):
        cases = (
            ({SYNTHETIC_BITS: 96, OTHER_BITS: 32}, ()),
            ({SYNTHETIC_BITS: 96, OTHER_BITS: 32}, (SYNTHETIC_KEY, 682)),
            ({SYNTHETIC_BITS: 64, OTHER_BITS: 64}, (SYNTHETIC_KEY,)),
            ({SYNTHETIC_BITS: 32, OTHER_BITS: 96}, (SYNTHETIC_KEY,)),
        )
        for counts, valid_keys in cases:
            with self.subTest(valid_keys=valid_keys, counts=counts):
                with self.fake_run(counts, valid_keys=valid_keys) as run:
                    with self.assertRaises(RuntimeError):
                        solution.recover_key_with_diagnostics()
                run["simulator"].run.assert_called_once()

    def test_failed_simulator_result_is_not_retried(self):
        with self.fake_run({}, success=False) as run:
            with self.assertRaises(RuntimeError):
                solution.recover_key_with_diagnostics()
        run["simulator"].run.assert_called_once()
        run["result"].get_counts.assert_not_called()
        run["validate"].assert_not_called()

    def test_simulator_exception_is_not_retried(self):
        with self.fake_run({}) as run:
            run["simulator"].run.side_effect = RuntimeError("artificial simulator failure")
            with self.assertRaisesRegex(RuntimeError, "artificial simulator failure"):
                solution.recover_key_with_diagnostics()
        run["simulator"].run.assert_called_once()
        run["validate"].assert_not_called()

    def test_rejects_invalid_measurement_frequencies(self):
        cases = ({}, {SYNTHETIC_BITS: 0}, {SYNTHETIC_BITS: -1},
                 {SYNTHETIC_BITS: True}, {SYNTHETIC_BITS: 128.0},
                 {SYNTHETIC_BITS: 127})
        for counts in cases:
            with self.subTest(counts=counts):
                with self.fake_run(counts) as run:
                    with self.assertRaises(RuntimeError):
                        solution.recover_key_with_diagnostics()
                run["simulator"].run.assert_called_once()
                run["validate"].assert_not_called()

    def test_rejects_malformed_measured_keys(self):
        for measured in ("0" * 9, "0" * 9 + "2", 150):
            with self.subTest(measured=measured):
                with self.fake_run({measured: 128}) as run:
                    with self.assertRaises((TypeError, ValueError)):
                        solution.recover_key_with_diagnostics()
                run["simulator"].run.assert_called_once()
                run["validate"].assert_not_called()

    def test_budget_errors_precede_loading_and_simulation(self):
        kwargs_list = [
            {"iterations": value} for value in (0, -1, 26, True, 1.5)
        ] + [{"shots": value} for value in (0, -1, 129, True, 1.5)]
        for kwargs in kwargs_list:
            with self.subTest(kwargs=kwargs):
                with (
                    mock.patch.object(solution, "_public_inputs") as public_inputs,
                    mock.patch.object(solution, "AerSimulator") as aer,
                ):
                    with self.assertRaises((TypeError, ValueError)):
                        solution.recover_key_with_diagnostics(**kwargs)
                public_inputs.assert_not_called()
                aer.assert_not_called()

    def test_public_integer_entry_point(self):
        with mock.patch.object(
            solution, "recover_key_with_diagnostics", return_value=(SYNTHETIC_KEY, {})
        ) as recover:
            self.assertEqual(solution.recover_key(), SYNTHETIC_KEY)
        recover.assert_called_once_with()


class SolveTests(unittest.TestCase):
    def test_missing_classical_module_precedes_any_quantum_work(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "recover_key") as recover,
            mock.patch.object(solution, "load_locked") as load_locked,
        ):
            with self.assertRaisesRegex(NotImplementedError, "toy_cipher_classical"):
                solution.solve()
        recover.assert_not_called()
        load_locked.assert_not_called()

    def test_delegates_full_decryption_using_synthetic_values(self):
        classical = ModuleType(CLASSICAL_MODULE)
        classical.decrypt_tier5 = mock.Mock(return_value="synthetic result")
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: classical}),
            mock.patch.object(solution, "recover_key", return_value=SYNTHETIC_KEY) as recover,
            mock.patch.object(
                solution, "load_locked", return_value={"ciphertext_hex": "010203"}
            ) as load_locked,
        ):
            self.assertEqual(solution.solve(), "synthetic result")
        recover.assert_called_once_with()
        load_locked.assert_called_once_with(5)
        classical.decrypt_tier5.assert_called_once_with(SYNTHETIC_KEY, "010203")


if __name__ == "__main__":
    unittest.main()
