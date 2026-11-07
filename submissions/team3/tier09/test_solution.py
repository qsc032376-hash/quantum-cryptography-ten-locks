"""Artificial Tier 9 pipeline checks, never a classical solution of real N.

All recovery mocks and the one small Aer circuit use synthetic N=15. Actual
Tier 9 challenge files, ciphertext, factors, and order are never read here.
"""

from contextlib import contextmanager
from types import ModuleType
import sys
import unittest
from unittest import mock

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from submissions.team3.tier09 import solution


CLASSICAL_MODULE = "submissions.team3.rsa_classical"
ZERO = "0" * 14
QUARTER = format(1 << 12, "014b")
HALF = format(1 << 13, "014b")
THREE_QUARTERS = format(3 << 12, "014b")
MIXED_COUNTS = {ZERO: 16, QUARTER: 16, HALF: 16, THREE_QUARTERS: 16}
EXPECTED_QUERIES = {
    "controlled_power_blocks": 14,
    "equivalent_base_multiplications": 16383,
    "exponents": [1 << j for j in range(14)],
}
ARTIFICIAL_ORDER_RESULT = (4, {"minimal_order_verified": True})


class CircuitLayoutTests(unittest.TestCase):
    def test_work_one_counting_layout_and_named_powers(self):
        def fake_multiplier(_multiplier, _modulus, work_bits):
            return QuantumCircuit(1 + work_bits)

        with (
            mock.patch.object(solution, "build_controlled_multiplier", side_effect=fake_multiplier),
            mock.patch.object(solution, "load_locked") as load_locked,
        ):
            circuit = solution.build_circuit(modulus=15, base=2, phase_bits=14, work_bits=7)
        load_locked.assert_not_called()
        self.assertEqual((circuit.num_qubits, circuit.num_clbits), (21, 14))
        self.assertEqual(solution.count_modular_powers(circuit), EXPECTED_QUERIES)
        x_wires = [
            circuit.find_bit(item.qubits[0]).index
            for item in circuit.data if item.operation.name == "x"
        ]
        self.assertEqual(x_wires, [14], "Only work[0] prepares the integer one")
        measurements = [
            (circuit.find_bit(item.qubits[0]).index, circuit.find_bit(item.clbits[0]).index)
            for item in circuit.data if item.operation.name == "measure"
        ]
        self.assertEqual(measurements, [(j, j) for j in range(14)])
        powers = [
            item for item in circuit.data
            if item.operation.name.startswith("tier09_controlled_modmul_power_")
        ]
        self.assertEqual(len(powers), 14)
        for control, item in enumerate(powers):
            wires = [circuit.find_bit(wire).index for wire in item.qubits]
            self.assertEqual(wires[0], control)
            self.assertEqual(wires[1:], list(range(14, 21)))
            self.assertEqual(len(set(wires)), len(wires))
            self.assertEqual(len(wires), 8, "No dirty or clean auxiliary wires")

    def test_non_coprime_base_is_rejected_before_any_multiplier(self):
        with mock.patch.object(solution, "build_controlled_multiplier") as build:
            with self.assertRaises(ValueError):
                solution.build_circuit(modulus=15, base=3)
        build.assert_not_called()

    def test_dimension_limits(self):
        for keywords in (
            {"modulus": 15, "work_bits": 3},
            {"modulus": 15, "phase_bits": 0},
            {"modulus": 15, "phase_bits": True},
            {"modulus": 15, "base": True},
            {"modulus": 15, "base": 1},
        ):
            with self.subTest(keywords=keywords):
                with self.assertRaises(ValueError):
                    solution.build_circuit(**keywords)


