#!/usr/bin/env python3
"""Read-only, bounded profiling of the unchanged official Tier 5/6/7 workers.

Run this only as a diagnostic, separately from the three ordinary Checker CLI
runs. The callback observes function inputs/returns; it neither replaces nor
edits any production, Qiskit, Aer, or Checker function. The official solve
worker installs its usual Aer recorder, exactly as it does in normal use.

Private QPY recordings stay in --private-dir. Published evidence contains only
structural fingerprints, operation histograms, metrics and equality booleans.
Numeric gate parameters, global-phase values, measurement counts, recovered
keys and plaintext are never published. Opaque gate definitions are not read.

The supplied fingerprint helper must expose summarize(circuit, checker), which
returns a JSON-safe structural summary without inspecting opaque definitions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
from numbers import Number
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_recordings(path: Path):
    from qiskit import qpy

    with path.open("rb") as handle:
        sizes = json.loads(handle.readline())
        circuits = []
        for size in sizes:
            payload = handle.read(size)
            if len(payload) != size:
                raise ValueError("Incomplete official circuit recording")
            circuits.extend(qpy.load(io.BytesIO(payload)))
        if handle.read(1):
            raise ValueError("Unexpected trailing recording bytes")
    return circuits


def native_equal(left, right) -> bool:
    """Transient native-basis equality; never enter an opaque gate definition."""
    allowed = {"rz", "sx", "x", "cx", "measure", "barrier", "reset", "delay"}
    if (left.num_qubits, left.num_clbits, len(left.data)) != (
        right.num_qubits, right.num_clbits, len(right.data)
    ):
        return False
    if not isinstance(left.global_phase, Number) or not isinstance(right.global_phase, Number):
        raise ValueError("Native equality requires a scalar numeric global phase")
    if left.global_phase != right.global_phase:
        return False
    for a, b in zip(left.data, right.data):
        if a.operation.name not in allowed or b.operation.name not in allowed:
            raise ValueError("Native equality refuses opaque instructions")
        if getattr(a.operation, "condition", None) is not None or getattr(b.operation, "condition", None) is not None:
            raise ValueError("Native equality refuses conditional instructions")
        if a.operation.name != b.operation.name:
            return False
        if a.operation.base_class is not b.operation.base_class:
            return False
        if (a.operation.num_qubits, a.operation.num_clbits) != (
            b.operation.num_qubits, b.operation.num_clbits
        ):
            return False
        if [left.find_bit(q).index for q in a.qubits] != [
            right.find_bit(q).index for q in b.qubits
        ]:
            return False
        if [left.find_bit(c).index for c in a.clbits] != [
            right.find_bit(c).index for c in b.clbits
        ]:
            return False
        if len(a.operation.params) != len(b.operation.params):
            return False
        for left_value, right_value in zip(a.operation.params, b.operation.params):
            if not isinstance(left_value, Number) or not isinstance(right_value, Number):
                raise ValueError("Native equality requires scalar numeric parameters")
            if left_value != right_value:
                return False
    return True


def plain_config(locals_dict):
    keys = (
        "basis_gates", "optimization_level", "seed_transpiler",
        "num_processes", "coupling_map", "initial_layout",
    )
    return {key: locals_dict.get(key) for key in keys}


def worker(args):
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer.backends.aerbackend import AerBackend

    checker = load_module(args.official_root / "tools/check_submission.py", "official_checker_probe")
    helper = load_module(args.helper, "structural_fingerprint_probe")
    solution_path = (args.official_root / f"submissions/team3/tier{args.tier:02d}/solution.py").resolve()
    checker_path = str((args.official_root / "tools/check_submission.py").resolve())
    solution_string = str(solution_path)
    transpile_code = transpile.__code__
    aer_run_code = AerBackend.run.__code__
    original = []
    preprocessed = []
    aer = []
    scoring_input = []
    scoring_output = []
    configs = []
    aer_options = []
    inflight = {}
    profile_errors = []

    def circuits(value):
        if isinstance(value, QuantumCircuit):
            return [value.copy()]
        if isinstance(value, (list, tuple)):
            return [item.copy() for item in value if isinstance(item, QuantumCircuit)]
        raise TypeError("Unexpected circuit argument type")

    def profile(frame, event, arg):
        code = frame.f_code
        if code is not transpile_code and code is not aer_run_code:
            return
        try:
            if code is transpile_code:
                if event == "call":
                    caller = frame.f_back
                    caller_path = caller.f_code.co_filename if caller else ""
                    if args.phase == "solve" and caller_path == solution_string:
                        original.extend(circuits(frame.f_locals["circuits"]))
                        configs.append(plain_config(frame.f_locals))
                        inflight[id(frame)] = "source"
                    elif args.phase == "score" and caller_path == checker_path:
                        scoring_input.extend(circuits(frame.f_locals["circuits"]))
                        configs.append(plain_config(frame.f_locals))
                        inflight[id(frame)] = "score"
                elif event == "return" and id(frame) in inflight:
                    kind = inflight.pop(id(frame))
                    target = preprocessed if kind == "source" else scoring_output
                    target.extend(circuits(arg))
            elif args.phase == "solve" and event == "call":
                aer.extend(circuits(frame.f_locals["circuits"]))
                options = frame.f_locals.get("run_options", {})
                backend_options = frame.f_locals["self"].options
                backend_seed = getattr(backend_options, "seed_simulator", None)
                aer_options.append({
                    "shots": options.get("shots"),
                    "seed_simulator": options.get("seed_simulator"),
                    "seed_specified": "seed_simulator" in options,
                    "backend_seed_simulator": backend_seed,
                    "effective_seed_simulator": options.get("seed_simulator", backend_seed),
                    "backend_method": getattr(backend_options, "method", None),
                    "backend_max_memory_mb": getattr(backend_options, "max_memory_mb", None),
                    "backend_max_parallel_threads": getattr(backend_options, "max_parallel_threads", None),
                })
        except Exception as error:
            # Preserve normal worker execution; do not publish exception values.
            profile_errors.append(type(error).__name__)

    prefix = args.private_dir / f"tier{args.tier:02d}"
    started = time.perf_counter()
    sys.setprofile(profile)
    try:
        if args.phase == "solve":
            checker.worker_solve(args.tier, str(solution_path), str(prefix))
        else:
            checker.worker_transpile(str(prefix) + ".circuits", str(prefix) + ".score.json")
    finally:
        sys.setprofile(None)
    elapsed = time.perf_counter() - started

    def summaries(items):
        return [helper.summarize(circuit, checker) for circuit in items]

    evidence = {
        "tier": args.tier,
        "phase": args.phase,
        "instrumentation": "sys.setprofile; unchanged official worker function",
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "qiskit_parallel": os.environ.get("QISKIT_PARALLEL"),
        "worker_wall_seconds": elapsed,
        "profile_errors": profile_errors,
        "transpile_configurations": configs,
        "source_sha256": hashlib.sha256(solution_path.read_bytes()).hexdigest(),
        "official_checker_sha256": hashlib.sha256(Path(checker_path).read_bytes()).hexdigest(),
    }
    if args.phase == "solve":
        recorded = load_recordings(Path(str(prefix) + ".circuits"))
        normalized = []
        for circuit in aer:
            clean = checker.strip_simulator_instructions(circuit)
            clean.metadata = {}
            clean.name = "scored"
            normalized.append(clean)
        outcome = json.loads(Path(str(prefix) + ".json").read_text())
        from common import load_hashes

        expected_hash = load_hashes()[args.tier]
        evidence.update({
            "original_constructed": summaries(original),
            "source_precompile_output_before_optional_gf2": summaries(preprocessed),
            "actual_aer_input": summaries(aer),
            "official_recorded_inputs": summaries(recorded),
            "aer_run_options": aer_options,
            "captured_constructed_count": len(original),
            "captured_aer_call_count": len(aer_options),
            "captured_aer_circuit_count": len(aer),
            "trace_complete": (
                not profile_errors and len(original) > 0
                and len(original) == len(preprocessed) == len(aer)
            ),
            "every_aer_input_matches_official_recording_native_exact": all(
                any(native_equal(item, record) for record in recorded)
                for item in normalized
            ) if normalized and recorded else False,
            "every_official_recording_matches_aer_input_native_exact": all(
                any(native_equal(record, item) for item in normalized)
                for record in recorded
            ) if normalized and recorded else False,
            "precompile_output_matches_aer_input_native_exact_by_call": [
                native_equal(before, actual)
                for before, actual in zip(preprocessed, aer)
            ],
            "outcome": {
                "hash_ok": outcome.get("answer_hash") == expected_hash,
                "error_present": outcome.get("error") is not None,
                "error_type": str(outcome["error"]).split(":", 1)[0]
                    if outcome.get("error") else None,
                "not_implemented": outcome.get("not_implemented"),
                "solve_seconds": outcome.get("solve_seconds"),
                "circuits_executed": outcome.get("circuits_executed"),
                "unique_circuits": outcome.get("unique_circuits"),
            },
        })
        if args.reference_capture_dir:
            reference_path = args.reference_capture_dir / f"tier{args.tier:02d}.circuits"
            if reference_path.exists():
                reference = load_recordings(reference_path)
                evidence["bridge_to_primary_checker"] = {
                    "reference": str(reference_path),
                    "unique_count_equal": len(recorded) == len(reference),
                    "native_exact_by_record_index": [
                        native_equal(item, other)
                        for item, other in zip(recorded, reference)
                    ],
                }
            else:
                evidence["bridge_to_primary_checker"] = {
                    "reference_present": False,
                    "expected_reference_filename": reference_path.name,
                }
    else:
        scored = json.loads(Path(str(prefix) + ".score.json").read_text())
        output_metrics = [checker.compute_metrics(item) for item in scoring_output]
        selected = max(
            range(len(output_metrics)),
            key=lambda index: (
                output_metrics[index]["two_qubit_gates"],
                output_metrics[index]["depth"],
            ),
        ) if output_metrics else None
        evidence.update({
            "official_scoring_inputs": summaries(scoring_input),
            "official_scoring_outputs": summaries(scoring_output),
            "trace_complete": (
                not profile_errors and len(scoring_input) > 0
                and len(scoring_input) == len(scoring_output)
            ),
            "selected_unique_record_index": selected,
            "selected_scoring_input": helper.summarize(scoring_input[selected], checker)
                if selected is not None else None,
            "selected_scoring_output": helper.summarize(scoring_output[selected], checker)
                if selected is not None else None,
            "selected_metrics_equal_official_worker_output": (
                output_metrics[selected] == scored["metrics"]
            ) if selected is not None else False,
            "official_worker_output": scored,
        })
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")


def bounded_run(command, *, environment, timeout_seconds, rss_limit_bytes):
    import psutil

    started = time.perf_counter()
    process = subprocess.Popen(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=environment, start_new_session=True,
    )
    peak_rss = 0
    stop_reason = None
    while process.poll() is None:
        try:
            parent = psutil.Process(process.pid)
            members = [parent] + parent.children(recursive=True)
            rss = 0
            for member in members:
                try:
                    rss += member.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            peak_rss = max(peak_rss, rss)
        except psutil.NoSuchProcess:
            pass
        elapsed = time.perf_counter() - started
        if elapsed > timeout_seconds:
            stop_reason = "timeout"
        elif peak_rss > rss_limit_bytes:
            stop_reason = "rss_limit"
        if stop_reason:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            break
        time.sleep(0.05)
    return {
        "returncode": process.wait(),
        "stop_reason": stop_reason,
        "wall_seconds": time.perf_counter() - started,
        "peak_process_tree_rss_bytes_sampled_50ms": peak_rss,
        "timeout_seconds": timeout_seconds,
        "rss_limit_bytes": rss_limit_bytes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-capture-dir", type=Path)
    parser.add_argument("--tier", type=int, choices=(5, 6, 7))
    parser.add_argument("--phase", choices=("solve", "score"))
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--rss-limit-mib", type=int, default=2048)
    args = parser.parse_args()
    for name in ("official_root", "private_dir", "helper", "output"):
        setattr(args, name, getattr(args, name).resolve())
    if args.reference_capture_dir:
        args.reference_capture_dir = args.reference_capture_dir.resolve()
    if args.phase:
        if args.tier is None:
            parser.error("--phase requires --tier")
        worker(args)
        return

    args.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, PYTHONHASHSEED="0", QISKIT_PARALLEL="FALSE")
    records = []
    for tier in ((args.tier,) if args.tier else (5, 6, 7)):
        for phase in ("solve", "score"):
            output = args.output / f"tier{tier:02d}-{phase}-profile.json"
            command = [
                sys.executable, str(Path(__file__).resolve()),
                "--official-root", str(args.official_root),
                "--private-dir", str(args.private_dir),
                "--helper", str(args.helper), "--output", str(output),
                "--tier", str(tier), "--phase", phase,
            ]
            if args.reference_capture_dir:
                command.extend(["--reference-capture-dir", str(args.reference_capture_dir)])
            resource_record = bounded_run(
                command, environment=environment, timeout_seconds=args.timeout,
                rss_limit_bytes=args.rss_limit_mib * 1024 * 1024,
            )
            resource_record.update({"tier": tier, "phase": phase, "evidence_file": output.name})
            records.append(resource_record)
            (args.output / "four-stage-resource-records.json").write_text(
                json.dumps(records, indent=2, sort_keys=True) + "\n"
            )
            print(json.dumps(resource_record), flush=True)
            if resource_record["returncode"] != 0 or resource_record["stop_reason"]:
                # No retries. Do not proceed to scoring a failed solve.
                break


if __name__ == "__main__":
    main()
