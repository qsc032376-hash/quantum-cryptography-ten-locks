# Tier 5 final selection and v6 handoff

**Decision: ACCEPT_GF2**, scoped to the tested implementation and environment. Ten newly executed OSC pairs passed for both implementations; the separate, unseeded official Tier 5 check of B also passed. B improves each scored gate/depth metric while retaining 19 active qubits. These observations do not guarantee future performance. This document is a handoff, not a v6 integration or release.

## Provenance and measured circuits

- Frozen v5: `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d`.
- A: `optimization/tier05-tier08-v2@0988ac44d88d08cc12258f2010afaf792dd53e7b`; source Tier 5 oracle and solver unchanged.
- B: the same A snapshot with the post-native consecutive-CX GF(2) rewrite from `research/real-circuit-optimization@4d79b7fa66d0acd4786d71be3c3ac2d291618c69`, inserted after solve's normal basis transpilation and before Aer execution. This is a runtime transformation, not a claim that the research branch contains a modified production solver.
- Depth-oriented mask-fusion reference: `research/tier05-mask-fusion@ab74c49`, 14,652 CX / depth 23,757. It was not included in these paired tests; those two numbers alone are insufficient to establish its full score or reliability against B.
- Excluded 22-active-qubit clean-ancilla version `research/tier05-clean-ancilla-osc@aed4e77`: all ten previously documented seeded OSC solves exceeded 120 seconds. See [clean-ancilla validation](TIER05_CLEAN_ANCILLA_OSC_VALIDATION.md).

| Metric | A | B | B minus A |
|---|---:|---:|---:|
| Two-qubit gates | 14,700 | 14,552 | −148 |
| Depth | 28,478 | 28,132 | −346 |
| Total gates | 41,086 | 40,938 | −148 |
| Active qubits | 19 | 19 | 0 |
| Ten seeded solves: mean seconds | 19.7523 | 22.2444 | +2.4921 |
| Ten seeded solves: range seconds | 18.671–20.498 | 21.152–24.951 | — |
| Mean Checker wall seconds | 21.7908 | 24.4682 | +2.6774 |
| Mean sampled peak process-tree RSS MiB | 307.27 | 286.36 | −20.91 |

## Rules and runtime

`SCORING.md` and `tools/scoring_config.yaml` define Simplicity as weighted best/team ratios: 2Q 0.4, depth 0.3, total gates 0.2, active qubits 0.1. Two-qubit count has the largest individual weight but is not the sole ranking criterion. B strictly improves the first three and ties the fourth, so it cannot score below A on these four metrics for the same eligible field; actual points depend on other teams. Extra active qubits worsen that metric's ratio. The Tier 5 small-circuit review threshold is 10 active qubits; 19 exceeds it, and the observed Checker produced no flags. These sources do not establish a separate hard 19-qubit upper limit.

The official configuration has separate 120-second solve and scoring-transpile thresholds. The Checker allows an additional 60 seconds for worker startup and explicitly flags a solve reporting over 120 seconds. Thus 120 seconds is not a limit on the entire Checker wall time. Our harness adds a separate 370-second outer process cap and does not relax either official threshold. The sampled 10 B solves are comfortably below 120 seconds, but future hardware, software, contention, or random outcomes may differ.

## New Cardinal paired experiments

Jobs 16343637–16343656 were submitted together as independent Slurm jobs, one run per seed and implementation, and all completed. Fixed matched Aer seeds 1000–10000 (step 1000) were captured at the actual Aer call; each used one circuit and 128 shots. All 20 returned PASS: official `full`, SHA-256 match, valid metrics, `flags=[]`, and an independent SHA-256 match. There were no observed TIMEOUT, FAIL or ERROR results. Every run reproduced its column of the circuit table above.

Both used Cardinal CPU, account PAS3574, 2 CPUs and 4 GiB per allocation, 8-minute Slurm wall limit, Python 3.12.4, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4, the existing Aer CPU statevector method and matching thread controls. Official scoring uses `[rz, sx, x, cx]`, all-to-all coupling, optimization level 1 and transpiler seed 12345. Each run used a fresh temporary A or B snapshot and the unchanged official Checker. The runner instruments only the temporary submission to supply and observe the paired seed and independent hash. Jobs ran concurrently, with the same CPU model Intel Xeon CPU Max 9470. Each pair shared a node except seed 7000 (A c0002, B c0004); concurrent allocations and shared-node load may affect time comparisons. RSS sums sampled process-tree RSS and can miss short peaks or double-count shared pages.

