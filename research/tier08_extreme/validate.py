"""Bounded Tier 8 checks using Team 3's original strict benchmark harness.

Run this with the pinned Python/Qiskit environment. Source snapshots are
isolated, other tier entrypoints are omitted, and worker output is discarded.
Only the harness's safe aggregate JSON is retained. No secret outcomes,
orders, factors, keys or plaintext are copied into this report.

The `official` phase calls the unchanged official check_tier through the
existing worker, without simulator-seed injection. The `cross` phase retains
the existing harness's strict PASS/FAIL/UNCONTROLLED classification and
records the seeds actually forwarded to Aer. It does not separately repeat
the scoring transpilation for each seed.
"""

import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = "c4455782ea9388d5897fc27270f42dd3786ed35d"
HARNESS_SHA = "ab9676749e00da904d0b8076811a2407d3b7205f"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_files(root):
    """Runtime files plus selected research inputs, excluding evolving evidence."""
    found = {}
    production = root / "submissions/team3/tier08"
    for path in sorted(production.rglob("*.py")):
        if "__pycache__" not in path.parts:
            found[str(path.relative_to(root))] = digest(path)
    research = root / "research/tier08_extreme"
    # Runtime candidates may read candidate.json/selected.json. Other JSON is
    # observational search evidence, not part of the runtime source identity.
    for filename in ("candidate.json", "selected.json"):
        path = research / filename
        if path.is_file():
            found[str(path.relative_to(root))] = digest(path)
    for path in sorted(research.glob("*.py")):
        if path.name not in ("validate.py", "verify.py", "profile.py", "search.py"):
            found[str(path.relative_to(root))] = digest(path)
    return found


