"""Exercise the Tier 5 handoff with synthetic measurements and ciphertext."""

from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.toy_cipher import ToyCipher
from tools.check_submission import load_solution


class Tier05IntegrationTests(unittest.TestCase):
    def setUp(self):
        original = ROOT / "submissions/team3"
        temp = TemporaryDirectory(prefix="renamed-tier05-")
        self.addCleanup(temp.cleanup)
        renamed = Path(temp.name) / "submissions" / "renamed-team"
        shutil.copytree(original / "tier05", renamed / "tier05",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(original / "toy_cipher_classical.py", renamed)
        self.solution = load_solution(renamed / "tier05" / "solution.py")

    def decrypt_synthetic(self, text):
        # This fixture is not the challenge input. A reversal would turn 5
        # into a different key and fail the synthetic decrypt.
        ciphertext = ToyCipher(5, 10).encrypt(text.encode()).hex()
        with (patch.object(self.solution, "recover_key",
                           side_effect=lambda: self.solution.measurement_to_key("0000000101")),
              patch.object(self.solution, "load_locked",
                           return_value={"ciphertext_hex": ciphertext})):
            return self.solution.solve()

    def test_fixed_width_integer_reaches_real_decryptor_in_renamed_team(self):
        text = "QC-05: synthetic fixture"
        self.assertEqual(self.decrypt_synthetic(text), text)

    def test_full_prefix_including_space_is_required_after_decryption(self):
        for text in ("QC-05:no space", "QC-06: wrong tier", "XX-05: wrong prefix"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "required prefix"):
                self.decrypt_synthetic(text)


if __name__ == "__main__":
    unittest.main()
