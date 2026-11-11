# Tier 5 extreme Grover circuit synthesis

Research date: November 11, 2026. Baseline: `c4455782ea9388d5897fc27270f42dd3786ed35d`. This branch is research-only. Production files, official tools/oracles, frozen final ZIP, v6.1 integration and other tiers are unchanged. No OSC jobs or hardware runs were performed.

## Selected construction

The strongest tested configuration combines relative-phase compute/inverse pairs, a fused quadratic mask transition, shared-target fanout, level-2 native precompilation, and the existing exact GF(2) resynthesis. It keeps **19 qubits, 25 Grover iterations and 128 shots**. Measurements still select keys; only measured candidates enter the unchanged public-prefix and decryption checks. No exhaustive classical key search is used by construction or recovery.

The new phase oracle is A⁻¹ Z A in operator notation (chronological A, Z, A⁻¹). A computes the first-byte comparison into the flag and leaves the second-byte mask in the work register. Z is the original exact diagonal phase mark, implemented by H on the flag, exact dirty-ancilla MCX8, then H. The public S-box/permutation inverse is folded into target constants exactly as in the accepted baseline.

### Why relative phases cancel

Let A map each basis state x to exp(iφ(x))|f(x)⟩, with f the required reversible computation. For diagonal Z with entries z(y), A⁻¹ Z A maps |x⟩ to z(f(x))|x⟩. The phases φ cancel exactly. Thus relative-phase Toffolis and the complete relative-phase dirty comparator may be used inside A when the actual inverse of A follows the diagonal mark. An unpaired relative-phase replacement of the central Z implementation would be invalid and is not used.

The relative comparator uses six borrowed key wires, not six clean ancillas. Its complete synthesis restores those dirty wires. The relative Toffoli is checked as a complex monomial operator with the correct classical permutation. The existing complete exact central comparator is retained. The diffuser uses the baseline's clean workspace only after oracle restoration, including its conventional global π phase. No extra qubit or modified iteration count is introduced.

### Fused masks and Boolean algebra

Each public mask bit is a degree-two algebraic-normal-form polynomial: key-bit XORs and one quadratic key product. The transition from mask 0 to mask 1 is their XOR. Duplicate monomials cancel over GF(2); the remaining terms are grouped by identical key controls and XORed into their target work bits. This is an ANF/ESOP-style rewrite of the supplied public arithmetic, not solving those equations for a key.

For one control predicate and several targets, a fanout F from one existing target, followed by a relative-phase controlled pivot flip and F⁻¹, has the required classical multi-target permutation. Its possible phases are confined to A and removed by A⁻¹. Group order and pivot choice are searched because they affect subsequent basis synthesis and GF(2) windows. The selected ordering reverses the sorted predicate groups and uses the last target as pivot. Workspace restoration and phase are verified below.

## Bounded search and resource attribution

The deterministic search evaluates eight combinations of mask/comparator relative phases and native levels 1/2, three additional level/GF(2) choices, and four fused-mask ordering/pivot choices: 15 whole-circuit configurations. One additional phase-polynomial screen gives 16 complete-circuit resource measurements, below the requested ceiling of 20. Three component compilations and a bounded two-depth SMT probe are far below their budgets. One finalist is promoted to official and five-pair seed validation. QPY/configuration fingerprints support cached duplicate evaluations. All scoring compilations use the unchanged official basis, level 1 and seed 12345.

| Configuration | CX | Depth | Total gates | Active qubits |
|---|---:|---:|---:|---:|
| Verified baseline, GF(2) | 14,552 | 28,132 | 40,938 | 19 |
| Relative masks, exact first comparator, native L2 | 11,100 | 22,953 | 31,030 | 19 |
| Relative masks and comparator, native L2 | 11,000 | 22,278 | 30,263 | 19 |
| Fused masks, ascending groups / first pivot | 11,025 | 19,378 | 28,413 | 19 |
| Selected fused masks, descending groups / last pivot | **10,950** | **19,703** | **28,363** | **19** |

