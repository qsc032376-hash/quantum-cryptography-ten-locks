"""Read the pinned classical adapter and test it with synthetic data only."""

from hashlib import sha256
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CLASSICAL_REV = "6c9ce26854c325907b65e491620693a1f605e71f"


class Tier07PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = TemporaryDirectory(prefix="tier07-classical-")
        cls.addClassCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        team = repo / "submissions" / "renamed-team"
        team.mkdir(parents=True)
        shutil.copytree(ROOT / "common", repo / "common",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "submissions/team3/classical_keystream.py", team)
        adapter = team / "tier07_classical.py"
        try:
            source = subprocess.check_output(
                ["git", "show", f"{CLASSICAL_REV}:submissions/team3/tier07_classical.py"],
                cwd=ROOT,
            )
        except subprocess.CalledProcessError as error:
            raise RuntimeError("Fetch origin feature/classical-implementation before running this test") from error
        adapter.write_bytes(source)
        spec = spec_from_file_location("audited_tier07_classical", adapter)
        cls.classical = module_from_spec(spec)
        with patch.object(sys, "path", list(sys.path)):
            spec.loader.exec_module(cls.classical)
            cls.check = import_module("common.check")
            cls.crypto = import_module("common.crypto")

    def test_integer_boundaries_and_fixed_width(self):
        for key, encoded in ((0, "0" * 14), (1, "0" * 13 + "1"), (16383, "1" * 14)):
            with self.subTest(key=key):
                self.assertEqual(self.classical.key_from_int(key), key)
                self.assertEqual(self.classical.key_bits_for(key), encoded)
        for key in (-1, 16384, True, "1", 1.0):
            with self.subTest(key=key), self.assertRaises(self.classical.KeyBitsError):
                self.classical.key_from_int(key)

    def test_distinguishes_canonical_and_reversed_readout(self):
        # A synthetic asymmetric value exposes a reversal and preserves leading zeros.
        k = 0x129
        canonical = "00000100101001"
        wire_order = [int(bool(k & (1 << j))) for j in range(14)]
        self.assertEqual(self.classical.key_from_bitstring(canonical), k)
        self.assertEqual(self.classical.key_from_qubit_bits(wire_order), k)
        self.assertEqual(self.classical.key_from_reversed_register(canonical[::-1]), k)
        self.assertNotEqual(self.classical.key_from_bitstring(canonical[::-1]), k)
        self.assertEqual(self.classical.key_from_bitstring("1" + "0" * 13), 8192)

    def test_rejects_short_invalid_and_multi_register_counts(self):
        for bits in ("1", "0" * 15, "0" * 13 + "x", "000000 00000000", None):
            with self.subTest(bits=bits), self.assertRaises(self.classical.KeyBitsError):
                self.classical.key_from_bitstring(bits)

    def test_synthetic_ciphertext_and_official_hash_comparison(self):
        expected_text = "QC-07: synthetic phase fixture"
        payload = expected_text.encode()
        key, bits = 0x129, "00000100101001"
        stream = self.crypto.keystream(bits, len(payload))
        encrypted = bytes(x ^ y for x, y in zip(payload, stream)).hex()
        result = self.classical.decrypt(key, encrypted)
        self.assertEqual(result, expected_text)
        self.assertEqual(self.classical.decrypt_bitstring(bits, encrypted), expected_text)
        with patch.object(self.check, "load_hashes", return_value={7: sha256(payload).hexdigest()}):
            self.assertTrue(self.check.is_correct(7, result))
            self.assertFalse(self.check.is_correct(7, result + "!"))
        with self.assertRaises(self.classical.CiphertextError):
            self.classical.decrypt(key, "bad hex")


if __name__ == "__main__":
    unittest.main()
