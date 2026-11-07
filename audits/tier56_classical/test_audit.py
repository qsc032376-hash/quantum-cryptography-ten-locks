"""Synthetic, independent regression checks for the Tier 5/6 adapter."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "submissions" / "team3" / "toy_cipher_classical.py"
SPEC = importlib.util.spec_from_file_location("audited_toy_cipher", ADAPTER)
CLASSICAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLASSICAL)
from common.toy_cipher import ToyCipher


KEY5 = 0x105
KEY6 = 0x2105
TEXT5 = "QC-05: synthetic café"
TEXT6 = "QC-06: synthetic fixture"
BYTE_VECTOR = bytes.fromhex("514300ff10557e80")
KNOWN_VECTORS = {
    5: (10, KEY5, "7c2e3584c1115d68"),
    6: (14, KEY6, "c821182f8f25a9c9"),
}


class KeyAndCipherTests(unittest.TestCase):
    def test_widths_ranges_and_boundaries(self):
        for tier, width in [(5, 10), (6, 14)]:
            with self.subTest(tier=tier):
                self.assertEqual(CLASSICAL.width_for(tier), width)
                for key in (0, 1, 1 << (width - 1), (1 << width) - 1):
                    self.assertEqual(CLASSICAL.key_from_int(key, width), key)
                for invalid in (-1, 1 << width, True, "1", 1.0):
                    with self.assertRaises(CLASSICAL.KeyFormatError):
                        CLASSICAL.key_from_int(invalid, width)

    def test_bit_order_and_leading_zeroes(self):
        for width, key in [(10, KEY5), (14, KEY6)]:
            for value in (0, 1, key, 1 << (width - 1)):
                with self.subTest(width=width, value=value):
                    text = format(value, f"0{width}b")
                    bits = [int(bool(value & (1 << j))) for j in range(width)]
                    self.assertEqual(CLASSICAL.key_from_bitstring(text, width), value)
                    self.assertEqual(CLASSICAL.key_from_bits(bits, width), value)

    def test_bad_bit_forms(self):
        for width in (10, 14):
            for text in ("1", "0" * (width + 1), "0" * (width - 1) + "x", 1):
                with self.assertRaises(CLASSICAL.KeyFormatError):
                    CLASSICAL.key_from_bitstring(text, width)
            for bits in ([1], [0] * (width - 1) + [2], [0] * (width - 1) + [1.0]):
                with self.assertRaises(CLASSICAL.KeyFormatError):
                    CLASSICAL.key_from_bits(bits, width)
        with self.assertRaises(CLASSICAL.ToyCipherError):
            CLASSICAL.key_from_int(1, 11)

    def test_float_key_width_rejected_by_adapter(self):
        # P3: float equality can pass the width membership test.
        with self.assertRaises(CLASSICAL.ToyCipherError):
            CLASSICAL.key_from_int(1, 10.0)

    def test_known_answer_and_binary_roundtrip(self):
        # Constants cross-checked from the public mask, substitution and
        # permutation definitions independently of the Python adapter.
        for tier, (width, key, expected_hex) in KNOWN_VECTORS.items():
            with self.subTest(tier=tier):
                cipher = ToyCipher(key, width)
                self.assertEqual(cipher.encrypt(BYTE_VECTOR).hex(), expected_hex)
                self.assertEqual(CLASSICAL.decrypt_bytes(tier, key, expected_hex), BYTE_VECTOR)
                data = bytes(range(256))
                self.assertEqual(CLASSICAL.decrypt_bytes(tier, key, cipher.encrypt(data).hex()), data)

    def test_bad_ciphertext_and_invalid_utf8(self):
        self.assertEqual(CLASSICAL.ciphertext_to_bytes(" 0a \t FF\n"), b"\x0a\xff")
        for invalid in ("", " \t", "a", "0z", b"aa", None):
            with self.assertRaises(CLASSICAL.CiphertextError):
                CLASSICAL.decrypt_bytes(5, KEY5, invalid)
        encoded = ToyCipher(KEY5, 10).encrypt(b"QC\xff").hex()
        with self.assertRaises(CLASSICAL.DecodeError):
            CLASSICAL.decrypt_tier5(KEY5, encoded)


class FilterTests(unittest.TestCase):
    def test_tier5_checks_qc_and_decrypts_utf8(self):
        cipher = ToyCipher(KEY5, 10)
        ciphertext = cipher.encrypt(TEXT5.encode()).hex()
        self.assertTrue(CLASSICAL.matches_prefix(KEY5, ciphertext))
        self.assertEqual(CLASSICAL.decrypt_tier5(KEY5, ciphertext), TEXT5)
        self.assertEqual(CLASSICAL.filter_candidates(5, [-1, KEY5, True], ciphertext), [TEXT5])
        q_only = cipher.encrypt(b"QX: fixture").hex()
        self.assertFalse(CLASSICAL.matches_prefix(KEY5, q_only, b"QC", tier=5))
        self.assertTrue(CLASSICAL.matches_prefix(KEY5, q_only, b"Q", tier=5))

    def test_tier6_uses_byte_sum_and_rejects_wrong_marked_candidate(self):
        plaintext = TEXT6.encode()
        ciphertext = ToyCipher(KEY6, 14).encrypt(plaintext).hex()
        self.assertEqual(CLASSICAL.checksum(bytes([255, 254, 3])), 0)
        self.assertEqual(CLASSICAL.checksum("é".encode()), 108)
        wrong_key = 100  # Also decrypts this synthetic first byte to Q.
        self.assertTrue(CLASSICAL.matches_prefix(wrong_key, ciphertext, b"Q", tier=6))
        with self.assertRaises(CLASSICAL.ChecksumError):
            CLASSICAL.decrypt_tier6(wrong_key, ciphertext, 131)
        self.assertEqual(CLASSICAL.decrypt_tier6(KEY6, ciphertext, 131), TEXT6)
        self.assertEqual(CLASSICAL.filter_candidates(6, [wrong_key, KEY6], ciphertext, 131), [TEXT6])

    def test_decode_failure_is_per_candidate(self):
        raw = b"Q\xff"
        ciphertext = ToyCipher(KEY6, 14).encrypt(raw).hex()
        with self.assertRaises(CLASSICAL.DecodeError):
            CLASSICAL.decrypt_tier6(KEY6, ciphertext, 80)
        self.assertEqual(CLASSICAL.filter_candidates(6, [KEY6], ciphertext, 80), [])

    def test_checksum_error_text_does_not_expose_key(self):
        ciphertext = ToyCipher(KEY6, 14).encrypt(TEXT6.encode()).hex()
        try:
            CLASSICAL.decrypt_tier6(KEY6, ciphertext, 132)
        except CLASSICAL.ChecksumError as error:
            self.assertEqual(error.key, KEY6)
            self.assertEqual((error.expected, error.actual), (132, 131))
            rendered = (str(error), repr(error), "".join(traceback.format_exception_only(error)))
            for value in rendered:
                self.assertNotIn(str(KEY6), value)
                self.assertNotIn(hex(KEY6), value)
                self.assertNotIn(format(KEY6, "014b"), value)
        else:
            self.fail("Expected checksum mismatch on synthetic fixture")

    def test_filter_surfaces_malformed_global_inputs_before_iteration(self):
        def untouched():
            self.fail("Caller input should be validated before candidates are consumed")
            yield KEY6
        for tier, ciphertext, expected in [(4, "aa", 10), (6, "aa", None), (5, "zz", None)]:
            with self.subTest(tier=tier, ciphertext=ciphertext, expected=expected):
                with self.assertRaises(CLASSICAL.ToyCipherError):
                    CLASSICAL.filter_candidates(tier, untouched(), ciphertext, expected)

    def test_nonempty_filter_surfaces_bad_checksum(self):
        for invalid in (-1, 256, True, "12", 12.0):
            with self.subTest(invalid=invalid):
                with self.assertRaises(CLASSICAL.ToyCipherError):
                    CLASSICAL.filter_candidates(6, [KEY6], "aa", invalid)

    def test_empty_filter_surfaces_bad_checksum(self):
        # P2: an empty measurements batch must not hide a caller error.
        invalid_values_silently_accepted = []
        for invalid in (-1, 256, True, "12", 12.0):
            try:
                CLASSICAL.filter_candidates(6, [], "aa", invalid)
            except CLASSICAL.ToyCipherError:
                continue
            invalid_values_silently_accepted.append(invalid)
        self.assertEqual(invalid_values_silently_accepted, [])

    def test_unexpected_internal_exception_is_not_swallowed(self):
        with patch.object(CLASSICAL, "decrypt_tier6", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                CLASSICAL.filter_candidates(6, [KEY6], "aa", 1)

    def test_filter_is_not_a_standalone_acceptance_check(self):
        for tier, width, key, prefix in [(5, 10, KEY5, b"QC"), (6, 14, KEY6, b"Q")]:
            with self.subTest(tier=tier):
                plaintext = b"XX: unmarked fixture"
                ciphertext = ToyCipher(key, width).encrypt(plaintext).hex()
                self.assertFalse(CLASSICAL.matches_prefix(key, ciphertext, prefix, tier))
                expected = sum(plaintext) % 256 if tier == 6 else None
                # Records the documented dependency on upstream prefix validation.
                self.assertEqual(CLASSICAL.filter_candidates(tier, [key], ciphertext, expected),
                                 [plaintext.decode()])


CHECKER_PROBE = """
import importlib.util
import json
import os
from pathlib import Path
import sys

