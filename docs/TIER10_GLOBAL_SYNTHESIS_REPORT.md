# Tier 10 global quantum group-operation synthesis

Research date: November 11, 2026. Runtime baseline: `c4455782ea9388d5897fc27270f42dd3786ed35d`. Final package `ca7290c` remains read-only. Search and validation source snapshot: `160641690c647b508205e4ea0129eb83cc14da6f`. All modifications are confined to this report and `research/tier10_global/`.

## Result and scope

The selected research method is exact mixed-polarity, coordinate-conjugated reversible row elimination with shared-predicate fanout. It preserves all 19 wires and the unchanged measurement-driven discrete-log recovery. The selected whole executed circuit uses **38,823 CX**, below all three requested CX milestones. The official Tier 10 Checker reproduces the metrics and returns FULL. Detailed final validation statistics appear below.

This is a resource improvement, not a hardware speedup. No release branch, supplied oracle, official tool, production solution, other tier or ZIP was modified. No OSC jobs were run. Local multi-seed tests and scoped mathematical evidence do not guarantee future performance or replace independent release auditing.

## Precise synthesis construction

Let P be the public work permutation: multiply by the given public multiplier modulo 83 for work integers below 83, and fix padding 83–127. For a bit permutation π and constant XOR mask f, define the invertible affine coordinate change E(x)=π(x) XOR f. Synthesize the conjugate E P E⁻¹ using row elimination, then map every emitted gate back through E⁻¹. Thus the emitted network realizes P on the entire encoded domain; E is a compiler coordinate transformation, not an additional quantum register or a secret lookup.

Row elimination maintains a permutation table T and fixes rows in increasing order. When rows below i are fixed, y=T(i)≥i. A positive guard m contained in y with m≥i cannot affect any earlier row: any z satisfying z AND m=m obeys z≥m≥i. Target bits lie outside the guard. Set missing bits, clear surplus bits with the appropriate safe guard, and reverse the self-inverse gate sequence once the table is identity. The inverse-table alternative reverses its result again. Bit relabeling maps targets and control masks back, while XOR conjugation turns some controls into negative literals. These are exact mixed-polarity Toffoli operations, implemented by X wrappers around exact MCX gates.

For consecutive operations with the same predicate, XOR their target masks. Choose an existing target pivot p and fan out p before and after the controlled pivot flip: F; MCX; F⁻¹. It flips all intended targets exactly when the predicate holds, even if the pivot starts in an arbitrary superposition. It requires no clean ancilla. The local ESOP identity C·l XOR C·¬l=C merges adjacent complementary cubes with a common target; identical adjacent cubes cancel. It does not authorize reordering noncommuting gates or dropping relative-phase corrections.

Every work gate receives the original external counting-qubit control. With that control off, the complete block is identity, including the X wrappers and fanout pairs. Different modules retain distinct controls. The construction never derives the unknown exponent, enumerates exponent candidates, or changes the public parameters, inverse QFT, classical bit mapping, 128-shot batch size, two-batch bound, or evidence-based recovery.

## Search coverage and cost interpretation

The deterministic seed is 20261111. Ninety-six coordinate configurations are explored: identity, random bit permutations, then mixed bit permutations/XOR polarities. Each coordinate configuration has four internal forward/inverse and clear-mode synthesis choices per unique public multiplier. Consequently 96 is the number of outer configurations, not the number of individual module networks. All generated networks pass exhaustive symbolic work-domain checks before ranking. Equivalent operation fingerprints are deduplicated; best public module networks are cached. Seven full-circuit checkpoints, a last-pivot alternative and native compilation-level alternatives form a bounded evaluation funnel. Only the level-1 finalist receives Checker and multi-seed evaluation; the baseline is the paired control. Search stops after reaching the bounded budget and the ambitious target; no global optimality is claimed.

The cheap MCX proxy selects networks but cannot predict whole-circuit Qiskit costs exactly. Screens follow the actual solver pipeline: transpile to Aer, then apply the official level-1 scorer with seed 12345 and basis `rz,sx,x,cx`. Candidate source has no additional ancillas. Candidate data is a precompiled public-operation cache; the offline synthesis time and exponential 128-entry truth tables are additional classical preparation, not free scalable arithmetic.

