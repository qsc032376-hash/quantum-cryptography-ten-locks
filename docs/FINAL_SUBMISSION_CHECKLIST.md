# Final Submission Checklist — Team 3 v6.3

Prepared 2026-11-11. Deadline: **November 13, 2026, 12:00 PM EST**.

## Approved package (immutable)

- File: `drafts/ten-locks-team3-v6.3-rc.zip`
- SHA-256: `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`
- Source commit: `ce75c0721622d363e77912191a52a02c34f92472`
- 37 members, all under a single top-level `team3/`; no `.venv`, `__pycache__` or
  `.ipynb_checkpoints`.
- Independent audit: 10/10 FULL, 10/10 hashes, no flags, no timeouts,
  **103,166 CX / 217,625 depth / 294,982 gates**.

There is **no public download link** for this archive and none should be created.
Keep the team repository private; upload the ZIP directly through the official form.
Local path above is the correct source file; its digest is the download-integrity
reference if the team copies it to another private location.

## Official submission requirements (from the challenge README)

- ZIP the **team folder** so the archive contains one folder named `team3/`.
- Include only the team folder: no repo checkout, `.venv`, caches or notebooks.
- Upload through the official Google form:
  `https://docs.google.com/forms/d/e/1FAIpQLSeYZrd6v9SxdsHyUpgYfwjhpEHVlhk7JjN5nYaVMcpo3uj7FQ/viewform`
- The form requires a Google sign-in and a file upload; confirm the visible team-name
  and member fields on the form itself (the public README does not enumerate them).
- Deadline is the form timestamp; late uploads are not accepted.
- Keep solutions private: do not push them to a public repo or open a PR.
- Resubmission replaces the earlier entry and **resets the tie-break time**, so avoid
  unnecessary resubmits.

## Checklist

| Item | Status | Evidence / action |
|---|---|---|
| Ten `solution.py` files present | PASS | 37-member manifest; each tier directory populated |
| Shared helpers and public caches present | PASS | `classical_keystream`, RSA/DH helpers, Tier 9/10 JSON |
| ZIP root is one `team3/` folder | PASS | 37 members, all prefixed `team3/` |
| No venv/cache/notebook cruft | PASS | member list audited |
| ZIP SHA-256 matches approved digest | PASS | `64c0e6…06c94` |
| All ten hashes match | PASS | independent Checker run 10/10 |
| Actual Aer execution per tier | PASS | `circuit_executed` true on all ten |
| No flags / no timeouts | PASS | report flags empty; max solve 14.9 s |
| README links WRITEUP | PASS | `[WRITEUP.md](WRITEUP.md)` present |
| README/WRITEUP metrics match submitted circuits | **FAIL** | ZIP docs are v6-era: T5 14,552 vs 10,950; T8 33,904 vs 7,856; T9 55,999 vs 34,186; T10 46,910 vs 38,823; total 162,716 vs 103,166 |
| v6.3 status statement accurate | **FAIL** | ZIP docs say "independent v6.3 review pending"; audit is complete and approved |
| Circuit diagrams for presentation | PARTIAL | Text/logic diagrams only; no rendered per-tier figures |
| Noise/hardware discussion | PARTIAL | Honest paragraph; no quantitative error budget |
| Final message disclosed? | OPEN | Challenge says the ten lines form a message; decide whether to state it |
| No hardcoded answers/secrets | PASS | source audit; keys recovered from measurements |
| No edits to official tools/hashes | PASS | only `submissions/team3` and docs/evidence added |
| Files kept private | CHECK | confirm repository visibility and form-only distribution |

## Critical decision: submit approved ZIP or rebuild docs?

The approved package is technically safe but its documents contradict its own metrics.
Two defensible options:

### Option A — submit the approved ZIP as-is (lowest risk)

- Preserves the exact audited 10/10 package and digest.
- Accepts that Presentation/Analysis may lose points for stale numbers and "pending"
  language.
- No new audit or packaging risk.

### Option B — rebuild with corrected documents (higher upside, needs re-audit)

- Use `docs/final-drafts/README.md` and `docs/final-drafts/WRITEUP.md`.
- Create a **new** ZIP (do not overwrite the approved one), then run the full ten-tier
  Checker and re-verify the 37-member manifest and SHA.
- Requires a fresh independent audit before upload; estimated effort 1–2 hours plus
  review. Do not attempt this if it risks missing the deadline.
- Any documentation change **requires a new package approval**; the current digest and
  audit no longer describe it.

Recommendation: if at least two hours remain after review, take Option B; otherwise
ship Option A and accept the presentation penalty.

## What would require renewed package approval

- Any edit to `README.md`, `WRITEUP.md`, `solution.py`, helpers or JSON caches.
- Any new ZIP, even with identical runtime bytes (new digest and member manifest).
- Any change to shot counts, circuits or dependencies.

## Rule-compliance assessment

- All ten tiers execute a circuit inside `solve()`; the hashes match; no classical
  answer substitution was found.
- Tier 9/10 caches are public operation tables, not secrets; the Tier 10 cache is LF
  canonical `b5de82…` (the `62b6eb…` variant is only CRLF).
- No official tool, `hashes.txt` or challenge helper was modified.
- No competition upload has been performed by this review; no public link exists.

## Concise summary for Sicheng

Approved ZIP is valid and fully passing; **do not change runtime**. Its only material
weakness is that README/WRITEUP are stale (v6 numbers and "pending" note), which can
cost presentation/analysis points. Corrected drafts are ready in `docs/final-drafts/`.
Either submit the safe approved ZIP now, or — only with enough time for a full re-audit
— rebuild a new ZIP from the drafts. Do not edit the approved ZIP in place and do not
upload before the final package is chosen.
