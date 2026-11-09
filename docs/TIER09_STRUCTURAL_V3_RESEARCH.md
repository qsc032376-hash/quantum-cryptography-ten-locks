# Tier 9 structural synthesis v3

**Decision: INCONCLUSIVE.** A last-target fan-out pivot reduces scored resources without increasing width; two local seed pairs pass, but the gain is small and the candidate is slower in both observed pairs. This is insufficient evidence to replace the existing candidate. No release or submission package was changed.

## Provenance and scoring

Baseline `optimization/tier09-v2@00fee41ee8707ccdd2b6920dd95cc877d2d506bf`; frozen fallback `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d`. The only production edit changes the fan-out pivot in `submissions/team3/tier09/shared_controls.py`; SHA-256 of this file is `884fb7acb738693d1df5d97d481ea21443790e7308167e07c2a4705d0ebbf6e9`. Research scripts and evidence are included separately. OSC report `e133887` and Tier 8 reference `b92a17f` were reviewed; see their original reports for historical evidence.

Local environment macOS 27.0.1 ARM64, Python 3.14.5, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4. The scoring pipeline compiles the actual Aer-native circuit with optimization level 1 and seed 12345, then compiles that circuit to `rz,sx,x,cx`, all-to-all, no initial layout, level 1, seed 12345, using the unchanged official `compute_metrics` (measurement and barriers excluded). Initial static baseline reproduced every requested metric. The actual executed candidate circuit is checked below. Simplicity weights are 40% two-qubit, 30% depth, 20% total, 10% active qubits; the first three improve and the fourth is unchanged. These resource changes are not a prediction of competition points or competitors' scores.

| Whole circuit | Baseline | Last pivot | Difference |
|---|---:|---:|---:|
| Two-qubit | 55,999 | 55,971 | -28 (-0.0500%) |
| Depth | 120,242 | 120,223 | -19 |
| Total gates | 168,116 | 168,088 | -28 |
| Active qubits | 22 | 22 | 0 |

## Structure and bounded searches

Public multipliers used by the 14 phase controls are 2, 4, 16, 25, 9 with respective frequencies 1, 4, 3, 3, 3. The extension fixes all states >=77. For multiplier 2, public cycle lengths have counts {1:52, 30:2, 10:1, 3:2}; for each of 4, 9, 16, 25 they are {1:52, 15:4, 5:2, 3:2}. These are synthesis properties of public permutations, not recovered secret values or a classical factoring fallback.

Standalone controlled blocks were compiled with an extra clean wire, separately through the same two compilation stages. Baseline fixed-mask / minimum-Hamming cycle-anchor CX counts: 2: 1,802 / 10,034; 4: 3,198 / 9,304; 9: 4,322 / 9,214; 16: 4,644 / 9,314; 25: 4,768 / 9,206. The anchor implementation uses an exact Gray-path transposition and native seven-control MCX, not Tier 8's extra dirty-wire layout. Minimum Hamming-distance anchor minimizes adjacent swaps within that star construction: 357 for multiplier 2, 332 for each other multiplier. It was rejected on local cost, without claiming all possible cycle synthesis is exhausted. The fixed-mask emitter shares a condition through F–MCX–F and includes both compute and uncompute; the compiled component counts include those costs. The native baseline whole circuit has 2,353 MCX, 145 CCX and 4,052 CX, plus 91 controlled phase, 7 swaps, 28 H and initialization X; counts overlap with the conceptual categories and are not separate additive scoring contributions. The high-control operations and their exact decomposition are the dominant legally modifiable source.

The standalone inverse QFT compiles to 203 CX, depth 108 and 518 total gates on 14 active qubits; state preparation adds one X and 14 H. Measurements and workspace initialization do not contribute two-qubit gates. There is no separately identified arithmetic uncomputation outside the included reversible permutation networks; the F fanout cleanup is included in those networks. Individual MCX, Boolean logic and cross-block cancellation cannot be separated into exact additive whole-circuit contributions after optimization. In particular standalone counts do not sum to the whole circuit. Full compiler output and per-block results are recorded in `docs/evidence/tier09_structural_v3/`.

Exact cancellation was screened by commuting two positive-controlled X gates when their targets coincide or neither target controls the other, and removing identical gates across only such commuting gates. None of the five block sequences lost an operation, and the whole circuit remained 55,999/120,242/168,116/22. This is a bounded local search, not a proof that no rewrite exists. Cross-block multiplication cannot simply be merged: different counting qubits are independent coherent controls, separated by other controlled blocks and followed by the full inverse QFT and measurement. No phase-estimation operations or measurement order were moved. Existing shared predicates and reversible fanout are retained; no new shared predicate was adopted without including its uncomputation. Prior v2 documented 21-qubit canonical fixed-mask at 69,693 CX and 178,514 depth; removing the existing clean wire worsens the primary objective, so it was not adopted. The extra wire doubles the theoretical complex128 statevector capacity from 32 to 64 MiB (actual Aer may optimize idle wires); no new 21-qubit runtime experiment was performed. Prior OSC v5 versus v2 means were 28.23 versus 36.10 seconds and 168.59 versus 170.74 MiB sampled RSS, on cluster nodes with possible load effects. These compare different circuits and are not v3 runtime measurements.

