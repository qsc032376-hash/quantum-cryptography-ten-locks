"""Replay the two pinned research operator audits against the installed team modules."""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

T5 = "97fcc0c7d6dec3b7385dc237d47d89d4d6ffd15c"
T8 = "8b18d3d18a6ee6b744e5ce60af13ed1c4f259c9d"
BASE = "aee41fb328027f8927a55d65c68e8a3e30332697"


def extract(ref, path, dest):
    dest.write_bytes(subprocess.check_output(["git", "show", f"{ref}:{path}"]))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(root, output):
    sys.path[:0] = [str(root), str(root / "submissions")]
    from submissions.team3.tier05 import oracle, solution
    from submissions.team3.tier08 import modular, solution as eight
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for file in ("search.py", "verify.py", "candidate.json"):
            extract(T5, "research/tier05_extreme/"+file, tmp/file)
        extract(BASE, "submissions/team3/tier05/oracle.py", tmp/"original.py")
        sys.path.insert(0,str(tmp))
        check = load("verify5", tmp/"verify.py")
        original = load("v62_stage5", tmp/"original.py")
        check.OUT = tmp
        check.oracle = original
        check.fused_oracle = lambda ciphertext, *args: oracle.build_phase_oracle(ciphertext)
        check.transition = oracle.transition
        check.build_config = lambda config: solution.build_circuit()
        # verify.py also needs the unchanged baseline builder for its full-state test.
        class Baseline:
            _public_inputs = staticmethod(solution._public_inputs)
            count_oracle_calls = staticmethod(solution.count_oracle_calls)
            @staticmethod
            def build_circuit():
                from unittest.mock import patch
                with patch.object(solution, "oracle", original):
                    return solution.build_circuit()
        check.solution = Baseline
        assert solution.SHOTS == 128 and solution.ITERATIONS == 25
        check.main()
        (output/"tier05-equivalence.json").write_bytes((tmp/"equivalence.json").read_bytes())
        extract(T8, "research/tier08_extreme/verify.py", tmp/"verify8.py")
        verify8 = load("verify8",tmp/"verify8.py")
        blocks = [verify8.operator_check(modular.build_controlled_multiplier(d,35,6),d,35,6)
                  for d in verify8.PUBLIC_MULTIPLIERS]
        result = dict(blocks=blocks,structure=verify8.order_finding_structure(eight),
                      fourier=verify8.synthetic_fourier_state(eight))
        (output/"tier08-equivalence.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    args=p.parse_args()
    run(args.root.resolve(),Path(__file__).resolve().parent)
