# v6.3 Candidate A — Independent Release Audit

Audit date: 2026-11-11. Auditor: Youyang Shang (independent of the integration author).
Audit branch: `audit/ten-locks-v6.3-independent`, based on
`ce75c0721622d363e77912191a52a02c34f92472`.

## Verdict

**RELEASE_APPROVED**

A clean official checkout at the integration commit, populated **only** by extracting
`drafts/ten-locks-team3-v6.3-rc.zip` into `submissions/team3/`, passes the unchanged
official Checker 10/10 FULL with all hashes matching, no flags, no timeouts and the
expected aggregate metrics. Source and archive bytes are consistent; Tier 5 and Tier 8
mathematics were independently re-checked.

No production file, frozen ZIP, RC branch or official tool was modified by this audit.

## Source integrity

Integration commit: `ce75c0721622d363e77912191a52a02c34f92472`.
Parent: `aee41fb` (v6.2). Diff from v6.2:

- Production code changed only:
  - `submissions/team3/tier05/oracle.py`
  - `submissions/team3/tier05/solution.py`
  - `submissions/team3/tier08/modular.py`
  - `submissions/team3/tier08/extreme_synthesis.py` (new)
- Added: v6.3 docs/evidence, the RC ZIP, and the team README/WRITEUP.
- No other tier production file changed.

Tier 8's two runtime files are byte-identical to the accepted source
`8b18d3d18a6ee6b744e5ce60af13ed1c4f259c9d`:

- `tier08/modular.py` SHA-256 `0a1d5054…f905a8`
- `tier08/extreme_synthesis.py` SHA-256 `05de0bad…4a8187`

Tier 8 check: `build_controlled_multiplier` uses the cached last-pivot native network;
scored result is **7,856 CX**, matching the promised 7,856-CX synthesis.

Tier 5 check:

- `ITERATIONS = 25`, `SHOTS = 128`, `MAX_SHOTS = 128`.
- The circuit applies the phase oracle and diffuser 25 times.
- `oracle.build_phase_oracle` returns `fused_oracle(..., order=1, pivot_last=True)`,
  whose final step is the real adjoint `c.compose(a.inverse(), inplace=True)`.
- Public ciphertext comes from `load_locked(5)`; no plaintext, key, factor or
  precomputed answer is embedded. No research import or mock patch remains.

Scan of the extracted runtime for `research`/`mock`/`subprocess` found only source
comments referring to the original research cache; no forbidden runtime dependency.
No hardcoded plaintext or private secret was found.

## Archive integrity

`drafts/ten-locks-team3-v6.3-rc.zip`

- SHA-256: `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`
  (matches the expected digest)
- 37 members; `ZipFile.testzip()` returns `None`.
- Every one of the 37 members is byte-identical to its Git blob at `ce75c07`.
- Compared with the source tree, only `tier01/test_solution.py` and
  `tier01/validate_quantum.py` are omitted (test-only helpers); no runtime file is
  missing and there is no extra member.
- Tier 9 cache: `06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b`
  (ZIP == source).
- Tier 10 canonical LF cache:
  `b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6`
  (ZIP == source). The historical `62b6eb…` is the CRLF working-tree rendition;
  no cache file was rewritten.

## Independent Checker

Clean worktree at `ce75c07`; ZIP extracted to a separate team directory; official
`tools/check_submission.py`, unchanged. Python 3.12.10, Qiskit 2.6.1, Aer 0.18.2.
Full mode, all ten tiers.

| Tier | Status | Hash | Circuits | CX | Depth | Gates | Active | solve s | Flags |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | full | match | 1 | 151 | 44 | 298 | 25 | 7.890 | none |
| 2 | full | match | 2048 | 0 | 3 | 3 | 1 | 0.962 | none |
| 3 | full | match | 24 | 7,808 | 8,771 | 19,497 | 7 | 8.782 | none |
| 4 | full | match | 1 | 183 | 195 | 455 | 20 | 0.256 | none |
| 5 | full | match | 1 | 10,950 | 19,703 | 28,413 | 19 | 9.845 | none |
| 6 | full | match | 2 | 3,000 | 5,715 | 8,752 | 22 | 14.934 | none |
| 7 | full | match | 2 | 209 | 154 | 536 | 15 | 0.219 | none |
| 8 | full | match | 1 | 7,856 | 18,804 | 22,861 | 18 | 3.663 | none |
| 9 | full | match | 1 | 34,186 | 71,632 | 102,830 | 22 | 13.853 | none |
| 10 | full | match | 1 | 38,823 | 92,604 | 111,337 | 19 | 3.885 | none |

**Aggregate: 103,166 CX / 217,625 depth sum / 294,982 gates** — exactly the expected
values and exactly the per-tier table in `docs/V63_INTEGRATION_REPORT.md`.
Hash: match on all ten. Circuit executed: yes on all ten. Flags: empty on all ten.
Timeout: none. The previously recorded Tier 6 preflight timeout did **not** recur;
Tier 6 completed in 14.934 s.

## Mathematical verification (independent)

Tier 5 phase oracle, all 1,024 key inputs:

- Prepared uniform superposition over the 10 key qubits with work/flag in |0>,
  applied the extracted phase oracle, transpiled to the official basis, and inspected
  the 19-qubit statevector.
- Expected phase predicate was recomputed independently with
  `solution.validate_candidate(key, ciphertext, prefix)` for every key.
- Maximum amplitude error after the single global sign (+1): **9.12e-16**.
- Leakage outside the key-only subspace: **−5.1e-15** (floating-point zero).
- This covers all 1,024 Boolean inputs, not one known key.

Tier 8 controlled multipliers, full 9-qubit operator (control + 6 work + 2 retained
dirty slots), all 512 columns, for public multipliers 2, 4, 11 and 16:

| Multiplier | Forward max error | Inverse max error |
|---:|---:|---:|
| 2 | 5.00e-15 | 4.89e-15 |
| 4 | 8.88e-15 | 9.33e-15 |
| 11 | 2.69e-14 | 2.75e-14 |
| 16 | 2.75e-14 | 2.69e-14 |

Padding 35–63 is fixed; control 0 is identity; both dirty slots are restored. These
operators are independent of the integration author's evidence files.

No fresh multi-seed reliability run was performed in this audit; the integration
evidence records 5/5 seeds for Tiers 5 and 8. That is a residual confidence gap, not a
correctness failure; the official single run and deterministic operator checks passed.

## Runtime and dependency risks

- Checker wall time in this audit: about 101 s for all ten tiers; no solve exceeded the
  official 120-second limit (max observed 14.934 s).
- Python 3.12.10 / Qiskit 2.6.1 / Aer 0.18.2 are the pinned environment; no deprecation
  or import failure appeared.
- The archive contains all 37 runtime assets; the two excluded files are test-only.
- Tier 10's `b5de82…` cache must be handled as LF; Windows CRLF checkouts will show
  `62b6eb…`. That is a tooling hazard, not a package defect.
- No competition upload was performed.

## Decision

**RELEASE_APPROVED.** The package is ready for the team leader to submit, subject to
the normal final upload checks. This audit does not itself upload, freeze or merge
anything.
