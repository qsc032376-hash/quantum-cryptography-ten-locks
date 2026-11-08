# Tier 5 clean-ancilla OSC validation

**Status: ten OSC pairs and both unseeded official checks completed.** Candidate and exact baseline source bundles were uploaded with authorization; the original candidate bundle lacked the unrelated `0988ac44d88d08cc12258f2010afaf792dd53e7b` object and a supplementary baseline bundle resolved preflight. Ten paired jobs have been submitted on Cardinal in serial order.

## Provenance and mathematical review

Baseline is `0988ac44d88d08cc12258f2010afaf792dd53e7b`, with post-native GF(2) rewriting as in `4d79b7fa66d0acd4786d71be3c3ac2d291618c69`. Clean candidate implementation and existing evidence are from `4317d8d`. Neither the official checker, scoring configuration, challenge inputs nor helper files differ between baseline and research reference. In the candidate, q19–q21 are extra clean ancillas: each clean M15 MCX8 begins and ends with all three at zero. The 25 oracle calls, original masks, equality wrappers, phase comparator, diffuser, and q[j]→c[j] measurements are preserved. The existing GF(2) pass rewrites only consecutive CX windows and checks their linear maps.

The existing `research/tier05_joint_mcx/experiment.py` checked the actual clean MCX8 on all 512 control/target basis branches with clean ancillas zero, including complex amplitudes and restoration, with maximum error 5.11e-15. Linearity extends the ideal subspace identity to arbitrary superpositions and entanglement with untouched wires; composition with the unchanged surrounding gates preserves the phase predicate. This is not an exhaustive comparison of arbitrary 22-qubit states, a formal proof of the entire transpiler, or an assertion about dirty initial ancillas. Existing local isolated Checker for the candidate returned full, hash match, metrics ok and no flags; two local 128-shot paired seeds passed but the candidate took approximately 89–90 seconds.

## Official limits and scoring

`tools/scoring_config.yaml` sets solve and scoring-transpilation limits to 120 seconds each. `tools/check_submission.py` gives each subprocess an additional 60 seconds for startup; it separately flags a reported solve beyond 120 seconds. Consequently 120 seconds is a solve threshold, not a total Checker wall-clock limit. The prepared harness applies a 370-second outer cap to the complete single-tier Checker, without relaxing either internal limit. Peak RSS is sampled over the process tree and may miss brief peaks or double-count shared pages.

Simplicity weights are 0.4 for two-qubit count, 0.3 depth, 0.2 total gates, and 0.1 active qubits; each ratio is best eligible team value divided by the team's value. The candidate improves gates and depth but increases active qubits from 19 to 22. If, purely as an illustration, these are the only two eligible teams and their measurements set the best values, the normalized simplicity fractions would be approximately 0.87548 baseline and 0.98636 candidate. The actual ranking depends on all eligible teams and is unknown. Full status and valid metrics are prerequisites.

## Experiments and decisions

All ten baseline trials passed; all ten candidate trials returned independently matching hashes but their solves exceeded 120 seconds, so the official checker classified each as circuit_only with an over-time flag. In the separate unseeded checks, both versions were full, hash matched, metrics were valid, and flags were empty; the candidate solve was 118.116 seconds, close to the 120-second limit. The prepared scripts use 128 shots, CPU statevector, 2 threads, 4 GiB Slurm allocation per trial, fixed seeds 1000–10000, isolated processes and unchanged 120-second official solve threshold. Results must record every failed or timed-out run; no retries or changed thresholds are authorized by this plan.

All ten paired seeds were run serially on Cardinal CPU with 2 CPUs, 4 GiB per job, Python 3.12.4, Qiskit 2.6.1, Aer 0.18.2 and NumPy 2.5.4. Each run reported its requested simulator seed actually forwarded, 128 shots and one genuine Aer circuit; independent SHA-256 matched for all 20. The unmodified Checker classified all ten baselines full/hash-match/metrics-ok/no-flags and all ten candidates circuit_only/hash-false/metrics-ok with the `solve() went over solve_timeout_s` flag. The independent candidate hashes matched, but the Checker intentionally reports hash false when a correct answer arrives after 120 seconds. Our `TIMEOUT` classification means this official solve limit was exceeded; these ten solves did return, and were not killed by the 180-second worker outer timeout.

