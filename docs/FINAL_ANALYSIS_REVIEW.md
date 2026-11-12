# Final Analysis Review — Team 3 v6.3

Review date: 2026-11-11. Target: 20-point Analysis pool
(12 classical-versus-quantum cost/scaling, 8 hardware or noise discussion).

## Bottom line

The existing write-up has the **right instincts** — it separates query complexity from
gate count, warns that toy instances are brute-forceable, and discusses connectivity,
decoherence, readout and fault tolerance. It is **not yet a full 20-point analysis**:
there is no quantified comparison table, no explicit error/resource model, and the
"tradeoffs" are described rather than analysed. The corrected draft in
`docs/final-drafts/WRITEUP.md` adds the missing table and quantitative framing without
inventing hardware data.

## Rubric assessment

| Criterion | Points | Current state | Gap |
|---|---:|---|---|
| Classical vs quantum cost and scaling | 12 | Several strong paragraphs; correct asymptotic statements | No per-tier cost table; no explicit query-vs-gate accounting; scalability of table synthesis only briefly noted |
| Hardware run or noise discussion | 8 | Clear "Aer is not hardware" paragraph; names error sources | No quantitative error budget, no routing/overhead estimate, no fault-tolerance resource estimate |

**Readiness:** partial. The discussion is honest and technically correct but reads like
a limitations section rather than an analysis. Draft additions should move it toward
the upper half of the pool; no score is guaranteed.

## What should be added (and is now in the draft)

### 1. Per-tier classical/quantum comparison table

A compact table with:

- classical baseline (queries, checks or brute-force size),
- quantum work actually used (oracle calls, shots, controlled blocks),
- asymptotic note,
- why the toy size makes the comparison non-decisive.

The draft uses: BV 24 queries vs 1 oracle call; DJ `2^{n-1}+1` worst case vs 24 calls;
Simon `O(2^{n/2})` vs 32–128 shots; Grover `O(2^10)` vs 25 iterations; Shor trial
division trivial for 35/77; DLP brute force 41 vs 12 blocks. It also states that the
Tier 8/9 table synthesis and Tier 5 reversible oracle dominate circuits and do not
scale.

### 2. Query complexity vs circuit cost

Make explicit that:

- Grover's `O(√(N/M))` counts oracle queries, not compiled two-qubit gates.
- Shor's polynomial order finding assumes efficient reversible modular arithmetic; a
  `2^w` permutation table is exponential preprocessing and is not that.
- A smaller scored circuit can be a slower solver (Tier 5's 22-qubit 13,802-gate
  candidate timed out; Tier 9's extra ancilla reduced CX but increased solve time).
- Shot counts, oracle calls and circuit executions are separate from the scored
  circuit; Simplicity only measures the largest executed circuit.

### 3. Hardware and noise analysis

The draft should and does cover:

- current two-qubit error rates (`10^-3`–`10^-2`), readout error, coherence limits;
- connectivity forcing SWAP routing, which raises CX and depth;
- calibration-aware transpilation, dynamical decoupling, error mitigation;
- fault tolerance: surface code, thousands of logical qubits and millions of
  Toffoli-equivalent operations for cryptographic sizes, orders-of-magnitude physical
  overhead;
- no hardware run is claimed, so this is a noise/scaling discussion, not an experiment.

If the team can obtain even a small hardware run (e.g., a 5–20 qubit toy circuit on a
free backend) with calibration data, that would strengthen the 8-point criterion. It is
optional; without it, the quantitative noise discussion is the safer path.

### 4. Optimization tradeoffs

Current text lists changes; the analysis should explain the tradeoff axes:

- **Width vs gates:** Tier 9's clean workspace reduces CX but adds an active qubit.
- **Gates vs runtime:** Tier 5's clean-ancilla candidate had fewer gates but timed out;
  circuit size is not simulation time.
- **Compiler vs algorithm:** Tier 7's level-2 pretranspilation changes depth/gates but
  not the algorithm or CX; it is a compilation result.
- **Preprocessing vs runtime:** Tier 8/9/10 caches move cost into classical synthesis.
- **Sampling vs certainty:** Grover/Shor/QPE success is probabilistic; fixed shots and
  bounded batches give finite confidence, not certainty.

Including at least three of these with concrete numbers is the difference between a
description and an analysis.

## Remaining weaknesses

- No actual hardware experiment; the noise section must remain honest about that.
- No quantitative logical-qubit/Toffoli estimate for RSA-2048; avoid numbers that are
  not derived by the team. A qualitative statement plus cited orders of magnitude is
  enough, or omit precise figures.
- Simplicity is relative and cannot be analysed without competitor metrics; do not
  invent a score.
- The write-up should not claim a "quantum advantage" for these toy sizes; it should
  say the algorithms demonstrate the intended query structure while classical brute
  force remains trivial.

## Recommendation

Use the corrected draft's analysis sections, keep the honesty about simulator limits,
and add a compact hardware error-budget table (error rate, coherence, routing overhead,
fault-tolerance multiplier) clearly labelled as an estimate from public typical values,
not a measured experiment. That best supports the 12+8 structure without fabricating
results.