The largest cost is controlled reversible group multiplication. Removing all multiplier blocks from the candidate leaves 60 CX for the two inverse-QFT bodies and preparation; removing QFT leaves 38,763 CX. These particular totals agree additively, but removal deltas and isolated templates are not generally additive because compiler context changes. `profile.json` ranks each of the twelve public power blocks by full-circuit removal delta. `search.json` records the baseline MCX arity histogram; `alternatives.json` records native operation counts, fanout/X overhead and dirty decomposition costs. Compute/uncompute here refers to exact predicate fanout and negative-literal wrappers, not erasing the intended modular work output.


### Ranked whole-circuit block attribution

Each row is the CX reduction when that one block is removed and the remaining complete circuit is recompiled. These are diagnostic removal experiments, not valid alternative solvers or additive isolated gate counts.

| Rank | Public power block | Baseline marginal CX | Candidate marginal CX |
|---:|---|---:|---:|
| 1 | tier10_controlled_A_power_32 | 9566 | 10666 |
| 2 | tier10_controlled_g_power_32 | 6438 | 7236 |
| 3 | tier10_controlled_A_power_8 | 4014 | 3634 |
| 4 | tier10_controlled_g_power_1 | 3632 | 3518 |
| 5 | tier10_controlled_A_power_16 | 4124 | 3422 |
| 6 | tier10_controlled_g_power_2 | 3960 | 3378 |
| 7 | tier10_controlled_A_power_2 | 4342 | 3348 |
| 8 | tier10_controlled_g_power_16 | 3866 | 3336 |
| 9 | tier10_controlled_A_power_1 | 4008 | 3310 |
| 10 | tier10_controlled_A_power_4 | 4010 | 3134 |
| 11 | tier10_controlled_g_power_8 | 3488 | 2849 |
| 12 | tier10_controlled_g_power_4 | 3054 | 2106 |

## Distinct approaches and unsuccessful probes

| Approach | Investigation and outcome |
|---|---|
| Global fixed-mask/generalized row elimination | Conjugate each complete multiplier under shared coordinate-search families; mixed polarity substantially improves the selected whole circuit. No unjustified cross-control permutation merge is used. |
| Shared control predicates | Exact grouped-target fanout reuses a predicate within a block without clean workspace. Last-target pivot measured 38,831 CX versus 38,823; reject this variant. |
| Cycle anchors and ordering | Exact minimum-distance cycle-anchor method from Tier 8 was tested on a representative public multiplier. Isolated 11-wire dirty-ancilla construction costs 7,052 CX versus 4,634 for the selected eight-wire block. Not promoted to full execution. Different disjoint cycle orderings are possible but were not exhaustively searched. |
| PPRM / ANF and ESOP | Exhaustive Boolean Möbius-transform reconstruction of output XOR input on a representative multiplier yields 226 terms, including 92 dependent on the target bit. Naive in-place extraction is invalid; an out-of-place evaluator needs seven extra targets (26 total wires), outside this budget. Local complementary-cube ESOP merging and mixed polarities are implemented; unrestricted ESOP minimization/shared nonlinear ancillas remain unimplemented. |
| Cross-block cancellation | Equal work predicates with different external controls do not cancel. A flattened logical scan finds adjacent self-inverse pairs, principally wrapper operations; ordinary native compilation already handles local cancellation. No unproved commuting rewrite is promoted. |
| Dirty ancillas | Exact M15 templates borrow other counting wires and restore them; no zero-state assumption. Explicit borrowing gives 38,823 CX and depth 92,591, a 13-layer static difference only; not promoted over the already validated no-extra-ancilla source path. |
| Compilation levels | Native levels 2/3 give 38,767 CX, depth 92,283 and 110,097 gates under the unchanged level-1 scorer. These 56-CX additional savings are static-only and not claimed as accepted results. Native level 0 matches the selected level-1 metrics. |