class RecoveryTests(unittest.TestCase):
    @contextmanager
    def fake_recovery(self, counts_sequence=None, order_effect=None, factors=(3, 5), success=True):
        if counts_sequence is None:
            counts_sequence = [dict(MIXED_COUNTS)]
        circuit = QuantumCircuit(21, 14)
        circuit.measure(range(14), range(14))
        compiled = mock.Mock(name="artificial_native_compiled")
        compiled.count_ops.return_value = {"mcx": 10, "measure": 14}
        jobs = []
        for counts in counts_sequence:
            result = mock.Mock()
            result.success = success
            result.get_counts.return_value = counts
            job = mock.Mock()
            job.result.return_value = result
            jobs.append(job)
        with (
            mock.patch.object(solution, "_public_parameters", return_value={"N": 15}),
            mock.patch.object(solution, "build_circuit", return_value=circuit) as build,
            mock.patch.object(solution, "count_modular_powers", return_value=dict(EXPECTED_QUERIES)) as count,
            mock.patch.object(solution, "transpile", return_value=compiled) as compile_call,
            mock.patch.object(solution, "AerSimulator") as aer,
            mock.patch.object(solution, "recover_order", return_value=ARTIFICIAL_ORDER_RESULT) as order,
            mock.patch.object(solution, "factors_from_order", return_value=factors) as factor_call,
        ):
            aer.return_value.run.side_effect = jobs
            if order_effect is not None:
                order.side_effect = order_effect
            yield {
                "build": build, "queries": count, "transpile": compile_call,
                "compiled": compiled,
                "aer": aer, "run": aer.return_value.run, "order": order,
                "factors": factor_call, "jobs": jobs,
            }

    def test_multiple_outcomes_are_used_in_one_successful_batch(self):
        with self.fake_recovery() as run:
            factors, diagnostics = solution.recover_factors_with_diagnostics()
        self.assertEqual(factors, (3, 5))
        run["order"].assert_called_once_with(MIXED_COUNTS, 2, 15, 14)
        run["factors"].assert_called_once_with(2, 15, 4)
        run["transpile"].assert_called_once()
        run["run"].assert_called_once_with(
            run["compiled"], shots=64, seed_simulator=solution.SEED_SIMULATOR
        )
        self.assertIs(run["transpile"].call_args.args[1], run["aer"].return_value)
        self.assertNotIn("basis_gates", run["transpile"].call_args.kwargs)
        self.assertEqual(diagnostics["distinct_measured_outcomes"], 4)
        self.assertEqual(diagnostics["shots"], 64)
        self.assertEqual(diagnostics["recovered_order"], 4)
        self.assertTrue(diagnostics["modular_order_check"])
        self.assertTrue(diagnostics["factors_recovered_from_measurements"])
        self.assertEqual(diagnostics["controlled_power_blocks_shot_weighted"], 14 * 64)
        self.assertEqual(diagnostics["equivalent_base_multiplications_shot_weighted"], 16383 * 64)
        for forbidden in ("p", "q", "factors", "key", "counts", "plaintext"):
            self.assertNotIn(forbidden, diagnostics)

    def test_insufficient_measurements_allow_one_bounded_supplement(self):
        effects = [solution.InsufficientMeasurements("artificial shortfall"), ARTIFICIAL_ORDER_RESULT]
        with self.fake_recovery([{ZERO: 64}, dict(MIXED_COUNTS)], order_effect=effects) as run:
            factors, diagnostics = solution.recover_factors_with_diagnostics()
        self.assertEqual(factors, (3, 5))
        self.assertEqual(run["run"].call_count, 2)
        self.assertEqual(run["order"].call_count, 2)
        combined = dict(MIXED_COUNTS)
        combined[ZERO] += 64
        self.assertEqual(run["order"].call_args.args, (combined, 2, 15, 14))
        self.assertEqual(diagnostics["shots"], 128)
        self.assertEqual(diagnostics["aer_run_calls"], 2)
        self.assertEqual([call.kwargs["shots"] for call in run["run"].call_args_list], [64, 64])
        self.assertEqual([call.kwargs["seed_simulator"] for call in run["run"].call_args_list],
                         [solution.SEED_SIMULATOR, solution.SEED_SIMULATOR + 1])
        run["transpile"].assert_called_once()

    def test_two_insufficient_batches_stop_without_classical_factor_fallback(self):
        effects = [solution.InsufficientMeasurements("artificial shortfall")] * 2
        with self.fake_recovery([{ZERO: 64}, {ZERO: 64}], order_effect=effects) as run:
            with self.assertRaises(solution.InsufficientMeasurements):
                solution.recover_factors_with_diagnostics()
        self.assertEqual(run["run"].call_count, 2)
        run["factors"].assert_not_called()

    def test_aer_failure_does_not_retry_or_process_measurements(self):
        with self.fake_recovery(success=False) as run:
            with self.assertRaisesRegex(RuntimeError, "Aer failed"):
                solution.recover_factors_with_diagnostics()
        run["run"].assert_called_once()
        run["order"].assert_not_called()
        run["factors"].assert_not_called()

    def test_incomplete_counts_do_not_reach_order_processing(self):
        with self.fake_recovery([{ZERO: 63}]) as run:
            with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                solution.recover_factors_with_diagnostics()
        run["run"].assert_called_once()
        run["order"].assert_not_called()

    def test_non_sampling_order_error_does_not_repeat_simulation(self):
        with self.fake_recovery(order_effect=ValueError("artificial invalid readout")) as run:
            with self.assertRaises(ValueError):
                solution.recover_factors_with_diagnostics()
        run["run"].assert_called_once()
        run["factors"].assert_not_called()

    def test_wrong_factor_pairs_fail_without_more_quantum_batches(self):
        for factors in ((1, 15), (3, 3), (True, 15), (3,), (3.0, 5)):
            with self.subTest(factors=factors):
                with self.fake_recovery(factors=factors) as run:
                    with self.assertRaisesRegex(RuntimeError, "factors"):
                        solution.recover_factors_with_diagnostics()
                run["run"].assert_called_once()

    def test_unusable_order_does_not_blindly_repeat_same_base(self):
        with self.fake_recovery() as run:
            run["factors"].side_effect = ValueError("artificial unusable order")
            with self.assertRaises(ValueError):
                solution.recover_factors_with_diagnostics()
        run["run"].assert_called_once()

    def test_wrong_power_accounting_precedes_compilation_and_aer(self):
        with self.fake_recovery() as run:
            run["queries"].return_value = {"controlled_power_blocks": 11}
            with self.assertRaisesRegex(RuntimeError, "modular powers"):
                solution.recover_factors_with_diagnostics()
        run["transpile"].assert_not_called()
        run["run"].assert_not_called()

    def test_compilation_timeout_precedes_quantum_work(self):
        clock = [0.0]

        def compile_slowly(*_args, **_kwargs):
            clock[0] = 100.0
            return mock.sentinel.compiled

        with self.fake_recovery() as run:
            run["transpile"].side_effect = compile_slowly
            with mock.patch.object(solution.time, "perf_counter", side_effect=lambda: clock[0]):
                with self.assertRaises(TimeoutError):
                    solution.recover_factors_with_diagnostics()
        run["run"].assert_not_called()
        run["order"].assert_not_called()

    def test_time_budget_can_prevent_supplement(self):
        clock = [0.0]
        with self.fake_recovery(order_effect=solution.InsufficientMeasurements("artificial shortfall")) as run:
            job = run["jobs"][0]

            def run_slowly(*_args, **_kwargs):
                clock[0] = 60.0
                return job

            run["run"].side_effect = run_slowly
            with mock.patch.object(solution.time, "perf_counter", side_effect=lambda: clock[0]):
                with self.assertRaisesRegex(TimeoutError, "supplemental"):
                    solution.recover_factors_with_diagnostics()
        run["run"].assert_called_once()
        run["factors"].assert_not_called()

    def test_integer_pair_adapter_exposes_only_measured_pair(self):
        with mock.patch.object(solution, "recover_factors_with_diagnostics", return_value=((3, 5), {})) as recover:
            self.assertEqual(solution.recover_factors(), (3, 5))
        recover.assert_called_once_with()


