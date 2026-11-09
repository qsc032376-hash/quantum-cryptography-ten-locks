# Tier 8 independent OSC Cardinal validation

**Overall integration recommendation: ACCEPT**, subject to the final integrated submission check. On Cardinal, baseline and candidate each passed all ten paired seeded trials, and a separate candidate Checker run without test-harness seed injection also passed. The candidate reproduces the expected lower gate counts and unchanged active-qubit count; no seeded trial timed out. The independent full complex-operator audit below supports exact controlled-permutation equivalence. Ten samples cannot guarantee future success across platforms, seeds or load.

## Provenance and configuration

- Baseline `optimization/tier05-tier08-v2@0988ac44d88d08cc12258f2010afaf792dd53e7b`; candidate `optimization/tier08-advanced-v2@b92a17fae7cf14c880e6457bce4f3c339626fc94`. Both remote references were fetched and matched. Candidate `submissions/team3/tier08/modular.py` SHA-256: `ae89e63eb178c60774670e86c8e2cb4f1212e2dc8eb0070c8f3e9cc8639e4350` on both local and OSC copies. Official tools, scoring config, common code, challenge files, Tier 8 solution and order code are unchanged across these commits.
- Cardinal CPU partition, PAS3574 project, 2 CPUs and 4 GiB per Slurm allocation, 8-minute job limit; all report Intel Xeon CPU Max 9470. Nodes used: c0007, c0042 and c0043. First two pairs ran across different nodes; remaining pairs ran on the same node, but jobs were submitted independently and could overlap. Load and node effects limit timing comparisons.
- Python 3.12.4, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4, psutil 7.2.2, CPU statevector method, double precision, two Aer threads, 64 shots per run and one Aer circuit in every observed trial. The ten preselected distinct actual simulator seeds were 1000–10000 in steps of 1000. Official scoring uses `[rz,sx,x,cx]`, all-to-all coupling, optimization level 1 and transpiler seed 12345.
- Official solve and scoring-transpile thresholds are each 120 s, not a 120 s limit on the complete Checker. An additional 60 s is allowed for worker startup by the unchanged Checker; the harness applies a 370 s outer wall cap. No official timeout was relaxed. Process-tree peak RSS is sampled every 50 ms and summed across processes, so it may miss peaks or double-count shared memory.

The candidate commit was not present on OSC and the private Git remote could not authenticate there. With user authorization, an incremental bundle and test scripts were uploaded to the existing private OSC research directory. The transfer archive SHA-256 was `a647c354b04d3e314b4b7a15af1f1c31432cd38d31f3849e728821fd5b3e64f3`; the baseline prerequisite and exact candidate commit and source digest were verified after import.

## Official scored circuits

| Metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Two-qubit gates | 42,792 | 33,904 | −20.77% |
| Depth | 123,300 | 96,055 | −22.10% |
| Total gates | 130,171 | 102,561 | −21.21% |
| Active qubits | 18 | 18 | unchanged |

Each row of the paired trial table below used an actual executed circuit and produced exactly its variant's metrics above. Official Simplicity uses best/team ratios weighted 0.4, 0.3, 0.2 and 0.1 respectively. Candidate strictly improves the first three and ties active qubits, so it dominates this baseline on the four measures when eligible. Other teams' results are unknown; no final competition score is asserted.

## Ten paired Cardinal trials

All 20 trials were **PASS**, meaning the original official Checker returned `full`, SHA-256 match, valid metrics, zero flags and no timeout, with one actual Aer call. Independent SHA-256 also matched, and each recorded forwarded seed equals the seed in the table; every call used the same 64 shots, method and precision. Completed / timeout / failed counts were **10 / 0 / 0** for each implementation. Baseline and candidate snapshots and Checker processes were separate. Jobs 16447730/16447731 formed the first pair; remaining jobs 16448141–16448158 were submitted in seed order, baseline then candidate, and could run concurrently.

| Actual seed | Status baseline / candidate | solve seconds baseline / candidate | Checker wall seconds baseline / candidate | sampled peak RSS MiB baseline / candidate | Slurm jobs baseline / candidate | nodes baseline / candidate |
|---:|---|---:|---:|---:|---|---|
|1000|PASS / PASS|32.797 / 28.467|38.8505 / 35.4886|520.58 / 460.35|16447730 / 16447731|c0007 / c0043|
|2000|PASS / PASS|31.436 / 27.077|35.4809 / 31.1262|523.90 / 457.22|16448141 / 16448142|c0007 / c0042|
|3000|PASS / PASS|34.386 / 27.167|39.0816 / 31.1981|522.32 / 457.92|16448143 / 16448144|c0042 / c0042|
|4000|PASS / PASS|34.353 / 27.132|38.7627 / 31.2960|521.02 / 456.85|16448145 / 16448146|c0042 / c0042|
|5000|PASS / PASS|34.515 / 27.079|38.8249 / 31.1981|527.70 / 457.23|16448147 / 16448148|c0042 / c0042|
|6000|PASS / PASS|35.103 / 30.064|39.5099 / 34.1151|522.66 / 463.35|16448149 / 16448150|c0042 / c0042|
|7000|PASS / PASS|35.386 / 27.387|39.1573 / 30.7240|524.46 / 460.40|16448151 / 16448152|c0043 / c0043|
|8000|PASS / PASS|34.582 / 27.749|38.2981 / 31.2158|526.71 / 458.18|16448153 / 16448154|c0043 / c0043|
|9000|PASS / PASS|34.367 / 27.139|38.0984 / 30.7283|518.70 / 459.70|16448155 / 16448156|c0043 / c0043|
|10000|PASS / PASS|34.220 / 26.880|37.9589 / 30.7300|519.48 / 458.64|16448157 / 16448158|c0043 / c0043|