The ascending-group alternative has slightly better depth but more CX; it remains a static Pareto tradeoff rather than an independently runtime-validated finalist. The selected candidate reaches below 13,000 and below 11,000 CX; it does not reach 10,000 or 8,000.

Isolated official-basis costs before whole-circuit optimization: original oracle 540 CX, candidate oracle 424 CX, diffuser 48 CX. The original oracle therefore dominates the basic 588-CX iteration. The current baseline reduces 25×588=14,700 CX to 14,552 through GF(2) windows. These isolated values are not an additive attribution of the optimized candidate: compilation boundaries, repeated-iteration cancellation and native L2 alter costs. In the selected whole circuit, the GF(2) pass records 125 accepted windows and removes 800 native CX before final scoring. It verifies equal binary linear maps for each replacement; positive CNOT matrices preserve relative phase exactly, including on externally entangled wires.

## Other methods, limits and rejected directions

- **Phase-polynomial optimization:** consecutive CX/RZ windows on at most five wires are represented by linear parity masks and accumulated angles, resynthesized and compared as complete complex operators before accepting reductions. No additional CX-saving window was accepted for the finalist; the whole result remains 10,950 CX. This is a bounded local pass, not unrestricted phase-polynomial minimization.
- **Mixed polarity:** public equality X wrappers are retained around the mask comparisons; no hidden solution is encoded. The work-target pivot choice and ordering are varied without altering predicates.
- **Exact Toffoli/MCX:** exact central dirty MCX and clean-work diffuser remain. Relative-phase operations are permitted only in the proven conjugation context, never as standalone substitutes for an exact phase mark.
- **Cross-iteration rewriting:** full 25-iteration compilation and GF(2) runs exploit eligible boundaries. No attempt is made to shorten Grover's iteration count or commute gates through noncommuting reflections without proof.
- **SMT-guided synthesis:** a safe synthetic three-wire CNOT block is reduced from four gates to one; length zero is UNSAT, length one SAT, under a two-second-per-query cap. Its complete complex operator is checked. This demonstrates bounded exact linear synthesis but provides no additional measured production savings; expanding SMT to nonlinear whole-oracle synthesis was not justified after the finite search.
- **Prior 22-qubit design:** ten documented OSC solves took roughly 148–158 seconds and exceeded the unchanged 120-second limit, despite matching independently computed hashes. An extra three dense statevector wires can increase state storage by eightfold, while decomposition and backend behavior also matter; width alone is not a causal runtime proof. The present candidate retains 19 qubits, so that rejected architecture is not repeated.

The prior timeout evidence is `aed4e77:docs/TIER05_CLEAN_ANCILLA_OSC_VALIDATION.md`; accepted GF(2) provenance is `0134d0d:docs/TIER05_FINAL_SELECTION.md`. Finite compiler heuristics and this search do not establish global gate optimality or asymptotic scalability.

## Correctness evidence and retained failures

[Equivalence evidence](../research/tier05_extreme/equivalence.json) checks all 1,024 key inputs of the fused Boolean transition. A nonzero-amplitude complex superposition over every key is compared with the public expected phase predicate; this tests marked and unmarked phase action and clean-workspace restoration without recording which keys are marked. Test-only classical enumeration is never used by the solver. The local RCCX complex operator, an arbitrary-workspace oracle state, the full compiled 25-iteration state and measurement mapping are checked separately.

An initial full-state test failed with a raw amplitude difference around 0.765 despite probabilities agreeing. The diagnostic identified a test-wrapper issue: Aer applies circuit-global phase before `set_statevector`, whose initialization overwrites it. The corrected helper compiles the circuit, removes known global-phase metadata before initialization, and multiplies the resulting state by that known phase afterward. It does not infer or fit a phase from the answer. The corrected full-Grover difference is approximately 6.18×10⁻¹², the oracle clean-phase error approximately 6.65×10⁻¹⁶, and workspace leakage approximately 2.99×10⁻³⁰. The arbitrary-workspace oracle state agrees to about 2.99×10⁻¹⁷. These are finite statevector checks plus the monomial conjugation argument, not a dense 19-qubit operator proof.

