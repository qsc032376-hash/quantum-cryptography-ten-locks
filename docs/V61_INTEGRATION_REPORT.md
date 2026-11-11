# Team 3 v6.1 integration candidate

Date: November 11, 2026 (America/New_York). This branch is an integration candidate, not an authorized replacement for the frozen final submission. No archive was rebuilt or uploaded.

## Provenance and imported changes

- Audited v6 runtime: `c4455782ea9388d5897fc27270f42dd3786ed35d`.
- Frozen final package: `ca7290c7f6b35e37e4ef94f3d5f79110309f594f`; unchanged.
- Tier 7 research: `556dd7dfc0d080aceec1a519302ba34c5f436eee`.
- Tier 10 research: `7edfe872aec8651ca28e1721ef4e322ba942d113`. Its validation JSON identifies source snapshot `1606416` and binds the public cache by SHA-256.

Tier 7 `solution.py` is byte-identical to its accepted research version: only the pretranspilation level changes to 2. Both the 64-shot 14-bit QPE and 32-shot phase-cancellation circuit retain their controlled powers, bit mapping, seeds and recovery logic. The official scorer still transpiles at level 1.

Tier 10 imports the approved `candidate.json` byte-for-byte as `public_operations.json`. The `grouped` and `emit` functions are extracted verbatim from the approved research source into the self-contained `global_synthesis.py`; `shared_control.fanout_multiplier` delegates to that implementation. A small local JSON loader replaces the disposable research wrapper. It is restricted to the validated public modulus 83 and seven work bits. The normal 19-qubit builder, all twelve controlled public powers, QFT wiring, seeds, shot budgets, measurement-derived exponent checks and classical decryptor are unchanged. The cache contains public gate operations, not measurements, exponents, keys or plaintext. Unsupported public parameters fail rather than silently selecting a new candidate.

The exact public cache SHA-256 is:

`b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6`

## Source integrity and reproducibility

[Source audit](v61-evidence/source-audit.json) confirms that the only changed existing files relative to the runtime RC are `submissions/team3/tier07/solution.py` and `submissions/team3/tier10/shared_control.py`. The only new production files are `submissions/team3/tier10/global_synthesis.py` and `submissions/team3/tier10/public_operations.json`. Every other tracked baseline file is byte-identical, including all Tier 1–6 and Tier 8–9 executable modules, shared decryptors, official Checker/configuration, challenge helpers/oracles and existing archives.

The audit reruns the deterministic public-network search from all 96 recorded coordinate configurations and the original forward/inverse/clear choices. The regenerated networks exactly equal the approved cache; no new random search result was substituted. Every generated network is checked over its complete work domain, and every integrated emitted Qiskit circuit equals the original research emitter's circuit. This carries the research phase/control/padding semantics into the production layout. Earlier research complex-operator and full-state evidence remains scoped evidence, not a new full-system formal proof.

The source audit records SHA-256 for every executable and cache file in the candidate team folder. The full Checker report identifies the exact submission Git tree; evidence and report additions do not alter that tree. Runtime imports resolve entirely within the official repository and `submissions/team3/`; no research directory or temporary source path is needed. Focused validation uses disposable candidate and baseline copies with their research directories removed.

## Environment and official procedure

Validation uses Python **3.12.16**, Qiskit **2.6.1**, Aer **0.18.2**, the unchanged official requirements, and psutil 7.2.2 for monitoring. [Environment freeze](v61-evidence/environment.txt) records installed versions. Official scoring uses `rz,sx,x,cx`, all-to-all coupling, optimization level 1 and transpiler seed 12345. The official solve and scoring-transpile limits remain 120 seconds each.

The unmodified official Checker ran in full mode against the integrated normal team directory. Complete reports are [Markdown](v61-evidence/full-checker/report.md) and [JSON](v61-evidence/full-checker/report.json). No metrics-only result is used as correctness evidence.

## Observed results

**Verdict: ACCEPT_INTEGRATION_RC.** The unchanged full Checker returned 10/10 FULL, ten matching hashes, actual quantum execution, valid metrics, no flags and no timeouts. All focused paired trials also passed. This verdict applies to the observed candidate and is not final-package approval.

Tested team tree: `submission-tree:a375b7b347abc81f87d63bc751f783cda59fe705`.

| Tier | 2Q | Depth | Gates | Active qubits | Status |
|---:|---:|---:|---:|---:|---|
| 1 | 151 | 44 | 298 | 25 | FULL / match |
| 2 | 0 | 3 | 3 | 1 | FULL / match |
| 3 | 7,808 | 8,771 | 19,497 | 7 | FULL / match |
| 4 | 183 | 195 | 455 | 20 | FULL / match |
| 5 | 14,552 | 28,132 | 40,938 | 19 | FULL / match |
| 6 | 3,000 | 5,691 | 8,680 | 22 | FULL / match |
| 7 | 209 | 153 | 527 | 15 | FULL / match |
| 8 | 33,904 | 96,055 | 102,561 | 18 | FULL / match |
| 9 | 55,999 | 120,242 | 168,116 | 22 | FULL / match |
| 10 | 38,823 | 92,604 | 111,337 | 19 | FULL / match |