| Statistic | Baseline | Candidate |
|---|---:|---:|
| Solve mean / median, s | 34.1145 / 34.3765 | 27.6141 / 27.1530 |
| Solve min / max, s | 31.436 / 35.386 | 26.880 / 30.064 |
| Complete Checker wall mean, s | 38.4023 | 31.7820 |
| Sampled peak RSS mean, MiB | 522.75 | 458.98 |
| Sampled peak RSS min / max, MiB | 518.70 / 527.70 | 456.85 / 463.35 |

Mean paired solve difference (candidate minus baseline) was **−6.5004 s**, or **−19.05%** relative to baseline mean; mean sampled peak RSS was **−12.20%**. These are observations under this configuration, not claims of universal speed or memory improvement.

### Independent unmodified candidate Checker

Slurm job **16448159** on c0043 invoked the unchanged Checker against an unmodified candidate snapshot, with no test-harness seed injection. The original solver retains its own simulator seed 808. The result was `full`, hash match, metrics valid, `flags=[]`, one circuit and the candidate metrics above; solve **26.848 s**, complete Checker wall **30.5744 s**, sampled peak RSS **459.32 MiB**. This is separate from the ten paired samples.

## Mathematical audit

The candidate implements each public work permutation `P_m(x)=m*x mod 35` for `x<35`, identity for `35≤x<64`, controlled by the phase wire. Fixed-mask elimination reverses a self-inverse operation sequence transforming the entire permutation to identity; cycle-anchor resynthesis rotates cycle representations and realizes the same ordered endpoint transpositions. Each complete MCX operation has exact phase and restores its borrowed dirty wires. With control zero all controlled operations are identity. The optimizer neither changes the public modular powers nor computes a classical factoring answer.

The independently written local `research/tier08_osc/audit.py` constructed the complete complex 512×512 operator for each actual 9-wire multiplier and compared every element against an independently constructed mathematical matrix for all control, work and two dirty-wire values, including padding; its adjoint was also compared to the inverse permutation. The maximum operator/inverse element errors for multipliers 2, 4, 11 and 16 were respectively **1.5211e−13**, **1.9229e−13**, **2.9333e−13** and **2.9122e−13** (`research/tier08_osc/audit.json`). This covers complex phases, arbitrary dirty inputs and restoration in each block to numerical precision, not a dense full 18-qubit operator. The existing separate 1–6-control template complex-operator tests have maximum error 3.78e−15. Equality of each full controlled block extends by linearity to superposition and external entanglement; composition with unchanged 12 powers, inverse QFT, initialization and measurements preserves the full phase-estimation circuit.

## Decisions and remaining risks

- Mathematical correctness: **ACCEPT**, numerical full-block checks plus compositional argument for the stated construction and environment.
- Official Checker reliability: **ACCEPT for this fixed configuration**, 10/10 each and a separate unseeded candidate check; this is not a zero-failure proof.
- Circuit resources: **ACCEPT**, all three gate metrics improved, 18 active qubits retained.
- Runtime and memory: **ACCEPT for the observed sample**; shared nodes, concurrent execution, seed set, hardware and sampled RSS limit generalization.
- Overall integration: **ACCEPT**, integrating the candidate Tier 8 modular implementation only after normal review and rerunning the official integrated submission validation. The public permutation-table compiler has exponential classical preprocessing; disclose that limitation. Do not modify frozen v5 or create/freeze v6 as part of this validation.

## Reproduction and evidence

`hpc/tier08_osc/run_trial.py` archives the exact requested Git commit into a fresh temporary team snapshot, removes other tiers' solution entry points, and invokes the original official Checker. In seeded mode, a temporary wrapper supplies and records the requested Aer seed (and seed+1 if a second batch were needed), observed method/precision/shots/circuit count, and independent hash boolean; neither Checker nor scoring files are changed. `--unseeded` does not append the wrapper. Raw safe result JSON and Slurm logs remain in private OSC `~/tier09-osc-research/tier08-results` and `~/tier09-osc-research/tier08-study/logs`. The table above is the retained per-run record; no challenge keys, plaintext, factors or counts are written here.

With the two exact commit objects in a clone, a compatible virtual environment and private results/log directories, set `PYTHONPATH` to the clone root, `T8_VENV` to the venv, `T8_RESULTS` to the results directory, and submit `hpc/tier08_osc/trial.sbatch` for `T8_VARIANT=baseline` and `candidate` with each `T8_SEED` in 1000, 2000, ..., 10000. Submit candidate with `T8_SEED=unseeded` for the separate official check. Use the same authorized account and CPU partition. The script refuses existing result paths; retain all failures without reruns or timeout changes. For local phase audit use `OPENBLAS_NUM_THREADS=1 python -B research/tier08_osc/audit.py`. A local-only seed-1000 harness preflight was also performed before OSC; it is not included in the Cardinal statistics.