class SolveTests(unittest.TestCase):
    def test_missing_classical_module_precedes_data_loading_and_quantum_work(self):
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: None}),
            mock.patch.object(solution, "load_locked") as load,
            mock.patch.object(solution, "recover_factors") as recover,
        ):
            with self.assertRaisesRegex(NotImplementedError, "rsa_classical"):
                solution.solve()
        load.assert_not_called()
        recover.assert_not_called()

    @contextmanager
    def fake_classical(self, plaintext="artificial RSA plaintext", verified=True):
        module = ModuleType(CLASSICAL_MODULE)
        module.decrypt_tier9 = mock.Mock(return_value=plaintext)
        public = {"N": 15, "e": 3, "wrapped_key": 2, "key_width_bits": 4}
        with (
            mock.patch.dict(sys.modules, {CLASSICAL_MODULE: module}),
            mock.patch.object(solution, "load_locked", return_value={
                "public_parameters": public, "ciphertext_hex": "ab12",
            }) as load,
            mock.patch.object(solution, "recover_factors", return_value=(3, 5)) as recover,
            mock.patch.object(solution, "is_correct", return_value=verified) as correct,
        ):
            yield module.decrypt_tier9, public, load, recover, correct

    def test_solve_delegates_only_recovered_factors_and_checks_final_hash(self):
        with self.fake_classical() as (decrypt, public, load, recover, correct):
            self.assertEqual(solution.solve(), "artificial RSA plaintext")
        load.assert_called_once_with(9)
        recover.assert_called_once_with()
        decrypt.assert_called_once_with(3, 5, public, "ab12")
        correct.assert_called_once_with(9, "artificial RSA plaintext")

    def test_hash_mismatch_or_nontext_result_never_returns_plaintext(self):
        for plaintext, verified in (("artificial wrong text", False), (b"artificial bytes", True)):
            with self.subTest(result_type=type(plaintext).__name__):
                with self.fake_classical(plaintext, verified) as (decrypt, _, _, recover, correct):
                    with self.assertRaises(RuntimeError):
                        solution.solve()
                recover.assert_called_once()
                decrypt.assert_called_once()
                if isinstance(plaintext, bytes):
                    correct.assert_not_called()


