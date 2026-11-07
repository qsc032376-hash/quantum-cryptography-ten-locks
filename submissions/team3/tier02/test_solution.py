"""Tier 2 tests using artificial public data and a fake Channel only."""

from collections import Counter
import unittest
from unittest import mock

from submissions.team3.tier02 import solution


class MeasurementCircuitTests(unittest.TestCase):
    def test_z_and_x_measurement_bases(self):
        for basis, expected in ((0, ["measure"]), (1, ["h", "measure"])):
            with self.subTest(basis=basis):
                circuit = solution.build_circuit(basis)
                self.assertEqual((circuit.num_qubits, circuit.num_clbits), (1, 1))
                self.assertEqual([item.operation.name for item in circuit.data], expected)
                measurement = circuit.data[-1]
                self.assertEqual(circuit.find_bit(measurement.qubits[0]).index, 0)
                self.assertEqual(circuit.find_bit(measurement.clbits[0]).index, 0)

    def test_rejects_invalid_basis(self):
        for basis in (-1, 2, True, "X", None):
            with self.subTest(basis=basis), self.assertRaises(ValueError):
                solution.build_circuit(basis)


class SiftingTests(unittest.TestCase):
    def test_qber_uses_only_matching_check_bits_and_preserves_key_indices(self):
        bob = [0, 0, 1, 1, 0, 1, 0, 1]
        measured = [1, 0, 1, 1, 1, 0, 1, 0]
        public = {
            "alice_bases": [0, 1, 1, 0, 0, 1, 0, 1],
            "check_bits": {"0": 0, "1": 1, "2": 1, "3": 1, "4": 1},
            "reconcile": mock.sentinel.public_reconciliation,
        }
        key_bits, stats = solution.analyze_link(bob, measured, public)
        self.assertEqual(key_bits, {5: 0, 6: 1, 7: 0})
        self.assertEqual(stats["qubits"], 8)
        self.assertEqual(stats["sifted_bits"], 6)
        self.assertEqual(stats["check_samples"], 3)
        self.assertEqual(stats["check_errors"], 1)
        self.assertAlmostEqual(stats["qber"], 1 / 3)
        self.assertEqual(stats["retained_key_bits"], 3)
        self.assertEqual(stats["z_basis_measurements"], 4)
        self.assertEqual(stats["x_basis_measurements"], 4)

    def test_empty_matching_check_sample_is_not_reported_as_zero_qber(self):
        public = {"alice_bases": [1, 1], "check_bits": {0: 0}}
        with self.assertRaises(ValueError):
            solution.analyze_link([0, 1], [0, 1], public)

    def test_mismatched_lengths_do_not_silently_truncate(self):
        public = {"alice_bases": [0, 1], "check_bits": {0: 0}}
        with self.assertRaises(ValueError):
            solution.analyze_link([0, 1], [0], public)

    def test_selection_compares_error_rates_not_error_totals(self):
        reports = {
            "link_A": {"check_errors": 3, "check_samples": 20},
            "link_B": {"check_errors": 2, "check_samples": 10},
        }
        self.assertEqual(solution.choose_clean_link(reports), "link_A")

    def test_tied_rates_and_missing_samples_are_inconclusive(self):
        tied = {
            "link_A": {"check_errors": 1, "check_samples": 4},
            "link_B": {"check_errors": 2, "check_samples": 8},
        }
        with self.assertRaises(RuntimeError):
            solution.choose_clean_link(tied)
        empty = {
            "link_A": {"check_errors": 0, "check_samples": 0},
            "link_B": {"check_errors": 1, "check_samples": 4},
        }
        with self.assertRaises(ValueError):
            solution.choose_clean_link(empty)