These probes are scoped: they do not exhaust every algorithm family or certify a scalable synthesizer. Network gates and selected mixed-polarity controls preserve phase by construction; relative-phase-only substitutes are never used. Work may remain entangled as required; temporary borrowed state must be restored.

## Mathematical and execution evidence

`equivalence.json` checks complete 256×256 complex operators and inverse operators for every distinct selected public controlled multiplier, including all padding values and both control branches. It compares amplitudes directly without fitting global phase. This independently tests the emitted X/MCX/fanout network against the analytic modular permutation, beyond symbolic search checks. Full 19-qubit statevector comparisons cover the actual prepared input and one deterministic random complex input. They are finite full-system tests, not a dense 2¹⁹×2¹⁹ operator proof. Measurement mapping q[j]→c[j] is checked separately.

`validation.json` records the exact committed research source, public-network digest, wrapper digest, pinned benchmark-harness revision, package versions, actual forwarded Aer seeds, finished jobs, hash matches, official metrics, solve times and sampled process-tree peak RSS. It retains every trial and does not save raw measurements, recovered exponents, keys or plaintext. The official 120-second solve/transpile limits remain unchanged. Some local validation overlapped the operator/statevector test; timings are load-sensitive observations, not controlled causal performance estimates. RSS is sampled every 20 ms and may miss peaks or double-count shared pages.

## Final measured comparison

| Metric | Baseline | Candidate | Reduction |
|---|---:|---:|---:|
| two_qubit_gates | 46,910 | 38,823 | 17.24% |
| depth | 109,763 | 92,604 | 15.63% |
| total_gates | 132,023 | 111,337 | 15.67% |
| active_qubits | 19 | 19 | 0.00% |

Official baseline and candidate: FULL, hash match, valid metrics, no flags. Ten paired seeds 1000–1009: baseline 10/10 PASS; candidate 10/10 PASS. Every run actually forwarded its requested seed and completed its recorded Aer jobs.

| Local quantity | Baseline | Candidate |
|---|---:|---:|
| mean_solve_seconds | 3.9767 | 6.0055 |
| mean_sampled_peak_rss_mib | 118.1859 | 129.2219 |

Maximum selected-block complex-operator error: 1.624e-13. Maximum inverse error: 1.631e-13. Both prepared and random full-system amplitude comparisons returned maximum error 0.0 in the recorded native simulation. This exact observed equality is not a claim of formal verification of all compiler behavior.

## Simplicity opportunity and decision

Tier 10 has a 2.625-point pool. For each positive reduction x→y and a fixed unknown rival minimum c, the maximum possible ratio gain is 1−y/x, attained when c=y. Summing official weights gives an abstract maximum of **0.386381 Simplicity points** for this candidate. If we already lead all affected metrics, the gain is zero. This interval is not an expected value or a known competition score. Actual eligibility and rival minima determine the outcome.

**Recommendation: ACCEPT_RESEARCH for the 38,823-CX level-1 candidate.** Full-domain phase-sensitive checks, actual executed-circuit FULL/hash/metrics evidence, ten paired seeds and sub-timeout local solves support research acceptance. All scored metrics improve or tie. Local simulation is slower by a material relative amount; the observed absolute increase is a few seconds with substantial margin to 120 seconds. We accept that tradeoff for research, not as proof of portable runtime. No independent auditor has yet approved this new candidate, and no OSC comparison was performed.

Before any submission consideration, obtain independent mathematical/runtime review on the target environment, confirm the generated public-operation cache and integration path, rerun relevant integrated checks, then rebuild and audit a separately authorized final artifact with a new digest. Preserve the currently accepted final package as fallback. No release integration or resubmission is performed here.

The six-dimensional Pareto record is in `research/tier10_global/pareto.json`. Static screens have unknown simulation time and memory; their resource/compilation frontier must not be presented as a fully measured runtime frontier. Baseline and finalist trade lower quantum resources against longer simulator time, so neither dominates the other across all measured dimensions.

Reproduce with [the research README](../research/tier10_global/README.md). All evidence is local CPU simulation, not quantum hardware.
