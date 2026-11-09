# Tier 8 advanced reversible synthesis

## Scope and provenance

Baseline is `optimization/tier05-tier08-v2@0988ac44d88d08cc12258f2010afaf792dd53e7b`; frozen v5 `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d` was not changed. On 2026-11-09, `git fetch origin research/tier08-modular-synthesis` returned `couldn't find remote ref`; no latest commit or best candidate from that branch could be recovered. Existing separate research `research/real-circuit-optimization@4d79b7fa66d0acd4786d71be3c3ac2d291618c69` screened GF(2) and commutation on the four real multipliers; source cancellations disappeared on recompilation, and full-circuit resources stayed 42,792 / 123,300 / 130,171 / 18. That evidence does not establish what the unavailable branch contained. The baseline previously passed ten paired seeds against v5 and the official Tier 8 Checker; see `docs/TIER05_TIER08_ADVANCED_OPTIMIZATION.md`.

This branch changes only team-owned `submissions/team3/tier08/modular.py` plus research and documentation. Candidate source SHA-256 is `ae89e63eb178c60774670e86c8e2cb4f1212e2dc8eb0070c8f3e9cc8639e4350`; the final commit containing it is this report's Git commit. The scoring configuration is `[rz,sx,x,cx]`, all-to-all coupling, optimization level 1, transpiler seed 12345; Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4. `solve()` builds 12 controlled powers, 12 counting plus six work wires, 64-shot batches and a maximum of two batches. It transpiles before Aer, so static comparisons apply the solve-time transpilation then the official scoring transpilation. Only the official Checker establishes what the actual Aer execution scored.

## Where the gates go

The executable circuit initializes work to one, applies 12 controlled multipliers and an inverse-QFT core, and measures counting wires. Public multipliers 2 and 4 appear once each, while 11 and 16 each appear five times. A multiplier acts as `m*x mod 35` on 0–34 and identity on padding 35–63. Baseline constructs full public permutation cycles, converts each cycle into endpoint transpositions, and uses forward/reverse Gray paths of adjacent swaps. Each adjacent swap is a controlled MCX6 with two arbitrary dirty counting wires. An isolated baseline exact MCX6 costs 36 native CX, repeated hundreds of times; the reverse-path steps restore Gray intermediates. They implement a fixed reversible permutation rather than a ripple-carry arithmetic network: there is no separate quantum adder or controlled-SWAP block in this implementation. Their uncomputation is included in the MCX/Gray-path totals and must not be counted a second time. The inverse QFT alone compiles to 132 CX / depth 89 / 366 gates on 12 active qubits. Initial preparation and measurement do not justify attributing isolated block costs additively without checking cross-block compiler behavior.

| Public multiplier | occurrences | Baseline isolated 2Q/depth/total | Candidate isolated 2Q/depth/total | Candidate synthesis |
|---:|---:|---|---|---|
| 2 | 1 | 4,212 / 12,171 / 12,816 | 1,804 / 4,582 / 5,205 | fixed mask |
| 4 | 1 | 3,888 / 11,235 / 11,837 | 2,448 / 6,123 / 7,028 | fixed mask |
| 11 | 5 | 3,456 / 9,987 / 10,516 | 2,952 / 8,531 / 8,994 | cycle anchor |
| 16 | 5 | 3,456 / 9,987 / 10,526 | 2,952 / 8,531 / 9,008 | cycle anchor |

Independent isolated QFT and multiplier numbers are diagnostic; whole-circuit results below are directly compiled and, separately, checked. `tier08/README.md` permits classical post-processing but requires quantum-assisted factoring and a circuit executed by `solve()`. The modified files synthesize public modular gates and do not compute factors, look up an answer, change the measurement/order recovery, or edit official challenge code. Enumerating a public toy permutation is exponential classical preprocessing; this is not a scalable modular arithmetic construction and should be disclosed in the presentation.

## Methods and mathematical justification

**Cycle-anchor variant.** For a cycle `(a, p(a), ..., p^(k−1)(a))`, applying transpositions `(a,p(a))`, then `(a,p²(a))`, etc. implements the same cycle for any anchor `a` chosen from the cycle. An endpoint exchange at Hamming distance `d` uses `2d−1` adjacent swaps. Choosing the cycle element minimizing the sum of Hamming distances is an exact finite search over the already generated public cycle; it changes neither permutation, powers nor extracted order. Each adjacent swap retains the existing complete exact dirty MCX. Anchor-only full circuit compiled to **37,464 / 107,908 / 114,109 / 18**; two paired seeds and a separate official check passed (raw safe evidence `research/tier08_advanced/anchor_validation.json`). It remains a valid fallback but is dominated on the measured metrics by the hybrid below.

**Fixed-mask elimination.** Adapted to the six-bit representation from Tier 9's fixed-mask idea, without assuming the two tiers share arithmetic or adding its extra clean wire. Let `T` initially equal the complete modular permutation. With all earlier rows fixed, `y=T(i)` is at least `i` because `T` is bijective. For every bit of `i` absent in the original `y`, apply a positive-controlled X using the fixed mask `y`, obtaining `y|i`; then clear surplus bits using mask `i`. All affected states are at least the currently fixed row, so earlier rows remain fixed. At the end `T` is identity; reverse the self-inverse gates to implement the original full permutation. Adding the external control to every gate makes control 0 identity and control 1 the permutation, with no conditional phase. Unused work wires and the two counting wires are borrowed only by exact MCX templates and restored immediately, even when dirty or entangled. No gate is moved across a phase operation.

