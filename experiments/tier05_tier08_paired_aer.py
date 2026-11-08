"""Bounded real-Aer seed runs; record only safe aggregate correctness data."""

import argparse
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from qiskit import transpile
import qiskit
import qiskit_aer
from qiskit_aer import AerSimulator


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "submissions" / "team3")]

from common import is_correct, load_locked  # noqa: E402
from submissions.team3.tier05 import solution as tier05  # noqa: E402
from submissions.team3.tier08 import solution as tier08  # noqa: E402
from submissions.team3.toy_cipher_classical import decrypt_tier5  # noqa: E402


BASELINE = "41c7c6775b8fc499c2acdd878b4829bd17e1210d"
BASIS = ["rz", "sx", "x", "cx"]


def baseline_module(source, name, folder):
    path = Path(folder) / (name.rsplit(".", 1)[-1] + ".py")
    path.write_bytes(subprocess.check_output(["git", "show", f"{BASELINE}:{source}"], cwd=ROOT))
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(tier, variant, folder):
    if tier == 5:
        locked = load_locked(5)
        ciphertext = bytes.fromhex(locked["ciphertext_hex"])
        prefix = locked["public_parameters"]["known_prefix"].encode("ascii")
        if variant == "baseline":
            old_oracle = baseline_module("submissions/team3/tier05/oracle.py",
                                         "submissions.team3.tier05.baseline_oracle", folder)
            with patch.object(tier05, "oracle", old_oracle):
                circuit = tier05.build_circuit(ciphertext=ciphertext)
        else:
            circuit = tier05.build_circuit(ciphertext=ciphertext)
        return circuit, locked, prefix
    locked = load_locked(8)
    if variant == "baseline":
        module = baseline_module("submissions/team3/tier08/solution.py",
                                 "submissions.team3.tier08.baseline_solution", folder)
    else:
        module = tier08
    circuit = module.build_circuit(modulus=locked["public_parameters"]["N"])
    return circuit, locked, None


def valid_result(tier, counts, locked, prefix):
    if tier == 5:
        ciphertext = bytes.fromhex(locked["ciphertext_hex"])
        valid = []
        for bits, frequency in counts.items():
            key = tier05.measurement_to_key(bits)
            if tier05.validate_candidate(key, ciphertext, prefix):
                valid.append((key, frequency))
        if len(valid) != 1 or valid[0][1] <= tier05.SHOTS / 2:
            return False
        return is_correct(5, decrypt_tier5(valid[0][0], locked["ciphertext_hex"]))
    try:
        order, _ = tier08.recover_order(counts, tier08.BASE,
                                        locked["public_parameters"]["N"], tier08.PHASE_BITS)
        p, q = tier08.factors_from_order(tier08.BASE, locked["public_parameters"]["N"], order)
        text = tier08.decrypt_tier8(p, q, locked["public_parameters"], locked["ciphertext_hex"])
        return text.startswith("QC-08: ") and is_correct(8, text)
    except (ValueError, ArithmeticError, tier08.InsufficientMeasurements):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", type=int, choices=(5, 8), required=True)
    parser.add_argument("--variant", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if len(args.seeds) != len(set(args.seeds)) or not args.seeds:
        parser.error("Provide distinct simulator seeds")
    with TemporaryDirectory(prefix="tier58-aer-") as folder:
        started = time.perf_counter()
        circuit, locked, prefix = prepare(args.tier, args.variant, folder)
        build_seconds = time.perf_counter() - started
        started = time.perf_counter()
        compiled = transpile(circuit, basis_gates=BASIS, coupling_map=None,
                             initial_layout=None, optimization_level=1,
                             seed_transpiler=12345, num_processes=1)
        compilation_seconds = time.perf_counter() - started
        simulator = AerSimulator(method="statevector", max_memory_mb=512,
                                 max_parallel_threads=2)
        shots = tier05.SHOTS if args.tier == 5 else tier08.SHOTS_PER_BATCH
        records = []
        for seed in args.seeds:
            started = time.perf_counter()
            try:
                aer_started = time.perf_counter()
                result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
                counts = {bits: int(count) for bits, count in result.get_counts().items()}
                aer_seconds = time.perf_counter() - aer_started
                recovery_started = time.perf_counter()
                passed = bool(result.success and sum(counts.values()) == shots
                              and valid_result(args.tier, counts, locked, prefix))
                recovery_seconds = time.perf_counter() - recovery_started
                error_type = None
            except Exception as error:
                passed, error_type = False, type(error).__name__
                aer_seconds = recovery_seconds = None
            seconds = time.perf_counter() - started
            records.append({"seed": seed, "shots": shots, "pass": passed,
                            "aer_seconds": None if aer_seconds is None else round(aer_seconds, 6),
                            "recovery_seconds": None if recovery_seconds is None else round(recovery_seconds, 6),
                            "aer_and_recovery_seconds": round(seconds, 6),
                            "error_type": error_type})
            print(f"tier={args.tier} variant={args.variant} seed={seed} pass={passed} "
                  f"seconds={seconds:.3f}", flush=True)
        payload = {
            "tier": args.tier, "variant": args.variant, "baseline_sha": BASELINE,
            "qiskit": qiskit.__version__, "aer": qiskit_aer.__version__,
            "platform": platform.platform(), "python": platform.python_version(),
            "configuration": {"basis": BASIS, "coupling_map": None,
                              "optimization_level": 1, "seed_transpiler": 12345,
                              "max_memory_mb": 512, "max_parallel_threads": 2},
            "build_seconds": round(build_seconds, 6),
            "compilation_seconds": round(compilation_seconds, 6),
            "peak_rss_raw": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "peak_rss_unit": "bytes" if sys.platform == "darwin" else "KiB",
            "records": records,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        if not all(row["pass"] for row in records):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
