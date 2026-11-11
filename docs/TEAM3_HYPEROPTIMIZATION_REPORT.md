# Team 3 quantum hyperoptimizer — bounded first study

Date: November 11, 2026. This study follows the additional request to conserve usage and maximize benefit. It delivers modular synthesis/verification infrastructure and concentrates new quantum execution on one high-value Tier 8 candidate. Prior Tier 5, 9 and 10 results are reused at immutable references, not reclassified as new achievements.

## Scope and provenance

Audited runtime: `c4455782ea9388d5897fc27270f42dd3786ed35d`. v6.1: `0c043a40d3ae10b579be312c72a7adfe1e26e9a4`. Frozen final package: `ca7290c7f6b35e37e4ef94f3d5f79110309f594f`. Prior Tier 5: `97fcc0c7d6dec3b7385dc237d47d89d4d6ffd15c`; Tier 9: `d294a5a6f26b8abe96b1117928f8857e95750040`; Tier 10: `7edfe872aec8651ca28e1721ef4e322ba942d113`.

The fetched v6.2 integration report at `aee41fb328027f8927a55d65c68e8a3e30332697` contains an author-run integrated Checker result and explicitly says separate source/package approval is pending. This study does not assume v6.2 is independently accepted and modifies none of its files or references. No final ZIP or competition submission is created. All edits are research/report files on this new branch.

## Framework and implemented coverage

The typed IR distinguishes exact unitaries, relative-phase unitaries and classical reversible action, with positive/negative controls, exact discrete phase operations, affine transforms, public permutations and ancilla-restoration contracts. A Boolean result cannot certify a phase-sensitive replacement. Runtime contracts are checked by dedicated verification; type declarations alone do not prove them.

Generic synthesis supports mixed-polarity fixed-row elimination, forward and inverse tables, complementary-cube cancellation, predicate-sharing target fanout and general CNOT-coordinate conjugation. Phase-sensitive verification compares full controlled complex operators and inverses without fitting a control-branch phase. Bounded SMT supports small exact monomial windows, including XOR-linear/Toffoli/mixed-control/multi-target operations and diagonal phases in multiples of π/4; it constrains both permutation and phase and independently replays results. Only UNSAT shorter bounds justify minimum gate count within a supplied library. SMT tests were not promoted into complete tiers without compilation and execution evidence.

The framework is intentionally an initial implementation. Global A*, beam search, meet-in-the-middle, unrestricted row-order search, dense affine expansion, arbitrary-angle phase optimization and new Tier 5/9/10 circuit searches are deferred. Existing Tier 5 compute–phase–uncompute/GF(2) proof and the Tier 9/10 acceptance evidence are referenced rather than duplicating those researchers' experiments. No claim of a fully general or globally optimal superoptimizer is made.

## New Tier 8 synthesis

The public permutation is P(x)=d·x mod 35 for x<35 and P(x)=x for padding 35–63. Row elimination fixes the complete permutation rather than only the orbit reached from work |1⟩. With earlier rows fixed, T(i)≥i. Choosing a control mask contained in T(i) and numerically at least i ensures a controlled target flip cannot affect an earlier row. Reversing these self-inverse gates implements the original table. Inverse-table synthesis is reversed back to the same forward operation.

Bit permutation and XOR coordinate changes convert positive guards into exact mixed-polarity controls in the original wire coordinates. X wrappers implement negative controls. Identical predicates share target fanout: F; MCX; F⁻¹. Complementary cubes with one common target obey C·l XOR C·¬l=C; identical consecutive cubes cancel. All emitted X/CX/MCX blocks are complete exact constructions, so Boolean equality is supplemented by an explicit phase-preserving gate argument and complex-operator tests.

For a sparse general linear map A, the compiler synthesizes A P A⁻¹ and emits A before that controlled core, then A⁻¹ afterward. Consequently the control-off path is A⁻¹A=I; the control-on path is P. Both affine networks are included in actual compilation and proxy cost. No counting qubit is treated as clean. The source block declares the original two borrowed wires but does not touch them; exact native MCX synthesis may use available wires under its restoration contract. Counting controls, 18-wire architecture, QFT control reversal, measurement layout, 64-shot batches, bounded retries and measurement-based order/factor recovery are unchanged.

## Search budget and plateau

There are 36 deterministic coordinate configurations (seed 20261112), four public multipliers and four forward/inverse-clear options: 576 cheap symbolic/proxy proposals. Every proposal is checked over all 64 work values. The first 24 use bit order/polarity; the last 12 add one or two CNOT coordinate gates. Candidate/proposal hashes support deduplication and completed-checkpoint reuse. Each final block independently minimizes a heuristic MCX proxy; the proxy is not an admissible global lower bound.

| Prefix | CX | Depth | Total gates | Active qubits |
|---:|---:|---:|---:|---:|
| 12 | 11,596 | 27,443 | 32,731 | 18 |
| 24 | **11,316** | **26,509** | **31,778** | **18** |
| 36 | 11,316 | 26,509 | 31,778 | 18 |

The final sparse-affine proposals did not improve the best result; all selected blocks use no additional affine CNOTs. Search stopped at this plateau. Three unique complete-circuit prefixes were scored; six compilations were actually performed including confirmation against Tier 8's basis-first execution pipeline. Both pipelines gave the same rows, but the retained implementation explicitly follows the real execution path. Four small framework regression tests passed. New official quantum validation is limited to the Tier 8 baseline and one finalist, followed by five paired seeds. No unbounded compute job or OSC allocation remains running.

