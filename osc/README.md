# OSC Pitzer — Qiskit Aer CPU batch setup

Helper files for running the Qiskit Aer simulations of tiers 8–10 on Ohio
Supercomputer Center's **Pitzer** cluster, CPU only (no GPU requested).

| File | Purpose |
|---|---|
| `osc/smoke_test.py` | Bell-state Aer test; prints Python/Qiskit/Aer versions and wall time |
| `osc/run_cpu.sh` | Slurm batch script: 1 node, 4 CPUs, 16 GB, 20 min, `--account=PAS3574` |
| `osc/README.md` | This guide |

Never commit an OSC password, project access code, GitHub token or SSH private
key. `run_cpu.sh` forwards only the three `OSC_*` variables; everything else is
read from your shell at submission time.

## 1. Log in

```bash
ssh PAS3574@pitzer.osc.edu
```

Authentication uses your OSC password plus Duo. Alternatively open the OSC
OnDemand shell in a browser. The login node is for editing, copying files and
submitting jobs only — **never** run a simulation there.

## 2. One-time Python environment

```bash
module avail python            # confirm the current Python module name
module load python/3.12        # adjust if OSC publishes a newer 3.12.x
python3 -m venv $HOME/.venvs/qiskit-ten-locks
source $HOME/.venvs/qiskit-ten-locks/bin/activate
python -m pip install --upgrade pip
cd ~/quantum-cryptography-ten-locks
python -m pip install -r requirements.txt
python tools/check_setup.py    # optional: validates Qiskit/Aer and the circuits
```

The pinned versions used for this repository are Python 3.12, `qiskit==2.6.1`
and `qiskit-aer==0.18.2` (see `requirements.txt`). `smoke_test.py` prints the
versions actually installed on the compute node.

If `$HOME` is tight, put the virtualenv under `$PFSDIR` and pass
`OSC_VENV=$PFSDIR/.venvs/qiskit-ten-locks`.

## 3. Submit the CPU smoke test

```bash
cd ~/quantum-cryptography-ten-locks
./osc/run_cpu.sh                 # self-submits with sbatch
# or explicitly:
sbatch osc/run_cpu.sh
```

Defaults come from the `#SBATCH` block: `qiskit-smoke`, `--account=PAS3574`,
1 node, 1 task, 4 CPUs, 16 GB, 20 minutes. Override without editing the file:

```bash
OSC_ACCOUNT=PAS3574 OSC_PYTHON_MODULE=python/3.12 \
OSC_VENV=$HOME/.venvs/qiskit-ten-locks ./osc/run_cpu.sh
```

The script refuses to compute on the login node: without `SLURM_JOB_ID` it only
calls `sbatch`.

## 4. Watch, read, cancel

```bash
squeue -u $USER                      # queued/running jobs
squeue -j <JOBID>                    # one job
tail -f osc/logs/smoke-<JOBID>.out   # stdout (JSON versions + counts)
cat osc/logs/smoke-<JOBID>.err       # stderr; empty on success
scancel <JOBID>                      # cancel
sacct -j <JOBID> --format=JobID,State,Elapsed,MaxRSS,AllocCPUS
```

`MaxRSS`/`Elapsed` from `sacct` record the real resources used.

## 5. Expected result

```
"python": "3.12.x", "qiskit": "2.6.1", "qiskit_aer": "0.18.2", ...
counts: {'00': ..., '11': ...}
PASS: Bell state on Aer (4096 shots, ... s)
```

A non-zero exit means the environment is wrong (missing module, wrong venv,
broken Aer install); fix it before running any tier simulation.

## 6. Notes

- No GPU partition is requested; the default `cpu` partition is used.
- Do not submit real tier key recovery from this guide; it is preparation only.
- Logs live in `osc/logs/` and are git-ignored, so results stay on the cluster.
- Keep the repository private; never push OSC credentials or recovered keys.