The compiler builds the anchor circuit and the fixed-mask circuit and estimates their native CX by summing individually compiled exact MCX-template costs. It picks the lower estimate deterministically for each public permutation; this is a selection heuristic, not a promise that isolated estimates add to a full score. In these instances it chooses fixed masks for 2 and 4 and the optimized cycle anchors for 11 and 16. Full-circuit resources are measured, not inferred by multiplying block savings. The pure fixed-mask screen gave isolated 2Q counts 1,804 / 2,448 / 3,084 / 3,460 for the four multipliers, so its 11 and 16 variants were rejected in favor of the anchor implementations. Previous exact CX-commutation and GF(2) screening did not improve the scored Tier 8 circuit. Sharing controls across powers was not applied: controls differ and borrowing can entangle them, so a valid joint rewrite requires an additional proof. No extra clean ancilla, relative-phase shortcut, or unmeasured larger-qubit candidate is proposed.

## Correctness

`research/tier08_advanced/verify.py` checks all 512 control/work/dirty basis branches for each of the four actual multipliers against the exact identity-extended table and against the baseline. The symbolic branch interpreter treats each MCX template as its exact classical controlled-X; it does not on its own prove phase behavior. `verify_templates.py` independently compares the full complex operator of every actual 1–6 control template, including every dirty input column, with the positive exact MCX permutation: maximum elementwise errors are at most 3.78e−15. Thus all template phases, both external-control values and borrowed-wire restoration are accounted for. A separate random complex 512-amplitude superposition per complete multiplier is compared to the old gate circuit, maximum observed error 2.90e−14 (`verification.json`). Equality of exact primitives and exhaustive basis permutations implies equality on arbitrary complex superpositions and external entanglement, up to numerical test precision; composition preserves every modular power, QFT, work register, dirty counting wires and measurement ordering. These tests do not assert an exhaustively computed dense 18-qubit whole-circuit matrix.

## Whole-circuit comparison and scoring

| Scored metric | Baseline | Hybrid candidate | Change |
|---|---:|---:|---:|
| Two-qubit gates | 42,792 | 33,904 | −8,888 |
| Depth | 123,300 | 96,055 | −27,245 |
| Total gates | 130,171 | 102,561 | −27,610 |
| Active qubits | 18 | 18 | 0 |

Official Simplicity uses best/team ratios weighted 0.4 two-qubit gates, 0.3 depth, 0.2 total gates, 0.1 active qubits; with valid full results the hybrid dominates this baseline on all four metrics. Other teams' best values are unknown, so no competition score is inferred. The official solve and scoring-transpile limits are separate 120-second limits; the complete Checker wall time also includes process startup and scoring.

## Actual execution, validation and recommendation

Two newly run local pairs used actual Aer seeds 801 and 802 injected and verified at `AerBackend.run`, 64 shots, one circuit and the same 120-second per-run limit and 1,536 MiB process-tree limit. All four returned PASS and matching SHA-256. The unmodified official Checker was run on the candidate in isolation and logged the circuit actually passed to Aer: **full**, hash match, valid metrics, **no flags**, one circuit, solve **22.086 s**, total Checker worker wall **23.5517 s**, sampled peak process-tree RSS **395.33 MiB**. The observed official metrics are exactly 33,904 / 96,055 / 102,561 / 18. No full ten-tier Checker was run.

| Seed | Baseline / candidate | solve s A / B | peak sampled process-tree RSS MiB A / B |
|---:|---|---:|---:|
| 801 | PASS / PASS | 30.269 / 22.698 | 445.03 / 312.73 |
| 802 | PASS / PASS | 28.137 / 22.543 | 486.00 / 402.34 |

Mean solve was 29.203 / 22.6205 seconds. These two samples indicate no timeout in this environment, not guaranteed reliability or a stable memory/performance improvement. RSS is a 20 ms sampled sum of process-tree RSS and can miss peaks or double-count shared pages. Tests ran locally on macOS arm64 with Python 3.13.9, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4, two Aer threads; the runner and safe complete records are `research/tier08_advanced/run_validation.py` and `validation.json`. Environment and host contention can change the results. The five existing advanced Tier 5/8 synthetic regression tests also passed. OSC was not needed for these bounded local tests; no OSC computation is claimed.

**Research verdict: ACCEPT.** Preserve the hybrid source as the best measured Tier 8 candidate; it is an exact full-domain construction and improves all three scored gate metrics with the same active-qubit count. For v6, integrate only `submissions/team3/tier08/modular.py`, keeping Tier 8 `solution.py` and `order.py` and other tiers intact, then independently run a larger paired-seed reliability study and the official integrated submission validation before release. The two-seed result does not replace such independent reliability evidence. Review toy-permutation exponential preprocessing and disclose it. The existing `permutation_table` API used by Tier 9/10 is unchanged.

## Reproduction

The source is the final commit on this branch, based on `0988ac4`; no pre-existing production v6 branch was changed. With dependencies pinned in `requirements.txt` and the baseline commit available:

```sh
python -B research/tier08_advanced/verify_templates.py
python -B research/tier08_advanced/verify.py
python -B research/tier08_advanced/global_screen.py
python -B tests/test_tier05_tier08_advanced_equivalence.py -v
```

The verification JSON records both double-compiled full circuits, all 512 branches per multiplier and complex-superposition errors. For the measured runtime protocol, use the separate benchmark-harness checkout at `ab9676749e00da904d0b8076811a2407d3b7205f` in sibling `Quantum-Cryptography-Benchmark-Harness`, and an unchanged baseline worktree at `0988ac4` in sibling `Quantum-Cryptography-Tier05-Tier08-V2`; execute `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier08_advanced/run_validation.py` from this checkout. The bounded harness samples process trees and injects only the requested simulator seed; its official mode invokes the original Checker against Tier 8 only. No secrets, measurement counts, factor values or plaintext are intentionally recorded.