The pure-SMT examples validate the small-window tool, not new whole-tier savings. Dense affine search, broad nonlinear SAT and additional Tier 5/9/10 candidates were not run. These are deferred methods, not failed correctness claims. The sparse-affine plateau and the absence of a new improvement in other tiers are retained honestly.

## Mathematical verification

The four complete 128×128 control/work complex operators cover both control branches and all padding states, with maximum forward/inverse error about 6.02×10⁻¹⁴ and no phase fitting. The untouched borrowed-wire extension is an identity tensor factor. A complete 18-qubit prepared-state comparison with the accepted runtime circuit gives maximum amplitude error about 9.62×10⁻¹⁴; measurement mapping is preserved. This is a compositional proof plus finite numerical evidence, not a dense 18-qubit operator proof or proof of every transpiler version. Matching hashes provide output correctness evidence separately.

## Official and reliability results

New validation source: `38129a2c34a6585ed76653090e438c9254ec301d`. The unmodified official Tier 8 Checker returned **FULL**, hash match, actual circuit execution, valid metrics, no flags and no timeout for baseline and candidate. Five paired seeds 8100–8104 passed **5/5 on each side**, with actual Aer seed forwarding and completed jobs recorded. [Safe execution evidence](../research/hyperoptimizer/results/validation.json).

| Local quantity | Baseline | Candidate |
|---|---:|---:|
| two_qubit_gates | 33,904 | 11,316 |
| depth | 96,055 | 26,509 |
| total_gates | 102,561 | 31,778 |
| active_qubits | 18 | 18 |
| solve_seconds | 22.759400 | 6.341000 |
| compile_seconds | 0.304809 | 0.106463 |
| peak_rss_mib | 364.950000 | 174.881250 |
| mean_aer_job_seconds | 22.537790 | 6.273028 |

Environment: Python 3.12.16, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4, local macOS ARM64. Compiler timings are individual static measurements, not per-seed compiler phase profiles. Solve includes construction, native compilation, Aer and classical recovery. Sampled RSS sums process-tree memory every 20 ms and may miss peaks or double-count shared pages. These samples suggest a local simulator improvement, not quantum hardware speedup or a future reliability guarantee. No new OSC experiment was performed.

## Per-tier verdicts and score opportunity

| Tier | Best retained CX / depth / gates / qubits | Evidence status | This study |
|---:|---|---|---|
| 5 | 10,950 / 19,703 / 28,363 / 19 | RELIABILITY_VALIDATED | Prior acceptance reused; no new candidate |
| 8 | 11,316 / 26,509 / 31,778 / 18 | RELIABILITY_VALIDATED | New ACCEPT_RESEARCH |
| 9 | 34,186 / 71,632 / 102,830 / 22 | RELIABILITY_VALIDATED | Prior acceptance reused; no new candidate |
| 10 | 38,823 / 92,604 / 111,337 / 19 | RELIABILITY_VALIDATED | Prior acceptance reused; no new candidate |

For Tier 8, the 2.25-point pool and official weights give a maximum hypothetical gain of **1.398896 Simplicity points** against fixed unknown competitor minima. For each positive metric x→y, the maximum ratio gain is 1−y/x, attained at rival minimum y. If we already lead every affected metric, gain is zero. No opponent data, probabilities or actual competition score are inferred.

Updating only Tier 8 in the user-supplied forecast gives **106,626 CX, 225,305 summed per-tier depth and 303,768 total gates**. This is arithmetic over isolated results and the supplied forecast, **not a new integrated Checker result**. It does not establish any overall research-stage target as achieved by a combined submission. The historical forecast itself may differ across compiler environments; an integrated run is required before quoting official aggregate metrics.

## Resource policy, failed directions and recommendation

**Overall verdict: ACCEPT_RESEARCH for the new Tier 8 candidate only.** Tier 5/9/10 retain their previously documented acceptance; this study contributes no new candidate for them. The large Tier 8 gain justified the small validation budget; no new broad search was needed after its sparse-affine plateau. The final baseline profiling adds one static compilation, for seven actual full resource compilations including pipeline confirmation, two official single-tier checks and ten paired executions. Every job has completed.

No sparse general affine configuration improved the selected bit/polarity result. No solver-derived local replacement was promoted into a tier without a measured whole-tier improvement. Dense affine, beam/A*/meet-in-the-middle, broad nonlinear SAT, further Grover joint-reflection synthesis and targeted Tier 10 heavy-block searches remain opportunities, not completed experiments. This is a deliberate usage-saving scope boundary. The typed IR and exact small-window APIs can support later adapters without pretending to implement every planned algorithm.

The [Pareto data](../research/hyperoptimizer/results/pareto.json) includes CX/depth/gates/qubits, solve time, compilation time, sampled memory and cache bytes. Audit/reproducibility risk is categorical and left unordered; no fabricated risk score is mixed into measured quantities. Unmeasured cross-tier performance stays unknown. Research cache size and packaging requirements prevent treating fewer gates as automatic overall dominance.

Recommend independent Tier 8 review and a separately authorized integration task. Preserve the 18-qubit layout and exact cached operators, package required runtime assets explicitly, then run the integrated unchanged Checker and focused reliability checks. Do not overwrite the current final ZIP or any active RC. No integration, merge or competition upload was performed.

[Reproduction instructions](../research/hyperoptimizer/README.md) cover tests, cache regeneration, operator checks and isolated official/paired trials. [Source/cache digests](../research/hyperoptimizer/results/digests.json) bind the deliverables; the execution JSON separately binds the exact evaluated source commit and wrapper.
