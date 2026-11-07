"""Exercise the Tier 10 quantum/classical interface with synthetic DH data."""

from importlib import import_module
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import hash_line, keystream, xor_bytes
from submissions.team3 import dh_classical
from submissions.team3.tier10 import solution

check = import_module("common.check")


def locked_fixture(text):
    p, g, order, alice, bob, width = 11, 3, 5, 2, 4, 4
    public_A, public_B = pow(g, alice, p), pow(g, bob, p)
    payload = text.encode("utf-8")
    bits = format(pow(public_A, bob, p), f"0{width}b")
    return {
        "public_parameters": {
            "p": p, "g": g, "order": order, "A": public_A, "B": public_B,
            "key_width_bits": width,
        },
        "ciphertext_hex": xor_bytes(payload, keystream(bits, len(payload))).hex(),
    }


class Tier10IntegrationTests(unittest.TestCase):
    def test_real_aer_to_shared_readout_decrypt_and_hash(self):
        text = "QC-10: synthetic DH fixture"
        with (
            patch.object(solution, "WORK_BITS", 4),
            patch.object(solution, "load_locked", return_value=locked_fixture(text)),
            patch.object(check, "load_hashes", return_value={10: hash_line(text)}),
            patch.object(dh_classical, "measurement_from_counts", wraps=dh_classical.measurement_from_counts) as convert,
            patch.object(dh_classical, "recover_exponent", wraps=dh_classical.recover_exponent) as recover,
        ):
            self.assertEqual(solution.solve(), text)
        self.assertGreater(convert.call_count, 1)
        for conversion in convert.call_args_list:
            self.assertEqual(len(conversion.args[0]), 12)
        # The classical merger sees only the verified full-order witness,
        # both when cross-checking the exponent and when decrypting.
        self.assertEqual(recover.call_count, 2)
        first, second = (call.args[0] for call in recover.call_args_list)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 1)
        self.assertEqual(dh_classical.equation_from_measurement(*first[0], 5), (2, 5))

    def test_rejects_wrong_prefix_and_hash_after_classical_decryption(self):
        # X=13 and Z=26 round to (u,v)=(1,2) in the synthetic order-5 group.
        key = f"{26:06b}{13:06b}"
        recovery = solution.ExponentRecovery(2, {key: 1}, (3, 1), key, {})
        for text, expected, error in (
            ("QC-10:missing space", "QC-10:missing space", "prefix"),
            ("QC-10: synthetic DH fixture", "QC-10: different fixture", "hash"),
        ):
            with (
                self.subTest(error=error),
                patch.object(solution, "load_locked", return_value=locked_fixture(text)),
                patch.object(solution, "recover_exponent_with_diagnostics", return_value=recovery),
                patch.object(check, "load_hashes", return_value={10: hash_line(expected)}),
                self.assertRaisesRegex(RuntimeError, error),
            ):
                solution.solve()


if __name__ == "__main__":
    unittest.main()