def fingerprint(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def official_status(result):
    if result.get("resource", {}).get("state") != "ok":
        return "FAIL"
    if (result.get("status") == "full" and result.get("hash_ok") is True
            and result.get("circuit_executed") is True
            and result.get("metrics_status") == "ok"
            and result.get("flags") == []):
        return "PASS"
    return "FAIL"


def summarize(report):
    summary = {}
    for variant in ("baseline", "candidate"):
        rows = [r for r in report["paired"] if r["variant"] == variant]
        complete = [r["result"] for r in rows if r["status"] == "PASS"]
        data = {"attempted": len(rows), "passed": len(complete),
                "statuses": {s: sum(r["status"] == s for r in rows)
                             for s in ("PASS", "FAIL", "UNCONTROLLED", "SKIP")}}
        if complete:
            data.update({
                "mean_solve_seconds_passed_only": statistics.mean(r["solve_seconds"] for r in complete),
                "median_solve_seconds_passed_only": statistics.median(r["solve_seconds"] for r in complete),
                "max_solve_seconds_passed_only": max(r["solve_seconds"] for r in complete),
                "mean_sampled_peak_rss_mib_passed_only": statistics.mean(
                    r["resource"]["peak_rss_bytes_sampled"] / 2**20 for r in complete),
                "max_sampled_peak_rss_mib_passed_only": max(
                    r["resource"]["peak_rss_bytes_sampled"] / 2**20 for r in complete),
            })
        summary[variant] = data
    by_seed = {}
    for row in report["paired"]:
        by_seed.setdefault(row["seed"], {})[row["variant"]] = row["status"]
    summary["paired_complete_passes"] = sum(
        r == {"baseline": "PASS", "candidate": "PASS"} for r in by_seed.values())
    summary["requested_distinct_seeds"] = len(by_seed)
    summary["strict_status_function"] = "unmodified benchmarks.cross_seed_regression.status"
    report["summary"] = summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", type=Path, default=ROOT.parent / "tier08-handoff-harness")
    parser.add_argument("--candidate-root", type=Path, default=ROOT)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1000, 2000, 3000, 4000, 5000])
    parser.add_argument("--phase", choices=("official", "cross", "all"), default="all")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--total-seconds", type=float, default=1200)
    parser.add_argument("--memory-mb", type=int, default=2048)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    if (not 0 < args.total_seconds <= 3600 or not 512 <= args.memory_mb <= 4096
            or len(args.seeds) > 10 or len(set(args.seeds)) != len(args.seeds)
            or any(s < 0 or s >= 2**32 for s in args.seeds)):
        parser.error("invalid bounded experiment configuration")
    harness = args.harness.resolve()
    source = args.candidate_root.resolve()
    harness_sha = subprocess.check_output(["git", "-C", str(harness), "rev-parse", "HEAD"], text=True).strip()
    if harness_sha != HARNESS_SHA:
        parser.error("benchmark harness does not match the pinned strict implementation")
    sys.path.insert(0, str(harness))
    from benchmarks.common import environment, run_worker, snapshot, write_json
    from benchmarks.cross_seed_regression import status

    baseline_sha = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", args.baseline + "^{commit}"], text=True).strip()
    files = source_files(source)
    stamp = fingerprint(files)
    limits = {"cross_seconds": 120, "official_outer_seconds": 370,
              "memory_mb": args.memory_mb, "per_invocation_total_seconds": args.total_seconds}
    if args.output.exists():
        if not args.resume:
            parser.error("output exists; use --resume to append unattempted seeds without overwriting failures")
        report = json.loads(args.output.read_text())
        if (report["candidate_source_fingerprint"] != stamp or report["baseline_commit"] != baseline_sha
                or report["harness_commit"] != harness_sha or report["limits"]["memory_mb"] != args.memory_mb
                or report["environment"] != environment()):
            parser.error("resume requires exactly the same runtime sources, baseline, harness, environment and memory budget")
    else:
        report = {
            "schema_version": 1, "kind": "tier08_extreme_validation", "tier": 8,
            "baseline_commit": baseline_sha, "candidate_parent_commit": subprocess.check_output(
                ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(),
            "candidate_source_files_sha256": files, "candidate_source_fingerprint": stamp,
            "harness_commit": harness_sha, "environment": environment(), "limits": limits,
            "official": {}, "paired": [], "invocations": [],
            "seed_policy": "existing harness injects requested seed plus Aer call index; transpiler/application RNG untouched",
            "resource_scope": "20 ms sampled sum of process-tree RSS; may miss peaks or double-count shared pages",
            "private_values_recorded": False,
        }
    all_requested_seeds = {r["seed"] for r in report["paired"]} | set(args.seeds)
    if len(all_requested_seeds) > 10:
        parser.error("at most ten distinct paired seeds across resumed invocations")
    invocation = {"phase": args.phase, "seeds": args.seeds, "time_budget_seconds": args.total_seconds}
    report["invocations"].append(invocation)
    started = time.monotonic()

    def save():
        summarize(report)
        invocation["wall_seconds_so_far"] = round(time.monotonic() - started, 4)
        write_json(args.output, report)

    with tempfile.TemporaryDirectory(prefix="tier08-extreme-validation-") as tmp:
        baseline = Path(tmp) / "baseline"
        candidate = Path(tmp) / "candidate"
        baseline.mkdir(); candidate.mkdir()
        snapshot(baseline_sha, baseline)
        snapshot(baseline_sha, candidate)
        shutil.copytree(source / "submissions/team3/tier08", candidate / "submissions/team3/tier08",
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(source / "research/tier08_extreme", candidate / "research/tier08_extreme",
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        assert fingerprint(source_files(candidate)) == stamp
        for tree in (baseline, candidate):
            for entry in (tree / "submissions/team3").glob("tier*/solution.py"):
                if entry.parent.name != "tier08":
                    entry.unlink()
            compile((tree / "submissions/team3/tier08/solution.py").read_text(), "solution.py", "exec")
        if args.preflight:
            print("preflight PASS", "source fingerprint", stamp, flush=True)
            return 0
        save()
        if args.phase in ("official", "all"):
            for variant, tree in (("baseline", baseline), ("candidate", candidate)):
                if variant in report["official"]:
                    continue
                remaining = args.total_seconds - (time.monotonic() - started)
                if remaining < 370:
                    invocation["stopped_reason"] = "not enough remaining budget for official outer cap"
                    save(); return 2
                entry = run_worker("official", tree, 8, None, 370, args.memory_mb)
                report["official"][variant] = {"validation_status": official_status(entry), "result": entry}
                save()
                print("official", variant, official_status(entry), entry.get("metrics"), flush=True)
                if official_status(entry) != "PASS":
                    invocation["stopped_reason"] = "official failure; no retry"
                    save(); return 1
        if args.phase in ("cross", "all"):
            if not all(report["official"].get(v, {}).get("validation_status") == "PASS"
                       for v in ("baseline", "candidate")):
                parser.error("cross-seed stage requires both unchanged official checks to have passed")
            attempted = {(r["variant"], r["seed"]) for r in report["paired"]}
            for seed in args.seeds:
                for variant, tree in (("baseline", baseline), ("candidate", candidate)):
                    if (variant, seed) in attempted:
                        continue
                    remaining = args.total_seconds - (time.monotonic() - started)
                    if remaining < 120:
                        invocation["stopped_reason"] = "not enough remaining budget for a complete bounded seed trial"
                        save(); return 2
                    entry = run_worker("cross", tree, 8, seed, 120, args.memory_mb)
                    label = status(entry)
                    report["paired"].append({"variant": variant, "seed": seed, "status": label, "result": entry})
                    save()
                    print("paired", variant, seed, label, entry.get("solve_seconds"), flush=True)
                    if entry.get("resource", {}).get("state") in ("timeout", "memory_limit"):
                        invocation["stopped_reason"] = "resource failure; no retry or further large runs"
                        save(); return 1
        invocation["completed_requested_phase"] = True
        save()
    return 0 if all(r["status"] == "PASS" for r in report["paired"]) else 1


if __name__ == "__main__":
    sys.exit(main())
