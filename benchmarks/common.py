"""Private, bounded helpers for benchmark workers and isolated Git snapshots."""
import hashlib
import io
import importlib.metadata
import platform
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'benchmarks' / 'worker.py'


def environment():
    versions = {'python': platform.python_version(), 'platform': platform.platform()}
    for package in ('qiskit', 'qiskit-aer', 'numpy', 'psutil'):
        try: versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: versions[package] = 'NOT INSTALLED'
    return versions


def resolve(ref):
    return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--verify', ref + '^{commit}'], text=True).strip()


def snapshot(commit, destination):
    data = subprocess.check_output(['git', '-C', str(ROOT), 'archive', '--format=tar', commit])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for item in archive.getmembers():
            path = Path(item.name)
            if path.is_absolute() or '..' in path.parts or not (item.isfile() or item.isdir()):
                raise ValueError('Unsafe archive entry')
        archive.extractall(destination, filter='data')


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_bounded(args, seconds, memory_mb, cwd):
    """Monitor the process tree's summed RSS, sampled at 20ms; discard child output."""
    import psutil
    env = dict(os.environ, PYTHONHASHSEED='0', QISKIT_PARALLEL='FALSE', OMP_NUM_THREADS='2')
    start = time.monotonic()
    proc = subprocess.Popen([sys.executable, str(WORKER), *map(str, args)], cwd=cwd,
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    peak = 0
    state = 'ok'
    parent = psutil.Process(proc.pid)
    while proc.poll() is None:
        try:
            processes = [parent, *parent.children(recursive=True)]
            rss = sum(p.memory_info().rss for p in processes if p.is_running())
            peak = max(peak, rss)
            if rss > memory_mb * 1024 * 1024:
                state = 'memory_limit'
            elif time.monotonic() - start > seconds:
                state = 'timeout'
            if state != 'ok':
                for p in reversed(processes):
                    try: p.kill()
                    except psutil.Error: pass
                break
        except psutil.Error:
            pass
        time.sleep(.02)
    proc.wait()
    if state == 'ok' and proc.returncode != 0:
        state = 'worker_error'
    return {'state': state, 'wall_seconds': round(time.monotonic()-start, 4),
            'peak_rss_bytes_sampled': peak, 'memory_limit_mb': memory_mb, 'timeout_seconds': seconds}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def run_worker(mode, tree, tier, seed, timeout, memory_mb):
    with tempfile.TemporaryDirectory(prefix='qbench_private_') as tmp:
        prefix = Path(tmp) / 'result'
        metadata = run_bounded([mode, tree, tier, seed if seed is not None else '-', prefix], timeout, memory_mb, tree)
        result = {}
        path = Path(str(prefix) + '.safe.json')
        if metadata['state'] == 'ok' and path.exists():
            result = json.loads(path.read_text())
        elif metadata['state'] == 'ok':
            metadata['state'] = 'worker_error'
        result['resource'] = metadata
        return result
