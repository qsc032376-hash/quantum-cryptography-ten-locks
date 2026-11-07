"""Artificial Tier 10 recovery tests; never inspect or solve the real group.

All examples use p=7 with a publicly constructed small subgroup. Quantum
execution is mocked here; circuit and readout tests cover those blocks.
"""

from contextlib import contextmanager
from types import ModuleType
import sys
import unittest
from unittest import mock

from qiskit import QuantumCircuit

from submissions.team3.tier10 import solution


CLASSICAL_MODULE = "submissions.team3.dh_classical"
PARAMETERS = {"p": 7, "g": 2, "A": 2, "B": 4, "order": 3, "key_width_bits": 3}


def raw_key(x, z):
    return format((z << 6) | x, "012b")


GOOD = raw_key(21, 21)       # u=v=1, so a=1 modulo 3.
WRONG_ZERO = raw_key(21, 0)  # u=1,v=0, so candidate a=0 fails A=2.
WRONG_TWO = raw_key(21, 43)  # u=1,v=2, so candidate a=2 fails A=2.
INCONSISTENT = raw_key(0, 21)
ZERO = raw_key(0, 0)
PAIR = (2, 1)               # Classical convention: (-v mod 3, u).
QUERIES = {
    "controlled_power_blocks": 12,
    "g_exponents": [1 << j for j in range(6)],
    "A_exponents": [1 << j for j in range(6)],
    "equivalent_base_multiplications": 126,
}


class ConstructionTests(unittest.TestCase):
    def test_builder_delegates_public_parameters_to_19_qubit_circuit(self):
        expected = QuantumCircuit(19, 12)
        with (
            mock.patch.object(solution, "build_qpe_circuit", return_value=expected) as build,
            mock.patch.object(solution, "load_locked") as load,
        ):
            circuit = solution.build_circuit(parameters=dict(PARAMETERS))
        self.assertIs(circuit, expected)
        build.assert_called_once_with(7, 2, 2, register_bits=6, work_bits=7)
        load.assert_not_called()

    def test_public_generator_order_and_membership_validation(self):
        self.assertEqual(solution._validate_parameters(dict(PARAMETERS)), PARAMETERS)
        for change in ({"order": 2}, {"A": 3}, {"B": 3}, {"g": True}, {"A": True}):
            with self.subTest(change=change):
                parameters = dict(PARAMETERS, **change)
                with self.assertRaises((ValueError, TypeError)):
                    solution._validate_parameters(parameters)

    def test_public_candidate_check_accepts_only_observed_canonical_integer(self):
        self.assertTrue(solution.verify_public_candidate(1, PARAMETERS))
        for candidate in (0, 2, -1, 3, True, 1.0):
            with self.subTest(candidate=candidate):
                self.assertFalse(solution.verify_public_candidate(candidate, PARAMETERS))