class SmallSyntheticAerTests(unittest.TestCase):
    def test_small_artificial_order_finding_pipeline(self):
        # Synthetic N=15 has a known demonstration order; this test neither
        # constructs nor analyzes the real Tier 9 modulus.
        with mock.patch.object(solution, "load_locked") as load:
            circuit = solution.build_circuit(modulus=15, base=2, phase_bits=8, work_bits=4)
        load.assert_not_called()
        simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
        compiled = transpile(circuit, simulator,
                             optimization_level=1, seed_transpiler=12345, num_processes=1)
        self.assertTrue(
            set(compiled.count_ops()) & {"ccx", "mcx"},
            "The small Aer test should exercise native controlled-X operations",
        )
        result = simulator.run(compiled, shots=32, seed_simulator=808).result()
        self.assertTrue(result.success)
        counts = {bits: int(count) for bits, count in result.get_counts().items()}
        expected_support = {format(value, "08b") for value in (0, 64, 128, 192)}
        self.assertTrue(set(counts).issubset(expected_support), "Artificial QFT readout has wrong bit order")
        self.assertEqual(sum(counts.values()), 32)
        order, diagnostics = solution.recover_order(counts, 2, 15, 8)
        self.assertEqual(order, 4)
        self.assertTrue(diagnostics["minimal_order_verified"])
        self.assertEqual(set(solution.factors_from_order(2, 15, order)), {3, 5})


if __name__ == "__main__":
    unittest.main()
