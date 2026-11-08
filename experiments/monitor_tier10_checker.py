"""Measure approximate process-tree peak RSS of a Checker invocation."""
import os
import subprocess
import sys
import time
import psutil

if len(sys.argv) != 3:
    raise SystemExit('usage: python monitor_tier10_checker.py TEAM_DIR REPORT_DIR')
env = dict(os.environ, OMP_NUM_THREADS='2')
started = time.monotonic()
process = subprocess.Popen([sys.executable, '-B', 'tools/check_submission.py', sys.argv[1], '--out', sys.argv[2]], env=env)
parent = psutil.Process(process.pid)
peak = 0
while process.poll() is None:
    try:
        family = [parent, *parent.children(recursive=True)]
        total = 0
        for p in family:
            try:
                total += p.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        peak = max(peak, total)
    except psutil.NoSuchProcess:
        pass
    time.sleep(0.02)
print(f'checker_wall_s={time.monotonic()-started:.3f} sampled_tree_peak_rss_bytes={peak}', flush=True)
raise SystemExit(process.returncode)