class RecoveryTests(unittest.TestCase):
    @contextmanager
    def fake_recovery(self, counts_sequence=None, *, parameters=None, success=True):
        parameters = dict(PARAMETERS if parameters is None else parameters)
        counts_sequence = [{GOOD: 128}] if counts_sequence is None else counts_sequence
        circuit = QuantumCircuit(19, 12)
        circuit.measure(range(12), range(12))
        compiled = mock.Mock(name="artificial_native_circuit")
        compiled.count_ops.return_value = {"mcx": 12, "measure": 12}
        jobs = []
        for counts in counts_sequence:
            result = mock.Mock()
            result.success = success
            result.get_counts.return_value = counts
            job = mock.Mock()
            job.result.return_value = result
            jobs.append(job)
        original_verify = solution.verify_public_candidate
        with (
            mock.patch.object(solution, "_public_parameters", return_value=parameters),
            mock.patch.object(solution, "build_circuit", return_value=circuit) as build,
            mock.patch.object(solution, "count_group_powers", return_value=dict(QUERIES)) as queries,
            mock.patch.object(solution, "transpile", return_value=compiled) as compile_call,
            mock.patch.object(solution, "AerSimulator") as aer,
            mock.patch.object(solution, "verify_public_candidate", wraps=original_verify) as verify,
        ):
            aer.return_value.run.side_effect = jobs
            yield {
                "parameters": parameters, "build": build, "queries": queries,
                "compiled": compiled, "transpile": compile_call, "aer": aer,
                "run": aer.return_value.run, "verify": verify, "jobs": jobs,
            }

    def test_one_measured_candidate_recovers_private_residue_and_witness(self):
        with self.fake_recovery() as run:
            result = solution.recover_exponent_with_diagnostics()
        self.assertEqual(result.exponent, 1)
        self.assertEqual(result.counts, {GOOD: 128})
        self.assertEqual(result.measurement, PAIR)
        self.assertEqual(result.counts_key, GOOD)
        run["verify"].assert_called_once_with(1, PARAMETERS)
        run["run"].assert_called_once_with(
            run["compiled"], shots=128, seed_simulator=solution.SEED_SIMULATOR
        )
        self.assertIs(run["transpile"].call_args.args[1], run["aer"].return_value)
        self.assertNotIn("basis_gates", run["transpile"].call_args.kwargs)
        self.assertEqual(result.diagnostics["controlled_power_blocks_shot_weighted"], 12 * 128)
        self.assertEqual(result.diagnostics["equivalent_base_multiplications_shot_weighted"], 126 * 128)
        self.assertEqual(result.diagnostics["public_candidate_checks"], 1)
        for name in ("exponent=", "counts=", "measurement=", "counts_key="):
            self.assertNotIn(name, repr(result))
        for key in ("exponent", "key", "counts", "measurement", "plaintext"):
            self.assertNotIn(key, result.diagnostics)

    def test_high_weight_wrong_rounding_does_not_inflate_correct_support(self):
        counts = {WRONG_ZERO: 80, GOOD: 16, ZERO: 32}
        with self.fake_recovery([counts]) as run:
            result = solution.recover_exponent_with_diagnostics()
        self.assertEqual([call.args[0] for call in run["verify"].call_args_list], [0, 1])
        self.assertEqual(result.exponent, 1)
        self.assertEqual(result.counts, counts)
        self.assertEqual(result.diagnostics["verified_informative_support_shots"], 16)
        self.assertEqual(result.diagnostics["readout_evidence"]["informative_shots"], 96)
        self.assertEqual(result.diagnostics["support_fraction_of_all_shots"], 16 / 128)
        self.assertEqual(result.diagnostics["support_fraction_of_informative_shots"], 16 / 96)
        self.assertTrue(result.diagnostics["support_is_same_batch_empirical_not_independent_probability"])

    def test_zero_inconsistent_and_partial_equations_are_never_candidate_checks(self):
        # A separate artificial order-six subgroup lets a measured equation
        # determine only a modulo 3; this partial class must not be expanded.
        parameters = {"p": 7, "g": 3, "A": 3, "B": 2, "order": 6, "key_width_bits": 3}
        valid = raw_key(11, 11)
        partial = raw_key(21, 21)
        inconsistent = raw_key(0, 11)
        counts = {valid: 32, partial: 32, inconsistent: 32, ZERO: 32}
        with self.fake_recovery([counts], parameters=parameters) as run:
            result = solution.recover_exponent_with_diagnostics()
        run["verify"].assert_called_once_with(1, parameters)
        evidence = result.diagnostics["readout_evidence"]
        for category in ("informative_shots", "partial_equation_shots", "inconsistent_shots", "uninformative_shots"):
            self.assertEqual(evidence[category], 32)
        self.assertEqual(result.diagnostics["support_fraction_of_all_shots"], 0.25)
        self.assertEqual(result.counts_key, valid)

    def test_candidate_budget_allows_one_supplement_and_deduplicates_checks(self):
        first = {WRONG_ZERO: 96, GOOD: 32}
        second = {WRONG_ZERO: 128}
        with mock.patch.object(solution, "MAX_CANDIDATES_PER_BATCH", 1):
            with self.fake_recovery([first, second]) as run:
                result = solution.recover_exponent_with_diagnostics()
        self.assertEqual([call.args[0] for call in run["verify"].call_args_list], [0, 1])
        self.assertEqual(run["run"].call_count, 2)
        run["transpile"].assert_called_once()
        self.assertEqual(result.counts, {WRONG_ZERO: 224, GOOD: 32})
        self.assertEqual(result.diagnostics["shots"], 256)
        self.assertEqual(result.diagnostics["maximum_public_candidate_checks"], 2)
        self.assertEqual(result.diagnostics["support_fraction_of_all_shots"], 32 / 256)
        self.assertEqual([record["new_candidates_checked"] for record in result.diagnostics["batches"]], [1, 1])

    def test_candidate_budget_never_scans_an_unobserved_exponent(self):
        with mock.patch.object(solution, "MAX_CANDIDATES_PER_BATCH", 1):
            with self.fake_recovery([{WRONG_ZERO: 96, WRONG_TWO: 32}, {WRONG_TWO: 128}]) as run:
                with self.assertRaises(solution.InsufficientQuantumEvidence):
                    solution.recover_exponent_with_diagnostics()
        self.assertEqual([call.args[0] for call in run["verify"].call_args_list], [0, 2])
        self.assertEqual(run["run"].call_count, 2)

    def test_already_rejected_candidate_is_not_checked_again(self):
        with self.fake_recovery([{WRONG_ZERO: 128}, {WRONG_ZERO: 128}]) as run:
            with self.assertRaises(solution.InsufficientQuantumEvidence):
                solution.recover_exponent_with_diagnostics()
        run["verify"].assert_called_once_with(0, PARAMETERS)
        self.assertEqual(run["run"].call_count, 2)

    def test_only_zero_or_inconsistent_outcomes_do_not_trigger_classical_search(self):
        with self.fake_recovery([{ZERO: 64, INCONSISTENT: 64}] * 2) as run:
            with self.assertRaises(solution.InsufficientQuantumEvidence):
                solution.recover_exponent_with_diagnostics()
        run["verify"].assert_not_called()
        self.assertEqual(run["run"].call_count, 2)

    def test_aer_failure_and_incomplete_counts_stop_without_retry(self):
        for success, counts in ((False, {GOOD: 128}), (True, {GOOD: 127})):
            with self.subTest(success=success):
                with self.fake_recovery([counts], success=success) as run:
                    with self.assertRaises(RuntimeError):
                        solution.recover_exponent_with_diagnostics()
                run["run"].assert_called_once()
                run["verify"].assert_not_called()

    def test_malformed_readout_does_not_trigger_supplement(self):
        with self.fake_recovery([{"0": 128}]) as run:
            with self.assertRaises(ValueError):
                solution.recover_exponent_with_diagnostics()
        run["run"].assert_called_once()
        run["verify"].assert_not_called()

    def test_inconsistent_support_accounting_is_not_reported_as_success(self):
        with self.fake_recovery() as run:
            with mock.patch.object(solution, "candidate_evidence", return_value=(
                {1: 128}, {1: PAIR}, {"informative_shots": 127},
            )):
                with self.assertRaisesRegex(RuntimeError, "support accounting"):
                    solution.recover_exponent_with_diagnostics()
        run["run"].assert_called_once()

    def test_query_count_failure_precedes_compilation(self):
        with self.fake_recovery() as run:
            run["queries"].return_value = {"controlled_power_blocks": 11}
            with self.assertRaisesRegex(RuntimeError, "controlled powers"):
                solution.recover_exponent_with_diagnostics()
        run["transpile"].assert_not_called()
        run["run"].assert_not_called()

    def test_compilation_budget_precedes_aer(self):
        clock = [0.0]

        def compile_slowly(*_args, **_kwargs):
            clock[0] = 100.0
            return mock.sentinel.compiled

        with self.fake_recovery() as run:
            run["transpile"].side_effect = compile_slowly
            with mock.patch.object(solution.time, "perf_counter", side_effect=lambda: clock[0]):
                with self.assertRaises(TimeoutError):
                    solution.recover_exponent_with_diagnostics()
        run["run"].assert_not_called()

    def test_time_budget_prevents_another_large_batch(self):
        clock = [0.0]
        with self.fake_recovery([{WRONG_ZERO: 128}]) as run:
            job = run["jobs"][0]

            def run_slowly(*_args, **_kwargs):
                clock[0] = 60.0
                return job

            run["run"].side_effect = run_slowly
            with mock.patch.object(solution.time, "perf_counter", side_effect=lambda: clock[0]):
                with self.assertRaisesRegex(TimeoutError, "supplemental"):
                    solution.recover_exponent_with_diagnostics()
        run["run"].assert_called_once()

    def test_integer_adapter_returns_only_measured_residue(self):
        result = solution.ExponentRecovery(1, {GOOD: 128}, PAIR, GOOD, {})
        with mock.patch.object(solution, "recover_exponent_with_diagnostics", return_value=result) as recover:
            self.assertEqual(solution.recover_exponent(), 1)
        recover.assert_called_once_with()


