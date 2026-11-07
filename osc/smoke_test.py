"""Minimal Qiskit Aer smoke test for Ohio Supercomputer Center (OSC) CPU nodes.

Runs a synthetic Bell state, checks the measurement statistics, and prints the
Python / Qiskit / Aer versions plus the wall-clock time.  It uses no challenge
data and recovers no key, so it is safe to run before the real simulations.

Usage (inside the project venv, on a compute node):

    python osc/smoke_test.py

Submit it through Slurm instead of running on the login node:

    sbatch osc/run_cpu.sh
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time

SHOTS = 4096
SEED = 12345
TOLERANCE = 0.05


def main() -> int:
    started = time.perf_counter()

    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator

    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])

    simulator = AerSimulator()
    compiled = transpile(circuit, simulator)
    result = simulator.run(compiled, shots=SHOTS, seed_simulator=SEED).result()
    counts = result.get_counts()

    elapsed = time.perf_counter() - started
    total = sum(counts.values())
    unexpected = sorted(set(counts) - {"00", "11"})
    share_00 = counts.get("00", 0) / total if total else 0.0

    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "qiskit": _version("qiskit"),
        "qiskit_aer": _version("qiskit-aer"),
        "numpy": _version("numpy"),
        "node": platform.node(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
        "slurm_mem_per_node": os.environ.get("SLURM_MEM_PER_NODE"),
        "wall_seconds": round(elapsed, 3),
    }
    print(json.dumps(environment, indent=2))
    print("counts:", dict(sorted(counts.items())))

    failures = []
    if total != SHOTS:
        failures.append(f"expected {SHOTS} shots, got {total}")
    if unexpected:
        failures.append(f"unexpected outcomes {unexpected}")
    if abs(share_00 - 0.5) > TOLERANCE:
        failures.append(f"'00' share {share_00:.3f} outside 0.5 +/- {TOLERANCE}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(f"PASS: Bell state on Aer ({SHOTS} shots, {elapsed:.2f} s)")
    return 0


def _version(distribution: str) -> str:
    try:
        from importlib.metadata import version

        return version(distribution)
    except Exception:  # pragma: no cover - packaging metadata is optional
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
