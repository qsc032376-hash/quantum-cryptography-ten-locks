# v6.3.1 independent release evidence

The root decision is `../V631_INDEPENDENT_RELEASE_AUDIT.md` and
`release-decision.json`. Only the exact archive at
`2fe40b2d096d87875244d5ccbb8a76ef979ac499` is approved, with SHA-256
`4f1b2de8c7b554bed75319ab7f965937bad85906aa11a26172f5573dc24dfb52`.

- `archive-comparison.json` and `verify_archive.py`: direct old/new ZIP bytes,
  37 members, paths, CRC, raw source blobs, 35 unchanged runtime files and caches.
- `documentation-review.md`: direct ZIP-member accuracy review, source citations
  and three explicitly non-blocking wording/citation caveats.
- `prior-checker-evidence.json` / review Markdown: independent examination of
  Junrui's follow-up evidence at `24b3c53181e184050973528903fd31abcc7f36b1`.
  The two `junrui-*.md` files are exact retained copies of those pinned blobs.
- `checker/report.json` and `.md`: the new, unchanged official Checker outputs
  from this audit's actual fresh execution, not copies of the old v6.3 run.
- `independent-checker.json`: source identities, observed environment, all 20
  worker seed observations, all per-tier outcomes, timings, sampled memory and
  file preservation checks. Raw private logs and the temporary official tree
  were removed after successful verification; they are not committed.
- `evidence-index.json`: SHA-256 index of the safe published evidence.

To reproduce, use Python 3.12 with the recorded Qiskit 2.6.1 / Aer 0.18.2
package environment and the pinned Git objects. In a clean audit checkout run:

```text
python docs/v631-independent-audit/run_independent_checker.py \
  --repository /absolute/path/to/audit-checkout \
  --private-root /absolute/path/to/new-private-scratch
```

Choose a new scratch directory and evidence destination/check-out; the script
refuses to overwrite an existing `independent-checker.json` or private tree.
It plans exactly one complete official run, preserves official limits/config,
sets only the documented process environment, and does not seed or patch Aer
calls. It records every outcome and has bounded outer resource guards. It uses
`git archive` of the official upstream commit followed by extraction of the exact
approved ZIP, not rebuilding the submission archive. Do not upload its private
scratch files or use a reproduction as permission to submit the competition form.

All numeric runtime metrics are from real unchanged-Checker execution. This
review performs no new quantum algorithm optimization and does not infer
unitary equivalence from hashes alone. Three documentation caveats remain in the
immutable submitted prose and are disclosed in the root decision.