class SolveTests(unittest.TestCase):
    def test_missing_classical_module_precedes_quantum_work_and_data_loading(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "load_locked") as load,
            mock.patch.object(solution, "recover_exponent_with_diagnostics") as recover,
        ):
            with self.assertRaisesRegex(NotImplementedError, "dh_classical"):
                solution.solve()
        load.assert_not_called()
        recover.assert_not_called()

    @contextmanager
    def fake_classical(self, *, text="artificial DH plaintext", verified=True):
        classical = ModuleType(CLASSICAL_MODULE)
        classical.measurement_from_counts = mock.Mock(return_value=PAIR)
        classical.equation_from_counts = mock.Mock(return_value=(1, 3))
        classical.recover_exponent = mock.Mock(return_value=1)
        classical.decrypt_tier10 = mock.Mock(return_value=text)
        # Deliberately retain bad raw samples. Only GOOD may reach the shared
        # converter, and only its one full-order pair may reach the merger.
        result = solution.ExponentRecovery(
            1, {WRONG_ZERO: 80, GOOD: 16, ZERO: 32}, PAIR, GOOD, {},
        )
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: classical}),
            mock.patch.object(solution, "load_locked", return_value={
                "public_parameters": dict(PARAMETERS), "ciphertext_hex": "a1b2",
            }) as load,
            mock.patch.object(solution, "recover_exponent_with_diagnostics", return_value=result) as recover,
            mock.patch.object(solution, "is_correct", return_value=verified) as correct,
        ):
            yield classical, load, recover, correct

    def test_shared_api_receives_only_one_publicly_verified_full_order_witness(self):
        with self.fake_classical() as (classical, load, recover, correct):
            self.assertEqual(solution.solve(), "artificial DH plaintext")
        load.assert_called_once_with(10)
        recover.assert_called_once_with()
        classical.measurement_from_counts.assert_called_once_with(GOOD, 3, register_bits=6, layout="xz")
        classical.equation_from_counts.assert_called_once_with(GOOD, 3, register_bits=6, layout="xz")
        classical.recover_exponent.assert_called_once_with([PAIR], PARAMETERS)
        classical.decrypt_tier10.assert_called_once_with([PAIR], PARAMETERS, "a1b2")
        correct.assert_called_once_with(10, "artificial DH plaintext")

    def test_shared_pair_or_partial_equation_mismatch_stops_before_merging(self):
        for field, returned in (("measurement_from_counts", (0, 1)), ("equation_from_counts", (1, 1))):
            with self.subTest(field=field):
                with self.fake_classical() as (classical, _, recover, correct):
                    getattr(classical, field).return_value = returned
                    with self.assertRaisesRegex(RuntimeError, "convention"):
                        solution.solve()
                recover.assert_called_once()
                classical.recover_exponent.assert_not_called()
                classical.decrypt_tier10.assert_not_called()
                correct.assert_not_called()

    def test_shared_exponent_disagreement_prevents_decryption(self):
        with self.fake_classical() as (classical, _, recover, correct):
            classical.recover_exponent.return_value = 2
            with self.assertRaisesRegex(RuntimeError, "recovery disagrees"):
                solution.solve()
        recover.assert_called_once()
        classical.decrypt_tier10.assert_not_called()
        correct.assert_not_called()

    def test_hash_mismatch_or_nontext_plaintext_is_never_returned(self):
        for text, verified in (("artificial wrong text", False), (b"artificial bytes", True)):
            with self.subTest(result_type=type(text).__name__):
                with self.fake_classical(text=text, verified=verified) as (classical, _, recover, correct):
                    with self.assertRaises(RuntimeError):
                        solution.solve()
                recover.assert_called_once()
                classical.decrypt_tier10.assert_called_once()
                if isinstance(text, bytes):
                    correct.assert_not_called()


if __name__ == "__main__":
    unittest.main()