| Aggregate over ten selected circuits | Stored v6 | Expected v6.1 | Observed v6.1 |
|---|---:|---:|---:|
| two_qubit_gates | 162,716 | 154,629 | **154,629** |
| depth | 369,186 | 351,915 | **351,890** |
| total_gates | 473,370 | 452,493 | **452,412** |

Depth is the sum of ten independent scoring-circuit depths, not a combined circuit depth. No values were adjusted or filtered to force agreement.

### Investigated differences

Tier 10 exactly reproduces 38,823 / 92,604 / 111,337 / 19. Tier 7 measures 209 / 153 / 527 / 15 rather than the research 209 / 154 / 536 / 15. Unchanged Tier 6 measures 3,000 / 5,691 / 8,680 / 22 rather than stored v6 3,000 / 5,715 / 8,752 / 22. All other tiers exactly match their expected metrics.

To isolate integration from environment effects, the unchanged baseline Tier 6 and Tier 7 were replayed with the same official Checker and Python 3.12 environment. [Diagnostic results](v61-evidence/baseline-diagnostics.json): both FULL; Tier 6 reproduces the candidate’s 3,000 / 5,691 / 8,680 / 22 exactly. Baseline Tier 7 yields 209 / 266 / 724 / 15 (already three gates below the stored v6 row). Thus Tier 6 drift is demonstrably present without either integration change. The Tier 7 level-2 change still reduces depth and gates relative to this same-environment baseline. These observations establish environment-sensitive compilation differences; the specific platform/library/numerical cause of the historical Tier 7 discrepancy has not been isolated. They are not evidence of unintended source edits.

The new report’s scoring-config and hashes-file byte digests differ from stored RC report digests. [Line-ending audit](v61-evidence/line-ending-audit.json) confirms the current files equal the exact baseline Git blobs with LF; converting only LF to CRLF reproduces both historical digests exactly. No official content or setting was changed. This line-ending explanation is separate from the gate-count differences and is not asserted as their cause.

## Focused reliability

Tests ran only after the full ten-tier pass. Baseline and candidate use fresh processes and fixed paired seeds: Tier 7 seeds 7100–7102 (three pairs), Tier 10 seeds 10100–10104 (five pairs). All 16 runs passed hash verification within 120 seconds. The wrapper records the seed actually forwarded to Aer: Tier 7 receives seed and seed+1, with 64 and 32 shots; Tier 10 uses one completed 128-shot batch in each observed run. It preserves the normal recovery and failure logic. Compilation timing wraps actual solution transpile calls; solve timing includes compilation, simulation and classical processing. [Full safe evidence](v61-evidence/reliability.json).

| Tier | Version | Passed | Mean compile s | Mean solve s | Mean sampled peak RSS MiB |
|---:|---|---:|---:|---:|---:|
| 7 | baseline | 3/3 | 0.011427 | 0.043435 | 83.739583 |
| 7 | candidate | 3/3 | 0.034436 | 0.061615 | 86.583333 |
| 10 | baseline | 5/5 | 0.048135 | 4.096695 | 112.515625 |
| 10 | candidate | 5/5 | 0.055082 | 5.453965 | 117.187500 |

RSS is summed process-tree RSS sampled every 20 ms; it can miss short peaks or double-count shared pages. These limited local trials do not guarantee arbitrary-seed or cross-platform success. No OSC or quantum-hardware performance is claimed.

## Reproduction

From a clean checkout of this integration branch with the referenced Git objects available, create a Python 3.12 environment and run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt psutil==7.2.2
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B docs/v61-evidence/audit_source.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -I tools/check_submission.py submissions/team3 --out docs/v61-evidence/full-checker
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B docs/v61-evidence/baseline_diagnostics.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B docs/v61-evidence/reliability.py
```

The recorded Checker invocation additionally set `--sha` to the submission-tree label above. `audit_source.py` validates source bytes, cache regeneration and emitted circuit equality. `reliability.py` refuses to start unless the recorded full Checker passes and candidate source digests still match. The diagnostic replay explains the measured historical discrepancies; it is not needed for every future reproduction. Do not commit regenerated evidence unless intentionally updating the validation record.

## Remaining audit and packaging requirements

No blocking correctness/source-integrity issue was observed for this integration RC. The precise historical compiler cause of the Tier 7 metric discrepancy remains unresolved and should be checked by the independent auditor. Measured metrics above, not the original hypotheses, are the candidate’s results.

Independent candidate review, final-document metric updates, any final-package rebuilding and artifact auditing remain separate authorized steps. Crucially, a future archive must include `tier10/public_operations.json` as well as the Python modules: the previous runtime ZIP builder selected only Python files and must not be reused unchanged. This task creates no new archive, modifies no old archive, and does not replace the frozen final submission. Recompute the final ZIP digest after any authorized packaging; do not reuse the v6 digest. Preserve the frozen v6 final package as rollback.
