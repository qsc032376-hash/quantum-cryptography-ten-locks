"""Collect public runtime metadata without running a quantum circuit.

Environment variables are explicitly allowlisted. Binary digests are for
actually imported extension-module files, not guessed wheel identities.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib
import importlib.machinery
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys


APPROVED = "ce75c0721622d363e77912191a52a02c34f92472"
PRIOR = "e49ed058ed83b43866ffca4ca9b9785e3f9301ed"
PRIOR_PATH = "docs/v63-metrics-reconciliation/environmental-comparison.json"
ENV_KEYS = (
    "PYTHONHASHSEED", "QISKIT_PARALLEL", "QISKIT_NUM_PROCS",
    "OMP_NUM_THREADS", "OMP_DYNAMIC", "OMP_PROC_BIND", "OMP_PLACES",
    "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "MKL_DYNAMIC",
    "NUMEXPR_NUM_THREADS", "RAYON_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS", "QISKIT_IN_PARALLEL", "LANG", "LC_ALL", "TZ",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(repository, *arguments):
    return subprocess.check_output(
        ["git", "-C", str(repository), *arguments], stderr=subprocess.DEVNULL
    )


def optional_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Do not overwrite existing environmental evidence")

    # Import public installed libraries only; no repository solution/helper is imported.
    import qiskit
    import qiskit_aer
    import numpy
    import scipy
    import psutil

    imported_explicitly = []
    for name in ("qiskit._accelerate", "qiskit_aer.backends.controller_wrappers"):
        module = importlib.import_module(name)
        imported_explicitly.append({"name": name, "actual_file": getattr(module, "__file__", None)})

    distributions = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name", "unknown")
        row = {"name": name, "version": distribution.version}
        wheel = distribution.read_text("WHEEL")
        if name.lower().replace("_", "-") in {"qiskit", "qiskit-aer", "numpy", "scipy", "rustworkx"}:
            row["installed_wheel_metadata"] = wheel
        distributions.append(row)
    distributions.sort(key=lambda row: (row["name"].casefold(), row["version"]))

    native = []
    suffixes = tuple(importlib.machinery.EXTENSION_SUFFIXES)
    prefixes = ("qiskit", "qiskit_aer", "numpy", "scipy", "rustworkx")
    for name, module in sorted(sys.modules.copy().items()):
        filename = getattr(module, "__file__", None)
        if not filename or not name.startswith(prefixes) or not filename.endswith(suffixes):
            continue
        path = Path(filename).resolve()
        native.append({"module": name, "path": str(path), "bytes": path.stat().st_size,
                       "sha256": sha(path.read_bytes()), "actually_imported": True})

    cpu_fields = {}
    for line in (optional_text("/proc/cpuinfo") or "").splitlines():
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        if key in {"vendor_id", "model name", "cpu family", "model", "stepping", "flags"}:
            cpu_fields.setdefault(key, value)
    cgroup = {name: optional_text("/sys/fs/cgroup/" + name) for name in (
        "cpu.max", "cpuset.cpus.effective", "memory.max", "memory.high",
        "memory.current", "memory.peak", "memory.swap.max", "pids.max",
    )}
    limits = {}
    for name in ("RLIMIT_AS", "RLIMIT_DATA", "RLIMIT_CPU", "RLIMIT_RSS", "RLIMIT_STACK"):
        if hasattr(resource, name):
            limits[name] = list(resource.getrlimit(getattr(resource, name)))

    prior_bytes = git_bytes(args.repository, "show", f"{PRIOR}:{PRIOR_PATH}")
    prior = json.loads(prior_bytes)
    reference_checks = []
    for reference in prior["references"]:
        contents = git_bytes(args.repository, "show", reference["commit"] + ":" + reference["path"])
        actual = sha(contents)
        reference_checks.append({**reference, "actual_sha256": actual,
                                 "matches_prior_record": actual == reference["sha256"]})
    protected = []
    for reference in prior["protected_source_files"]:
        relpath = reference["path"]
        approved_bytes = git_bytes(args.repository, "show", f"{APPROVED}:{relpath}")
        current = (args.official_root / relpath).read_bytes()
        protected.append({"path": relpath, "approved_sha256": sha(approved_bytes),
                          "fresh_root_sha256": sha(current),
                          "current_equals_approved": current == approved_bytes,
                          "matches_prior_record": sha(current) == reference["sha256"]})

    result = {
        "captured_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "scope": "Read-only environment inventory in audit process; no Aer or transpilation execution",
        "interpreter": {"executable": sys.executable, "version": sys.version,
                        "version_info": list(sys.version_info), "implementation": platform.python_implementation(),
                        "build": list(platform.python_build()), "compiler": platform.python_compiler(),
                        "api_version": sys.api_version, "byte_order": sys.byteorder,
                        "hash_info": {key: getattr(sys.hash_info, key) for key in (
                            "width", "modulus", "inf", "nan", "imag", "algorithm", "hash_bits", "seed_bits", "cutoff")},
                        "flags": {key: getattr(sys.flags, key) for key in (
                            "isolated", "ignore_environment", "no_user_site", "safe_path", "optimize", "hash_randomization")}},
        "platform": {"system": platform.system(), "release": platform.release(),
                     "machine": platform.machine(), "platform": platform.platform(),
                     "libc": list(platform.libc_ver())},
        "cpu": {"logical_cpu_count": os.cpu_count(), "physical_cpu_count": psutil.cpu_count(logical=False),
                "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
                "first_cpu_public_fields": cpu_fields},
        "resources": {"host_virtual_memory": psutil.virtual_memory()._asdict(),
                      "cgroup_v2": cgroup, "process_resource_limits": limits,
                      "note": "Host/cgroup memory values are a contemporaneous shared-resource snapshot, not per-test peak memory."},
        "environment_allowlist": {key: os.environ.get(key) for key in ENV_KEYS},
        "official_worker_forced_environment": prior["process_and_order"]["actual_worker_forced_environment"],
        "environment_note": "Observed variables belong to this collector. Official child-worker settings and per-run manifests establish actual test environments. No non-allowlisted variables or credentials were saved.",
        "installed_distribution_count": len(distributions), "installed_distributions": distributions,
        "explicit_native_imports": imported_explicitly, "actually_imported_native_modules": native,
        "binary_scope_note": "Hashes identify existing imported extension files only. They do not claim an exhaustive shared-library dependency inventory or a historical wheel identity.",
        "historical_comparison": {
            "source_commit": PRIOR, "source_path": PRIOR_PATH, "source_sha256": sha(prior_bytes),
            "source_git_blob": git_bytes(args.repository, "rev-parse", f"{PRIOR}:{PRIOR_PATH}").decode().strip(),
            "historical_recorded": prior["historical_v63"], "comparison": prior["comparison"],
            "reference_rechecks": reference_checks, "approved_source_rechecks": protected,
            "unknown_historical_full_binary_environment": True,
            "root_cause_not_proven_by_version_difference": True,
        },
        "evidence_schema_separation": {
            "pass_manager_probe_circuit_digest": "standalone public-op-arity structural schema from pass_manager_probe.py",
            "pass_manager_tree_digest": "recursive pass/controller classes plus whitelisted stable configuration fields",
            "four_stage_circuit_digest": "separate shared helper schema; compare only digests produced by the same schema",
        },
        "collector_sha256": sha(Path(__file__).read_bytes()),
        "quantum_simulations": 0, "transpilation_runs": 0,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"packages": len(distributions), "native_modules": len(native),
                      "historical_references_verified": all(r["matches_prior_record"] for r in reference_checks),
                      "protected_sources_verified": all(r["current_equals_approved"] for r in protected)}))


if __name__ == "__main__":
    main()
