"""Run from the validation checkout. See docs/TESTING_REPORT.md for worktree setup."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("CLASSICAL_WORKTREE", ROOT.parent / "classical-d65efdb")).resolve()
SHA = "d65efdb54d213ebd7b7fe39cd4235dce053f5604"
TEAM = Path("submissions/team3")
FILES = (TEAM / "tier01/classical.py", TEAM / "classical_keystream.py")
MESSAGE = "synthetic UTF-8: 测试 / " * 4


def setUpModule():
    if not SOURCE.is_dir():
        raise unittest.SkipTest(f"Missing detached source worktree: {SOURCE}")
    def git(*args):
        return subprocess.check_output(["git", "-C", SOURCE, *args], text=True).strip()
    if git("rev-parse", "HEAD") != SHA or git("status", "--porcelain", "--", "common", *FILES):
        raise RuntimeError("Expected clean classical modules and common/ at " + SHA)
    sys.path.insert(0, str(SOURCE))
    global bv, stream
    from submissions.team3.tier01 import classical as bv
    from submissions.team3 import classical_keystream as stream
    for module, path in zip((bv, stream), FILES, strict=True):
        if Path(module.__file__).resolve() != SOURCE / path:
            raise RuntimeError(f"Unexpected module origin: {module.__file__}")


def tearDownModule():
    sys.path.remove(str(SOURCE))


def stream_fixture(bits, data):
    # Independent encryption fixture: ASCII bits, four-byte BE counter starting at 0.
    blocks = (hashlib.sha256(bits.encode("ascii") + i.to_bytes(4, "big")).digest()
              for i in range((len(data) + 31) // 32))
    return bytes(x ^ y for x, y in zip(data, b"".join(blocks))).hex()


class Tier1(unittest.TestCase):
    def test_big_endian(self):
        for key, expected in [(0, "000000"), (1, "000001"), (0x1234, "001234"),
                              (0x123456, "123456"), (0xffffff, "ffffff")]:
            self.assertEqual(bv.key_to_bytes(key).hex(), expected)

    def test_measurement_and_repeating_xor(self):
        key = int("000000000100000000000001", 2)  # c14 and c0 set
        mask = bytes.fromhex("004001")
        data = MESSAGE.encode()
        cipher = bytes(b ^ mask[i % 3] for i, b in enumerate(data))
        self.assertEqual(bv.decrypt_tier1(key, cipher.hex(" ")), MESSAGE)

    def test_invalid_keys(self):
        for key in (-1, 1 << 24, True, "1", 1.5):
            with self.subTest(key=key), self.assertRaises(bv.Tier1KeyError):
                bv.decrypt_tier1(key, "00")

    def test_invalid_hex(self):
        for value in (None, "", "  ", "f", "zz"):
            with self.subTest(value=value), self.assertRaises(bv.Tier1CiphertextError):
                bv.decrypt_tier1(1, value)

    def test_invalid_utf8(self):
        with self.assertRaises(bv.Tier1DecodeError):
            bv.decrypt_tier1(1, "ff")


class Tier3(unittest.TestCase):
    def test_every_oracle_position(self):
        for balanced in range(24):
            flags = [i == balanced for i in range(24)]
            self.assertEqual(stream.key_bits_from_flags(flags),
                             "0" * balanced + "1" + "0" * (23 - balanced))

    def test_mixed_flags_round_trip(self):
        balanced = {2, 8, 19, 23}
        cipher = stream_fixture("001000001000000000010001", MESSAGE.encode())
        self.assertEqual(stream.decrypt_tier3([int(i in balanced) for i in range(24)], cipher), MESSAGE)

    def test_invalid_flags(self):
        for flags in ([0] * 23, [0] * 25, [0] * 23 + [2], [0] * 23 + ["1"]):
            with self.subTest(flags=flags), self.assertRaises(stream.KeyBitsError):
                stream.decrypt_tier3(flags, "00")


class Tier4(unittest.TestCase):
    def test_every_qubit_position(self):
        for j in range(10):
            self.assertEqual(stream.key_bits_from_int(1 << j, 10), "0" * (9-j) + "1" + "0" * j)
        self.assertEqual(stream.key_bits_from_int(1023, 10), "1" * 10)

    def test_multiblock_round_trip(self):
        cipher = stream_fixture("0001000010", MESSAGE.encode())
        self.assertEqual(stream.decrypt_tier4((1 << 6) | (1 << 1), cipher), MESSAGE)

    def test_invalid_integer(self):
        for s in (-1, 1024, True, "0000000001"):
            with self.subTest(s=s), self.assertRaises(stream.KeyBitsError):
                stream.decrypt_tier4(s, "00")

    def test_simon_hidden_string_must_be_nonzero(self):
        cipher = stream_fixture("0000000000", MESSAGE.encode())
        with self.assertRaises(stream.KeyBitsError):
            stream.decrypt_tier4(0, cipher)


class Shared(unittest.TestCase):
    def test_key_strings(self):
        for tier, width in ((3, 24), (4, 10)):
            for bits in (0, "1" * (width - 1), "0" * (width - 1) + "2"):
                with self.subTest(tier=tier, bits=bits), self.assertRaises(stream.KeyBitsError):
                    stream.decrypt(tier, bits, "00")

    def test_bad_hex_and_utf8(self):
        for tier, width in ((3, 24), (4, 10)):
            bits = "0" * (width-1) + "1"
            for value in (None, "", "f", "zz"):
                with self.subTest(tier=tier, value=value), self.assertRaises(stream.CiphertextError):
                    stream.decrypt(tier, bits, value)
            with self.assertRaises(stream.DecodeError):
                stream.decrypt(tier, bits, stream_fixture(bits, b"\xff"))

    def test_repository_root_imports(self):
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        subprocess.run([sys.executable, "-c",
                        "from submissions.team3.tier01.classical import decrypt_tier1; "
                        "from submissions.team3.classical_keystream import decrypt_tier3, decrypt_tier4"],
                       cwd=SOURCE, env=env, check=True, timeout=30)

    def test_clean_checker_worker(self):
        # Only official dependencies and the two deliverable team files are staged.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / "common", root / "common", ignore=shutil.ignore_patterns("__pycache__"))
            checker = root / "tools/check_submission.py"
            checker.parent.mkdir()
            shutil.copy2(ROOT / "tools/check_submission.py", checker)
            for path in FILES:
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE / path, root / path)
            probes = {
                1: "from classical import decrypt_tier1\n"
                   "def solve(): return decrypt_tier1(1, '4f4b')",
                3: "from submissions.team3.classical_keystream import decrypt_tier3\n"
                   f"def solve(): return decrypt_tier3([0]*23+[1], '{stream_fixture('0'*23+'1', b'OK')}')",
                4: "from submissions.team3.classical_keystream import decrypt_tier4\n"
                   f"def solve(): return decrypt_tier4(1, '{stream_fixture('0'*9+'1', b'OK')}')",
            }
            for tier, probe in probes.items():
                with self.subTest(tier=tier):
                    solution = root / TEAM / f"tier{tier:02d}/solution.py"
                    solution.parent.mkdir(exist_ok=True)
                    solution.write_text(probe, encoding="utf-8")
                    prefix = root / f"out{tier}"
                    subprocess.run([sys.executable, "-I", checker, "--_solve", str(tier), solution, prefix],
                                   cwd=root, check=True, timeout=60)
                    result = json.loads(prefix.with_suffix(".json").read_text())
                    self.assertIsNone(result["error"])
                    self.assertEqual(result["answer_hash"], hashlib.sha256(b"OK").hexdigest())
                    self.assertEqual(result["circuits_executed"], 0)


if __name__ == "__main__":
    unittest.main()