| Seed | Baseline / candidate | solve seconds B / C | Checker wall seconds B / C | sampled peak RSS MiB B / C | job B / C |
|---:|---|---:|---:|---:|---|
|1000|PASS / TIMEOUT|21.695 / 157.611|24.1528 / 160.3576|287.04 / 337.77|16342025 / 16342026|
|2000|PASS / TIMEOUT|21.473 / 147.482|24.2797 / 150.0481|286.43 / 340.52|16342171 / 16342172|
|3000|PASS / TIMEOUT|20.796 / 148.835|23.3179 / 151.3660|288.00 / 340.34|16342173 / 16342174|
|4000|PASS / TIMEOUT|20.515 / 148.197|22.8431 / 150.6460|286.96 / 336.61|16342175 / 16342176|
|5000|PASS / TIMEOUT|20.645 / 147.968|23.1986 / 150.7945|288.51 / 339.59|16342177 / 16342178|
|6000|PASS / TIMEOUT|20.939 / 148.656|23.0433 / 151.2405|286.99 / 340.73|16342179 / 16342180|
|7000|PASS / TIMEOUT|20.966 / 148.112|22.9910 / 150.6631|287.73 / 341.12|16342181 / 16342182|
|8000|PASS / TIMEOUT|20.821 / 148.297|23.1818 / 150.8957|286.24 / 340.49|16342183 / 16342184|
|9000|PASS / TIMEOUT|20.760 / 148.605|23.2149 / 151.8762|286.80 / 339.12|16342185 / 16342186|
|10000|PASS / TIMEOUT|20.542 / 147.800|22.8304 / 150.1753|289.48 / 340.92|16342187 / 16342188|

Means for solve, Checker wall and sampled peak RSS are 20.9152 / 149.1563 seconds, 23.3054 / 151.8063 seconds, and 287.42 / 339.72 MiB (baseline / candidate). All 20 report Intel Xeon CPU Max 9470; 19 ran on c0001, with candidate seed 5000 on c0002, so that pair is across nodes despite matching CPU model. These are empirical samples under one configuration, not a guarantee for competition hardware. Full-circuit metrics were constant across all ten runs: baseline 14,552 CX, depth 28,132, total 40,938, 19 active qubits; candidate 13,802 CX, depth 19,480, total 38,556, 22 active qubits. Raw result JSON and logs are kept in private OSC storage.

**Decisions:** mathematical correctness **ACCEPT on the documented clean-zero subspace** with finite tests and compositional argument, subject to compiler and implementation limits; circuit-resource reduction **ACCEPT** for CX/depth/total with three extra active qubits; runtime reliability **REJECT** for these fixed OSC conditions because 10/10 candidate solves exceeded the official limit; official scoring suitability **INCONCLUSIVE** because the unseeded candidate check was full but near the limit, all ten seeded runs were ineligible, and ranking depends on all eligible teams; overall integration **REJECT for final submission under these conditions**. The exact competition hardware and outcome are not inferred from OSC.


## Separate unseeded official checks

To distinguish ordinary solve behavior from the paired-seed instrumentation, two further separate Slurm jobs invoked the unchanged official Checker on isolated `prepare()` snapshots without injecting an Aer seed. Job 16343387 (baseline) returned **full**, hash match, valid metrics, no flags and solve 17.056 seconds. Job 16343388 (candidate) returned **full**, hash match, valid metrics, no flags and solve **118.116 seconds**. Both reproduced the metrics above. This candidate success is real but only 1.884 seconds inside the official solve threshold; it does not erase the 10/10 fixed-seed overruns or establish general reliability. The two initial unseeded job submissions 16343383 and 16343384 were canceled before execution because their shell quoting was invalid; no result is claimed for them.

## Reproduction

The OSC code snapshot used for these trials was `49850439a8155d5e6c1281e2db0fac2eb02ff9fd`, with the exact baseline commit imported separately; this commit contains `hpc/tier05_osc/run_trial.py` and `trial.sbatch`. From a clean clone with both commit objects, use the prepared compatible virtual environment, create a private results directory and `logs` before submission, set `PYTHONPATH` to the checkout root, `T5_VENV` to the venv, `T5_RESULTS` to the private directory, and export `T5_VARIANT` and `T5_SEED` for each job. Submit each `trial.sbatch` with the authorized account and CPU partition, serially in baseline/candidate seed order. These trials inject a paired seed through an instrumented temporary submission copy, record the actual forwarded seed and independent hash, then run the unmodified official Checker; the separately reported unseeded checks omit this injection. Timeouts and errors must not be discarded. The runner measures full Checker wall time, not pure Aer time; it samples the checker process tree rather than precisely attributing memory to Aer. Existing private OSC files retain the raw safe JSON and official reports.