class ChannelProtocolTests(unittest.TestCase):
    def test_blind_basis_selection_single_receive_then_finish_and_reconcile(self):
        case = self
        events = []
        measured_bits = [0, 1, 1, 0, 1, 0, 0, 1]
        choices = iter([0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1])

        def choose_basis(width):
            case.assertEqual(width, 1)
            events.append(("basis", None))
            return next(choices)

        class FakeChannel:
            log = []

            def __init__(self, name):
                self.name = name
                self.n_qubits = 8
                self.receive_count = 0
                self.finish_count = 0
                self.bases = None
                events.append(("construct", name))

            def receive_all(self, circuits):
                self.receive_count += 1
                case.assertEqual(self.receive_count, 1)
                case.assertEqual(self.finish_count, 0)
                case.assertEqual(Counter(event[0] for event in events)["basis"], 16)
                case.assertEqual(len(circuits), self.n_qubits)
                self.bases = []
                for index, circuit in enumerate(circuits):
                    case.assertEqual((circuit.num_qubits, circuit.num_clbits), (1, 1))
                    names = [item.operation.name for item in circuit.data]
                    case.assertIn(names, (["measure"], ["h", "measure"]))
                    self.bases.append(int("h" in names))
                    self.log.append((self.name, index, circuit))
                events.append(("receive", self.name))
                return measured_bits.copy()

            def finish(self):
                self.finish_count += 1
                case.assertEqual(self.receive_count, 1)
                case.assertEqual(self.finish_count, 1)
                events.append(("finish", self.name))
                return {
                    "alice_bases": self.bases.copy(),
                    "check_bits": {0: int(self.name == "link_A"), 1: 1},
                    "reconcile": {"artificial_link": self.name},
                }

        rng = mock.Mock()
        rng.getrandbits.side_effect = choose_basis
        with (
            mock.patch.object(solution.helper, "Channel", FakeChannel),
            mock.patch.object(solution.random, "Random", return_value=rng),
            mock.patch.object(
                solution.helper, "reconcile", return_value=b"artificial key"
            ) as reconcile,
        ):
            key, report = solution.recover_key_with_diagnostics()

        self.assertEqual(key, b"artificial key")
        self.assertEqual(report["selected_link"], "link_B")
        self.assertEqual(report["measurement_circuits"], 16)
        self.assertEqual(report["links"]["link_A"]["qber"], 0.5)
        self.assertEqual(report["links"]["link_B"]["qber"], 0.0)
        self.assertEqual(
            [event for event in events if event[0] != "basis"],
            [
                ("construct", "link_A"), ("construct", "link_B"),
                ("receive", "link_A"), ("finish", "link_A"),
                ("receive", "link_B"), ("finish", "link_B"),
            ],
        )
        self.assertEqual(len(FakeChannel.log), 16)
        self.assertEqual(len({(link, index) for link, index, _ in FakeChannel.log}), 16)
        reconcile.assert_called_once_with(
            {i: measured_bits[i] for i in range(2, 8)},
            {"artificial_link": "link_B"},
        )

    def test_existing_public_measurement_log_prevents_new_channel(self):
        fake_channel = mock.Mock()
        fake_channel.log = [("link_A", 0, mock.sentinel.measurement_circuit)]
        with (
            mock.patch.object(solution.helper, "Channel", fake_channel),
            mock.patch.object(solution.helper, "reconcile") as reconcile,
        ):
            with self.assertRaises(RuntimeError):
                solution.recover_key_with_diagnostics()
        fake_channel.assert_not_called()
        reconcile.assert_not_called()


class SolveTests(unittest.TestCase):
    def test_solve_uses_official_helpers_with_the_measured_key(self):
        with (
            mock.patch.object(solution, "recover_key", return_value=b"abc") as recover,
            mock.patch.object(
                solution, "load_locked", return_value={"ciphertext_hex": "010203"}
            ) as load_locked,
            mock.patch.object(solution, "xor_bytes", return_value=b"artificial line") as xor,
        ):
            self.assertEqual(solution.solve(), "artificial line")
        recover.assert_called_once_with()
        load_locked.assert_called_once_with(2)
        xor.assert_called_once_with(b"\x01\x02\x03", b"abc")


if __name__ == "__main__":
    unittest.main()
