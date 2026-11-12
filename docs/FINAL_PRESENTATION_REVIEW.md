# Final Presentation Review — Team 3 v6.3

Review date: 2026-11-11. Target: 25-point Presentation pool.
Approved package: `drafts/ten-locks-team3-v6.3-rc.zip`
SHA-256 `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`.

## Bottom line

The **technical content is strong**, but the documents inside the approved ZIP are
**materially stale** and would cost presentation and analysis credit if submitted
unchanged. The ZIP contains the v6-era README/WRITEUP (with a short "v6.3 pending"
note), while the actual v6.3 circuits score very differently:

| Tier | Documented in ZIP | Actual v6.3 |
|---|---:|---:|
| 5 | 14,552 CX | **10,950 CX** |
| 8 | 33,904 CX | **7,856 CX** |
| 9 | 55,999 CX | **34,186 CX** |
| 10 | 46,910 CX | **38,823 CX** |
| Total | 162,716 CX | **103,166 CX** |

A judge comparing the write-up with `report.json` sees contradictions on four tiers and
on the headline total. The approved ZIP cannot be edited under this task; corrected
drafts are provided in `docs/final-drafts/` and require a new, re-audited package.

## Rubric assessment

| Criterion | Points | Current state | Main gap |
|---|---:|---|---|
| Why each approach works | 10 | Good: each tier has objective/principle, circuit, extraction | Some "why" paragraphs are compressed; no single algorithm-selection table |
| Circuit design and construction | 8 | Good text: gates, qubits, QFT, arithmetic, synthesis | No rendered diagrams; only prose/ASCII; no per-tier measurement-flow figure |
| Clarity and delivery | 7 | Detailed and honest, but long and visibly versioned | Stale numbers/contradictions; v6 narrative; no short judge summary |

**Readiness:** strong raw material, not yet a polished 25/25 package. The corrected
drafts remove the contradictions and add the missing tables; diagrams remain the
largest presentation gap.

## What already works

- Every tier states what was hidden, why the algorithm applies, what is measured and how
  the key is derived — this directly matches the "why each approach works" criterion.
- The write-up separates measured outcomes from classical post-processing and admits
  what was not retained, which is more credible than inventing shot-level results.
- Resource tables, shot budgets, oracle-call counts and limitations are present.
- Optimization changes are explained with before/after numbers and explicit scoping
  ("not a dense unitary proof", "not hardware speedup").
- The analysis already distinguishes simulator results from hardware and names
  connectivity, decoherence, readout and fault-tolerance costs.

## Highest-impact presentation improvements

1. **Replace the stale documents.** Use `docs/final-drafts/README.md` and
   `docs/final-drafts/WRITEUP.md`. They use the audited v6.3 per-tier table
   (103,166 CX / 217,625 depth / 294,982 gates) and the 10/10 FULL result.
2. **Add one small circuit/measurement diagram per tier.** A single figure with three
   panels — state preparation, oracle/arithmetic block, inverse transform and
   measurement — is enough. Ten compact figures would materially improve the
   8-point construction criterion; text alone is weaker for judges scanning quickly.
3. **Add an algorithm-selection table.** Columns: clue in the tier, structure noticed,
   algorithm chosen, measurement used, classical post-processing. This makes the
   reasoning explicit and reduces repeated prose.
4. **Add a one-page judge summary.** Ten rows: tier, algorithm, CX/depth/gates/qubits,
   one-line measurement-to-key path, status. Put it immediately after the abstract.
5. **Remove version archaeology from the judge-facing text.** The final document should
   describe the submitted v6.3 package, not the v6→v6.3 history. Keep a short
   "validation history" appendix for provenance.
6. **State the final message policy.** The challenge says the ten decrypted lines form a
   final message. If the team is allowed/expected to reveal it, add one sentence; if
   not, say explicitly that it is omitted to keep the submission private.

## Draft status

`docs/final-drafts/README.md` and `docs/final-drafts/WRITEUP.md` are complete
judge-facing drafts: accurate v6.3 metrics, per-tier sections, optimization evidence,
complexity table, hardware/noise discussion and limitations. They are **outside** the
approved ZIP. Submitting them requires rebuilding the team folder and a fresh
independent audit; do not mix them into the frozen archive.

## Risks

- Submitting the approved ZIP unchanged is technically safe but likely leaves
  presentation/analysis points on the table because of the stale numbers.
- Rebuilding a package two days before the deadline introduces packaging/hash risk; the
  rebuild must repeat the 10-tier Checker and ZIP manifest audit.
- Do not claim the corrected drafts are already submitted; they are not.