Changing the pivot to the final target produces isolated CX values 1,802, 3,194, 4,318, 4,644, 4,768 respectively. Whole-circuit results above were measured independently, not inferred from their sum. Further anchor selection, alternative shared predicates, cross-block rewrites, and clean-wire resynthesis remain unexhausted.

## Exactness

For a target set S and any pivot p in S, F is the product of CX(p,t) for t in S other than p. Since the controls and targets are disjoint, F commutes with the condition, and F MCX(C,p) F flips exactly all of S when C is true and is identity when false. F is self-inverse, so the choice of p changes no branch, phase or borrowed wire. The existing fixed-mask elimination proves the complete permutation, including padding. Full complex 256-by-256 operators and inverse operators for all five actual controlled blocks were compared against their analytical permutation matrices (all 1,280 control/work inputs); maximum forward error 2.27e-13. This establishes relative phases and entanglement preservation at the logical block level, not merely basis truth tables or SHA agreement.

The existing `test_tier09_advanced_optimization.py` passed 7 tests: public old/new emitted gates across 2,560 control/work basis cases, synthetic small permutation and complete complex tests, plus an Aer synthetic compiled circuit with clean restoration and phase checks. `test_tier09_clean_workspace.py` passed 2 tests, six exact clean-template cases, max operator error 4.01e-15 and max auxiliary leakage amplitude 3.89e-16. The clean contract assumes initialization to zero; no claim is made for arbitrary clean input. Both control states, inverse mappings, identity padding, and relative phases are covered compositionally; phase register preparation, inverse QFT, measurement ordering, and solve logic are unchanged. A dense full 22-qubit unitary was not constructed.

Reproduce screenings with `/tmp/tier09-v3-venv/bin/python -B research/tier09_v3_screen.py`, `research/tier09_v3_pivot.py`, and `research/tier09_v3_verify.py` in a pinned environment; run the two existing tests named above. The screening scripts monkeypatch only their own process and do not alter solution sources. Operator and seed testing overlapped during the first pair, so local timing should not be interpreted as controlled performance evidence. Sampled process-tree RSS may double-count shared pages and miss short peaks.

## Local execution and Checker

Two sequential paired local trials used seeds 1000 and 2000, each one Aer job of 64 shots, max two simulator threads, 512 MiB simulator memory, and a 120-second/1024 MiB worker budget. Actual forwarded seeds and SHA-256 matches were verified; each execution recorded one unique circuit. Results are sampled process-tree peak RSS, not exact allocator peaks:

| Seed | Baseline solve s / MiB | Candidate solve s / MiB | Outcome |
|---:|---:|---:|---|
| 1000 | 17.663 / 144.17 | 19.172 / 143.95 | both hash match |
| 2000 | 17.677 / 144.33 | 18.246 / 143.69 | both hash match |

The two-pair mean is 17.670 versus 18.709 seconds; the sample is too small and subject to load/ordering effects to establish a runtime or memory change. Tests overlapped with the first pair. No further OSC job was justified for this marginal gain.

The unmodified official `check_tier` was also run in a separate Git-archive snapshot of the source baseline plus the changed file whose SHA-256 is recorded above, in a separate bounded worker. It returned **full**, SHA-256 match, metrics **ok**, zero flags, one executed and one unique circuit, and the 55,971 / 120,223 / 168,088 / 22 metrics. Solve took 17.717 seconds, sampled process-tree peak 194.98 MiB, resource state ok, within the official 120-second solve limit; the worker's outer timeout was 370 seconds and RSS cap 1024 MiB. An earlier worktree Checker also passed (18.520 seconds); evidence retains both and does not treat either as a reliability study. The archive result is in `docs/evidence/tier09_structural_v3/isolated-checker.json`. Source fingerprint refers to the research file including comments, with production behavior identical to the locally paired candidate; a comment was added during those runs. The verification did not assert any human reliability review.

**Disposition: INCONCLUSIVE** for replacing v2: correctness and local Checker evidence support this exact change, and all weighted resource metrics are no worse, but only two local pairs are available, both slower, and the gain is about 0.05% in the primary metric. Preserve the baseline as the current candidate; this branch records a Pareto improvement in circuit size pending broader runtime and reliability validation.