root = Path(sys.argv[1])
solution = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("official_checker", root / "tools/check_submission.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
# Same search paths and cwd as worker_solve, without initializing Aer.
sys.path.insert(0, str(checker.REPO_ROOT))
sys.path.insert(0, str(solution.parent))
os.chdir(checker.REPO_ROOT)
try:
    module = checker.load_solution(solution)
except ImportError as error:
    print(json.dumps({"import_error": str(error)}))
else:
    print(json.dumps({"value": module.VALUE}))
"""


@unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML required by official Checker loader")
class CheckerImportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tier56-audit-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.foreign_cwd = self.root / "foreign"
        self.foreign_cwd.mkdir()
        shutil.copytree(ROOT / "common", self.root / "common", ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "tools").mkdir()
        shutil.copy2(ROOT / "tools/check_submission.py", self.root / "tools/check_submission.py")

    def probe(self, team_name, tier, statement):
        team = self.root / "submissions" / team_name
        solution = team / f"tier{tier:02d}" / "solution.py"
        solution.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ADAPTER, team / ADAPTER.name)
        solution.write_text(statement + f"\nVALUE = width_for({tier})\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", CHECKER_PROBE, str(self.root), str(solution)],
            cwd=self.foreign_cwd, capture_output=True, text=True, timeout=15, check=True,
        )
        return json.loads(result.stdout)

    def test_team_root_import_resolves_after_team_directory_rename(self):
        dynamic_import = "\n".join([
            "import sys",
            "from pathlib import Path",
            "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))",
            "from toy_cipher_classical import width_for",
        ])
        for team in ("team3", "renamed-team"):
            for tier, width in ((5, 10), (6, 14)):
                with self.subTest(team=team, tier=tier):
                    self.assertEqual(self.probe(team, tier, dynamic_import), {"value": width})

    def test_checker_does_not_add_team_root_to_module_search_path(self):
        for tier in (5, 6):
            with self.subTest(tier=tier):
                result = self.probe("team3", tier, "from toy_cipher_classical import width_for")
                self.assertIn("toy_cipher_classical", result["import_error"])

    def test_hard_coded_team_name_breaks_after_rename(self):
        static_import = "from submissions.team3.toy_cipher_classical import width_for"
        self.assertEqual(self.probe("team3", 5, static_import), {"value": 10})
        shutil.rmtree(self.root / "submissions/team3")
        result = self.probe("renamed-team", 5, static_import)
        self.assertIn("submissions.team3", result["import_error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