| Actual seed | A / B status | Solve s A / B | Checker wall s A / B | Peak RSS MiB A / B | Job A / B | Node A / B |
|---:|---|---:|---:|---:|---|---|
|1000|PASS / PASS|19.370 / 21.689|21.3583 / 23.9331|307.18 / 287.17|16343637 / 16343638|c0001 / c0001|
|2000|PASS / PASS|19.315 / 21.625|21.2894 / 23.8809|307.16 / 286.46|16343639 / 16343640|c0001 / c0001|
|3000|PASS / PASS|19.316 / 21.594|21.2896 / 23.8865|307.55 / 284.35|16343641 / 16343642|c0001 / c0001|
|4000|PASS / PASS|19.296 / 21.611|21.2873 / 23.8810|307.54 / 285.39|16343643 / 16343644|c0001 / c0001|
|5000|PASS / PASS|20.343 / 24.951|22.3237 / 27.1566|307.55 / 286.34|16343645 / 16343646|c0001 / c0001|
|6000|PASS / PASS|18.671 / 21.152|20.7191 / 23.1852|307.68 / 286.27|16343647 / 16343648|c0002 / c0002|
|7000|PASS / PASS|20.498 / 22.475|22.7981 / 24.6898|306.14 / 285.46|16343649 / 16343650|c0002 / c0004|
|8000|PASS / PASS|20.334 / 22.404|22.3732 / 24.6142|306.75 / 286.89|16343651 / 16343652|c0004 / c0004|
|9000|PASS / PASS|20.314 / 22.510|22.3745 / 24.7648|307.98 / 287.50|16343653 / 16343654|c0004 / c0004|
|10000|PASS / PASS|20.066 / 22.433|22.0949 / 24.6898|307.18 / 287.79|16343655 / 16343656|c0004 / c0004|

New unseeded isolated B official Checker job **16343657**: `full`, SHA-256 match, metrics `ok`, `flags=[]`, one circuit, solve **17.294 s**, and exactly the B metrics in the comparison table. This run did not inject a simulator seed. Earlier B-versus-clean OSC evidence (10 B passes, mean solve 20.9152 s and separate unseeded job 16343387 solve 17.056 s) is supporting reused evidence, not counted as the new A/B pairs.

Raw safe JSON and logs remain in private OSC `~/tier09-osc-research/tier05-final-results` and `tier05-final-study/logs`; no keys, plaintext or challenge data are recorded here. `hpc/tier05_osc/run_trial.py` on this branch adds `original` to the previously used harness: it builds A from the pinned snapshot with the baseline installer and B with the GF(2) installer. The OSC runner SHA-256 was `259b5c092009628ea37de4964661cacf8d223b7be8a9805d74bb76c6522f4d42`. For reproduction, provide both pinned source commits, the matching Python environment, a private results directory and logs directory; export `PYTHONPATH`, `T5_VENV`, `T5_RESULTS`, `T5_VARIANT` (`original` or `baseline`) and each `T5_SEED`, and submit `hpc/tier05_osc/trial.sbatch` under the authorized account/CPU partition. The script records safe metrics, seed, process-tree RSS and job ID; do not discard failures or change timeouts.

## Mathematical evidence

Existing [GF(2) research](REAL_CIRCUIT_OPTIMIZATION_EXPERIMENTS.md) and `research/real_circuits/results/equivalence.json` record 10,879 consecutive positive-CX windows, 248 replacements and 148 CX removed. Every replaced window touches at most five wires; full complex operators were compared on all columns with maximum error zero. Equal binary linear maps imply identical positive-CX permutation operators on all inputs, including relative phases, superpositions and external entanglement. The pass preserves the global phase, all non-CX operations and ordering, and all ten measurement wire/bit mappings. Composition therefore preserves the complete oracle's phase and the original restoration behavior of key, work and flag; it does not rely on a dense 19-qubit operator or a hash match as proof. Construction still uses 25 Grover iterations. This argument is conditional on the inspected implementation, exact synthesis and compiler behavior; the complete integrated submission must be checked again.

## Exact v6 integration handoff

1. From `0988ac44d88d08cc12258f2010afaf792dd53e7b`, integrate the existing Tier 5 `submissions/team3/tier05/solution.py` and `submissions/team3/tier05/oracle.py`, together with that team's existing common/helper dependencies; preserve all other tiers and official files.
2. From `4d79b7fa66d0acd4786d71be3c3ac2d291618c69`, make `research/real_circuits/experiments.py` and its imports `research/circuit_optimizer/gf2_synthesis.py`, `commutation_rules.py`, and `metrics.py` available in the submission environment, including package initializers where present. The optimizer also depends on NumPy and Qiskit. Verify packaging/import availability in the actual isolated Checker environment; research modules are not automatically present in every submission ZIP.
3. In Tier 5 `solution.py`, immediately after its existing `compiled` transpilation and before `simulator.run(compiled, shots=shots).result()`, apply exactly `from research.real_circuits.experiments import gf2_runs` then `compiled, _, _ = gf2_runs(compiled)`. The disposable installer demonstrating the exact insertion is `research/real_circuits/validate_candidates.py:install_variant`. Do not add the diffuser or clean-ancilla variants.
4. Preserve iteration count, oracle and measurement mapping; rerun the isolated official Checker and verify the actual scored circuit, all four metrics, full/hash/no flags, and timeout on the integration platform. Then perform the separately authorized complete submission validation before any release. If packaging, timing, correctness or full validation fails, retain A as the independently accepted fallback.

Neither v6 nor any frozen release, official file, other tier or submission archive was modified by this handoff. Ten successful seeds are evidence, not a failure-rate guarantee; scoring against other competitors and execution conditions remain unknown.
