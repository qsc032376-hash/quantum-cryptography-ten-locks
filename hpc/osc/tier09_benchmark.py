#!/usr/bin/env python3
"""Run one bounded Tier 9 trial with the independently pinned benchmark harness."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

BASELINE = '41c7c6775b8fc499c2acdd878b4829bd17e1210d'
CANDIDATE = '00fee41ee8707ccdd2b6920dd95cc877d2d506bf'
HARNESS = 'ab9676749e00da904d0b8076811a2407d3b7205f'
SEEDS = tuple(range(1000, 10001, 1000))


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', choices=('baseline', 'candidate'), required=True)
    p.add_argument('--seed', type=int, choices=SEEDS, required=True)
    p.add_argument('--harness', type=Path, required=True, help='clean checkout at pinned harness commit')
    p.add_argument('--output-dir', type=Path, required=True, help='private, existing directory')
    p.add_argument('--preflight', action='store_true', help='validate configuration without a simulation')
    a = p.parse_args()
    root = a.harness.resolve()
    if git(root, 'rev-parse', 'HEAD') != HARNESS or git(root, 'status', '--porcelain', '--untracked-files=no'):
        p.error('harness checkout must be clean and at the pinned commit')
    ref = BASELINE if a.version == 'baseline' else CANDIDATE
    if git(root, 'rev-parse', ref + '^{commit}') != ref:
        p.error('specified commit unavailable')
    if not a.output_dir.is_dir():
        p.error('output directory must already exist')
    versions = {}
    for pkg in ('qiskit', 'qiskit-aer', 'numpy', 'psutil'):
        try: versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError: p.error(f'{pkg} is not installed')
    target = a.output_dir.resolve() / f'{a.version}-{a.seed}.json'
    metadata = target.with_suffix('.environment.json')
    if target.exists() or metadata.exists(): p.error('output already exists; preserve prior results')
    cmd = [sys.executable, str(root / 'benchmarks/cross_seed_regression.py'), '--tiers', '9',
           '--seeds', str(a.seed), '--ref', ref, '--timeout', '120', '--memory-mb', '1024',
           '--total-seconds', '180', '--output', str(target)]
    if a.preflight:
        print(json.dumps({'preflight': 'ok', 'commit': ref, 'harness': HARNESS, 'packages': versions,
                          'python': platform.python_version(), 'command': cmd}, indent=2))
        return 0
    if not os.environ.get('SLURM_JOB_ID'):
        p.error('simulation must run in a Slurm compute allocation')
    cpu = Path('/proc/cpuinfo')
    mem = Path('/proc/meminfo')
    cpu_models = sorted({line.split(':', 1)[1].strip() for line in cpu.read_text().splitlines()
                         if line.startswith('model name')}) if cpu.exists() else []
    memory = next((line for line in mem.read_text().splitlines() if line.startswith('MemTotal:')), None) if mem.exists() else None
    info = {'commit': ref, 'harness_commit': HARNESS, 'python': platform.python_version(),
            'packages': versions, 'platform': platform.platform(), 'cpu_models': cpu_models,
            'node_memory': memory, 'slurm_job_id': os.environ['SLURM_JOB_ID'],
            'cpus_per_task': os.environ.get('SLURM_CPUS_PER_TASK'),
            'simulator': 'statevector, CPU, default precision; max_memory_mb=512, max_parallel_threads=2',
            'seed': a.seed, 'limits': {'worker_seconds': 120, 'worker_rss_mib': 1024},
            'transpiler': 'solution defaults for cross-seed run; official scoring config in snapshot'}
    with metadata.open('x', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
    # The harness uses its own 2-thread setting and records actual seed and sampled RSS.
    return subprocess.run(cmd, cwd=root, check=False).returncode


if __name__ == '__main__':
    sys.exit(main())