The first isolated candidate Checker attempt failed before any circuit execution with ImportError: an eager research import created a circular module dependency. That failure is retained in `validation-attempt1.json`. The corrected disposable wrapper imports the builder lazily. It changes no gate network, search result or production file. A passing plaintext hash alone is never used as a unitary-equivalence argument.

## Official execution and reliability

Validated source snapshot: `0126267863e1bfe58b0fe8933fcb4cd943d933e7`; cache/config and wrapper digests are in [validation.json](../research/tier05_extreme/validation.json). Environment: Python 3.12.16, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4, macOS ARM64. The baseline official result is reused from the first attempt; the candidate has a new successful official run. In total, three official checks were invoked: baseline pass, candidate import failure, corrected candidate pass.

**Official result: FULL, SHA-256 match, actual Aer execution, valid metrics, zero flags, no timeout.** Five independent paired seeds 5100–5104 passed for both versions: **5/5 baseline and 5/5 candidate**. The pinned harness records actual forwarded seeds, completed Aer jobs and safe hash results. Each observed run uses one 128-shot circuit.

| Quantity | Baseline | Candidate |
|---|---:|---:|
| two_qubit_gates | 14,552 | 10,950 |
| depth | 28,132 | 19,703 |
| total_gates | 40,938 | 28,363 |
| active_qubits | 19 | 19 |
| mean_solve_seconds | 13.806400 | 13.950400 |
| mean_aer_job_seconds | 12.830031 | 13.162540 |
| mean_sampled_rss_mib | 212.893750 | 205.037500 |
| Static native transpilation + GF(2), seconds | 1.035774 | 0.719296 |
| Static native + scoring compilation, seconds | 1.117414 | 0.770730 |

Compilation values are single static screen measurements, not per-seed phase timers. Solve time includes construction, compilation, GF(2), simulation and post-processing. Aer job elapsed includes backend overhead. Process-tree RSS is sampled every 20 ms and can miss short peaks or double-count shared pages. No broad speedup or memory guarantee is inferred. Official solve/transpile limits remain 120 seconds; paired workers additionally retain a 120-second outer limit. Five seeds are finite evidence, not a zero-failure guarantee.

## Simplicity and recommendation

Tier 5 has a 1.5-point pool. For positive metric reduction x→y and a fixed unknown rival minimum, maximum possible ratio improvement is 1−y/x, attained when the rival minimum equals y. The weighted maximum for this candidate is **0.375498 points**. If the baseline already leads every affected metric, the gain is zero. No actual rival metrics or probabilities are assumed; this is an abstract upper bound, not a predicted official gain. All four official metrics improve or tie for the selected candidate.

**Verdict: ACCEPT_RESEARCH.** The finalized 10,950-CX candidate has phase/restoration evidence, actual official FULL/hash/metrics confirmation, unchanged width and algorithm, and five paired passes under the official timeout. Static alternatives with slightly lower depth or unverified runtime are not separately accepted. The [Pareto record](../research/tier05_extreme/pareto.json) keeps unknown runtime values null and distinguishes static resource/compilation tradeoffs from fully measured baseline/finalist performance.

This is not authorization to replace a frozen release. Before integration, obtain independent review, package the research emitter as a self-contained production module, rerun the appropriate integrated Checker/reliability checks and audit a newly built artifact. The current prototype uses a disposable research wrapper and is not itself a final submission package. Existing final ZIP, v6.1 branch and all production code remain unchanged.

See [reproduction instructions](../research/tier05_extreme/README.md). The deterministic search, exact tests, failure records, component data and safe trial results are retained. No 10,000-CX or 8,000-CX success is claimed.
