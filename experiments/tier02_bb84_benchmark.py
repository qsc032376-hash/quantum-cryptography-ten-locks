"""Paired, fresh-process Tier 2 timing. Workers emit aggregate measurements only."""
import argparse
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tarfile
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEAM = "submissions/team3/tier02/solution.py"
BASE = "41c7c6775b8fc499c2acdd878b4829bd17e1210d"
DEFAULT_SEED = 20261107


def peak_memory():
    import psutil
    memory = psutil.Process().memory_info()
    if hasattr(memory, "peak_wset"):
        rss = memory.peak_wset
    else:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    return rss


def worker(seed, plain):
    sys.path.insert(0, str(Path.cwd()))
    from common import is_correct
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.jobs.aerjob import AerJob
    from tools.check_submission import load_solution

    module = load_solution(TEAM)
    module.BASIS_SEED = seed  # test-only override; the production default stays intact.
    helper = module.helper
    seconds = dict(build=0.0, transpile=0.0, aer=0.0, sift=0.0)
    builds, batches, stats = [], [], []
    # Warm up Aer in this process with unrelated public data, outside all timers.
    warm = QuantumCircuit(1, 1)
    warm.h(0)
    warm.measure(0, 0)
    AerSimulator().run(warm, shots=1, seed_simulator=19).result()
    if plain:
        start = time.perf_counter()
        answer = module.solve()
        elapsed = time.perf_counter() - start
        assert is_correct(2, answer)
        return dict(seed=seed, solve_seconds=elapsed, peak_rss_bytes=peak_memory(), hash_ok=True)
    build, compile_batch = module.build_circuit, helper.transpile
    aer_run, job_result, analyze = AerSimulator.run, AerJob.result, module.analyze_link

    def timed_build(basis):
        start = time.perf_counter()
        c = build(basis)
        seconds["build"] += time.perf_counter() - start
        builds.append(basis)
        return c

    def timed_compile(*args, **kwargs):
        start = time.perf_counter()
        result = compile_batch(*args, **kwargs)
        seconds["transpile"] += time.perf_counter() - start
        return result

    def timed_run(backend, circuits, *args, **kwargs):
        start = time.perf_counter()
        job = aer_run(backend, circuits, *args, **kwargs)
        batches.append((len(circuits), kwargs["shots"]))
        starts[id(job)] = start
        return job

    def timed_result(job, *args, **kwargs):
        result = job_result(job, *args, **kwargs)
        seconds["aer"] += time.perf_counter() - starts.pop(id(job))
        return result

    def timed_sift(*args):
        start = time.perf_counter()
        bits, report = analyze(*args)
        seconds["sift"] += time.perf_counter() - start
        stats.append([report[k] for k in ("check_samples", "check_errors", "retained_key_bits")])
        return bits, report

    starts = {}
    with (patch.object(module, "build_circuit", timed_build),
          patch.object(helper, "transpile", timed_compile),
          patch.object(AerSimulator, "run", timed_run),
          patch.object(AerJob, "result", timed_result),
          patch.object(module, "analyze_link", timed_sift)):
        start = time.perf_counter()
        ok = is_correct(2, module.solve())
        elapsed = time.perf_counter() - start
    assert ok and not starts and batches == [(1024, 1), (1024, 1)]
    assert len(helper.Channel.log) == 2048
    rng = random.Random(seed)
    for pos, (link, index, circ) in enumerate(helper.Channel.log):
        assert (link, index) == (helper.LINKS[pos // 1024], pos % 1024)
        names = [op.operation.name for op in circ.data]
        assert names == (["h", "measure"] if rng.getrandbits(1) else ["measure"])
    rss = peak_memory()
    return dict(seed=seed, seconds=seconds, solve_seconds=elapsed, peak_rss_bytes=rss,
                builds=len(builds), aggregate_checks=stats, hash_ok=ok)


def snapshot(ref, folder):
    paths = ["common", "tools", "tier02", "hashes.txt", TEAM]
    data = subprocess.check_output(["git", "-C", ROOT, "archive", "--format=tar", ref, *paths])
    with tarfile.open(fileobj=io.BytesIO(data)) as arc:
        arc.extractall(folder, filter="data")


def compare(candidate, out, plain):
    env = dict(os.environ, OMP_NUM_THREADS="2", QISKIT_PARALLEL="FALSE",
               PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    records = []
    with tempfile.TemporaryDirectory() as tmp:
        trees = {}
        for name, ref in [("baseline", BASE), ("candidate", candidate)]:
            trees[name] = Path(tmp)/name
            trees[name].mkdir()
            snapshot(ref, trees[name])
        # One discarded pair, then 16 alternating AB/BA pairs at the production
        # basis seed. Eight more paired basis seeds separately test the protocol.
        trials = [("warmup", DEFAULT_SEED)] + [("timing", DEFAULT_SEED)] * 16
        if not plain:
            trials += [("protocol", s) for s in range(300, 308)]
        for pair, (kind, seed) in enumerate(trials):
            sides = ["baseline", "candidate"] if pair % 2 == 0 else ["candidate", "baseline"]
            matches = []
            for side in sides:
                command = [sys.executable, __file__, "--worker", str(seed)]
                if plain:
                    command.append("--plain")
                result = subprocess.run(command,
                                        cwd=trees[side], env=env, capture_output=True, timeout=90, check=True)
                row = json.loads(result.stdout)
                matches.append(row.get("aggregate_checks"))
                row.update(side=side, pair=pair, kind=kind)
                records.append(row)
            assert matches[0] == matches[1]
            print(kind, pair, "PASS", flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(baseline=BASE, candidate=candidate, uninstrumented=plain, runs=records), indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=int)
    parser.add_argument("--plain", action="store_true", help="time solve with no instrumentation")
    parser.add_argument("--candidate")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.worker is not None:
        print(json.dumps(worker(args.worker, args.plain)))
    elif args.candidate and args.out:
        compare(args.candidate, args.out, args.plain)
    else:
        parser.error("Provide --candidate REF and --out FILE")
