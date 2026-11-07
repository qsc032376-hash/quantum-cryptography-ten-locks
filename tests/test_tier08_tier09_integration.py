"""Exercise both Shor → RSA solve paths using only synthetic locked data."""

from functools import partial
from importlib import import_module
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import hash_line, keystream, xor_bytes
from submissions.team3.tier08 import solution as tier08
from submissions.team3.tier08.order import InsufficientMeasurements, factors_from_order, recover_order
from submissions.team3.tier09 import solution as tier09

check = import_module("common.check")


def locked_fixture(modulus, width, plaintext):
    key, exponent = 2, 5
    bits = format(key, f"0{width}b")
    payload = plaintext.encode("utf-8")
    return {
        "public_parameters": {
            "N": modulus, "e": exponent, "wrapped_key": pow(key, exponent, modulus),
            "key_width_bits": width,
        },
        "ciphertext_hex": xor_bytes(payload, keystream(bits, len(payload))).hex(),
    }


class ShorIntegrationTests(unittest.TestCase):
    def check_pipeline(self, module, tier, modulus, width, phase_bits):
        text = f"QC-{tier:02d}: synthetic RSA fixture"
        locked = locked_fixture(modulus, width, text)
        build = partial(module.build_circuit, phase_bits=phase_bits, work_bits=width)
        with (
            patch.multiple(module, PHASE_BITS=phase_bits, WORK_BITS=width),
            patch.object(module, "build_circuit", side_effect=build),
            patch.object(module, "_public_parameters", return_value=locked["public_parameters"]),
            patch.object(module, "load_locked", return_value=locked),
            patch.object(check, "load_hashes", return_value={tier: hash_line(text)}),
        ):
            self.assertEqual(module.solve(), text)

    def test_tier08_aer_to_rsa_and_hash(self):
        self.check_pipeline(tier08, 8, modulus=15, width=4, phase_bits=8)

    def test_tier09_aer_to_rsa_and_hash(self):
        self.check_pipeline(tier09, 9, modulus=21, width=5, phase_bits=9)

    def test_rejects_missing_period_evidence_and_nonminimal_period(self):
        with self.assertRaises(InsufficientMeasurements):
            recover_order({"00000000": 64}, 2, 15, phase_bits=8)
        with self.assertRaisesRegex(ValueError, "not minimal"):
            factors_from_order(2, 15, 8)

    def test_rejects_wrong_full_prefix_and_wrong_hash(self):
        for tier, module, modulus, width, factors in (
            (8, tier08, 15, 4, (3, 5)), (9, tier09, 21, 5, (3, 7)),
        ):
            for text, expected_hash_text, message in (
                (f"QC-{tier:02d}:missing space", f"QC-{tier:02d}:missing space", "prefix"),
                (f"QC-{tier:02d}: synthetic text", f"QC-{tier:02d}: different text", "hash"),
            ):
                with (
                    self.subTest(tier=tier, gate=message),
                    patch.object(module, "recover_factors", return_value=factors),
                    patch.object(module, "load_locked", return_value=locked_fixture(modulus, width, text)),
                    patch.object(check, "load_hashes", return_value={tier: hash_line(expected_hash_text)}),
                    self.assertRaisesRegex(RuntimeError, message),
                ):
                    module.solve()


if __name__ == "__main__":
    unittest.main()
