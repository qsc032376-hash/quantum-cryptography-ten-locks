"""Reproduce v2 team-module isolation without running a challenge circuit."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

# The two copied teams are byte-identical. The sentinel simulates a different
# first team's public modular-inverse implementation without editing any file.
COLLISION = r'''
import importlib, sys
from pathlib import Path
base=Path(sys.argv[1]); first=sys.argv[2]; second=sys.argv[3]
sys.path.insert(0,str(base))
a=importlib.import_module(first+'.dh_classical')
assert Path(sys.modules['rsa_classical'].__file__).resolve().is_relative_to((base/first).resolve())
assert Path(sys.modules['classical_keystream'].__file__).resolve().is_relative_to((base/first).resolve())
original=sys.modules['rsa_classical'].mod_inverse
assert original(3,5)==2
def sentinel(*args): return 0
sys.modules['rsa_classical'].mod_inverse=sentinel
b=importlib.import_module(second+'.dh_classical')
readout=importlib.import_module(second+'.tier10.readout')
assert Path(b.__file__).resolve().is_relative_to((base/second).resolve())
assert readout.dh_classical is b
team_rsa=importlib.import_module(second+'.rsa_classical')
assert Path(team_rsa.__file__).resolve().is_relative_to((base/second).resolve())
assert team_rsa.decrypt_key_bits is sys.modules['classical_keystream'].decrypt_key_bits
for tier in ('tier08', 'tier09'):
    mod=importlib.import_module(second+'.'+tier+'.solution')
    assert Path(mod.__file__).resolve().is_relative_to((base/second).resolve())
    assert getattr(mod, 'decrypt_tier'+str(int(tier[4:]))).__module__ == second+'.rsa_classical'
assert b.mod_inverse is sentinel and b.mod_inverse(3,5)==0
assert Path(sys.modules['rsa_classical'].__file__).resolve().is_relative_to((base/first).resolve())
assert Path(sys.modules['classical_keystream'].__file__).resolve().is_relative_to((base/first).resolve())
'''

FRESH_CHECKER = r'''
import importlib, sys
from pathlib import Path
from tools.check_submission import load_solution
base=Path(sys.argv[1]); team=base/'team_beta'; sys.path.insert(0,str(base))
path=team/'tier10'/'solution.py'; sys.path.insert(0,str(path.parent))
solution=load_solution(path)
dh=importlib.import_module('team_beta.dh_classical')
assert callable(solution.solve) and dh.mod_inverse(3,5)==2
for name in ('rsa_classical','classical_keystream'):
    assert Path(sys.modules[name].__file__).resolve().is_relative_to(team.resolve())
assert Path(importlib.import_module('team_beta.tier10.readout').__file__).resolve().is_relative_to(team.resolve())
'''


class TeamIsolationAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='v2_isolation_')
        cls.base = Path(cls.temp.name)
        for name in ('team_alpha', 'team_beta'):
            shutil.copytree(ROOT/'submissions/team3', cls.base/name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.venv'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, code, *args):
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.base), *args],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_preloaded_other_team_is_reused_in_both_orders(self):
        for first, second in (('team_alpha', 'team_beta'), ('team_beta', 'team_alpha')):
            with self.subTest(first=first):
                self.run_case(COLLISION, first, second)

    def test_fresh_checker_style_worker_loads_its_own_team(self):
        self.run_case(FRESH_CHECKER)


if __name__ == '__main__':
    unittest.main()
