# v6.3 metrics evidence — new four-stage investigation

This directory contains a new, uncensored three-run experiment. It supplements,
and does not overwrite, `../v63-metrics-reconciliation/` at commit
`e49ed058ed83b43866ffca4ca9b9785e3f9301ed` or the first ZIP verification at
`a6eb6230000a91317911c917755f9549847a35e8`.

The approved input is `ce75c0721622d363e77912191a52a02c34f92472` and its exact ZIP
SHA-256 is `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`.
All new execution uses Python 3.12.14, Qiskit 2.6.1 and Aer 0.18.2. The full
installed-package, native-extension and resource manifest is
`full-environment.json`; historical comparison limits are in
`environment-notes.md`.

## Evidence map

- `three-runs.json`: every scheduled full official run, fixed environment,
  raw ZIP preservation, actual scoring-worker input capture, times and sampled
  memory. `run-N/checker/report.json` and `.md` are unchanged official outputs.
- `actual-circuits.json`: all captured Tier 5/6/7 records from all three full
  runs, official-config compilation replay, selected indices, structural
  digests and transient exact native-instruction/parameter/phase comparisons.
- `tierNN-solve-profile.json`: additional diagnostic solve; actual constructed
  circuit, level-2 compilation output, raw Aer argument and recorder-normalized
  input, with actual shots and seeds. The diagnostic uses the unchanged
  official solve worker, observing inputs/returns via `sys.setprofile`.
- `tierNN-score-profile.json`: unchanged official scoring worker, its actual
  inputs and compiled outputs, the official maximum-(2Q,depth) winner and its
  metrics. No substitute default builder is used for these profiles.
- `four-stage-resource-records.json`: all six separately bounded diagnostic
  workers, including any failure. These are additional diagnostic executions,
  not replacements for or members of the three full Checker runs.
- `pass-manager-probe.json` and notes: generated pass inventories and four
  fresh-process direct-versus-QPY compilation probes; no Aer execution. Its
  independent structural schema is not comparable with the shared four-stage
  schema. Tier 6 here is explicitly a nominal-builder probe.
- `stage-localization-historical.json`: pinned-source evidence locating Tier 5's
  historical count difference upstream of official scoring; not a causal
  explanation or saved historical live Aer circuit.
- `acceptance-analysis.md`: observed ranges and conditional score sensitivity.
- `investigation.json`: final machine-readable assertions and preservation
  checks. `evidence-index.json` binds published evidence bytes.

The detailed score derivation and the earlier Hash Seed 0/1/42 and same-process
experiments are reused, explicitly labelled, from the unchanged prior evidence
at e49ed058. No historical experiment is represented as a new execution.

## Reproduction sequence

Run from a checkout containing the exact approved ZIP and the historical
archive manifest. Use the interpreter recorded in `three-runs.json`. Choose
new evidence/private directories; do not overwrite old results. Fix these
process variables before launching scripts:

```
PYTHONHASHSEED=0
QISKIT_PARALLEL=FALSE
OMP_NUM_THREADS=2
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
```

Leave `RAYON_NUM_THREADS` unset, as in the measured environment. The scripts do
not add a seed to the approved Tier 5 Aer call. Tier 6 and 7 preserve their
existing simulator seeds. Compiler seed is 12345; approved solver compilation
is level 2, official scoring is level 1, both with `rz,sx,x,cx` basis.

1. Run `repeat_three.py --repository ROOT --evidence OUT --private-root PRIVATE`.
   It creates three independent official trees from upstream Git object
   `340e1ce18cafa69f4cea906f88f93741738dc0fa`, directly extracts the exact ZIP,
   and runs the unchanged full official CLI three times. It does not rebuild
   the ZIP or retry/cherry-pick failed runs. `PRIVATE` is task-owned scratch.
2. Run `four_stage_probe.py --official-root PRIVATE/official-1
   --private-dir PRIVATE/four-stage --helper circuit_fingerprint.py
   --output OUT --reference-capture-dir PRIVATE/captured-1` with absolute
   helper/output paths. Default limits are 120 seconds and 2 GiB sampled RSS
   per diagnostic worker; no retries. The official worker itself is unchanged.
3. Run `analyze_actual_circuits.py --repository ROOT --evidence OUT
   --private-root PRIVATE`. This adds scoring-compilation replays, not Aer runs.
4. Run `finalize_evidence.py --repository ROOT --evidence OUT
   --private-root PRIVATE` to assert preservation and results. In this audit,
   the final invocation used `--remove-private-copies` only after all trace,
   source-integrity and cross-run comparisons completed. Its deletion guard
   accepts only `/workspace/scratch/v63-variance-private`.

The supplied probe and replay scripts locate `circuit_fingerprint.py` by their
specified path or sibling path, respectively. Keep those files together.
Optional standalone `fingerprint_selftest.py` checks only the public fingerprint
schema using synthetic circuits. It does not test algorithm success.

## Interpretation and privacy

The shared `v63-parameter-free-ordered-structure-v1` fingerprint hashes ordered
public instruction identities, arities, wire/classical-bit indices and parameter
types. It excludes numeric parameter values, global phase, opaque definitions,
labels, metadata and generated names. Equality is structural, not a proof of
unitary equivalence. Exact native parameters and global phase are compared
transiently; only booleans are published. No hidden Oracle decomposition is
inspected by the audit scripts.

Constructed opaque circuits have top-level, unexpanded costs; their low literal
CX count is not the scored cost. Official metrics exclude measurements,
barriers, reset and delay. The official winner is the largest 2Q count, then
depth, retaining the first record on a complete tie.

Private QPY payloads and measured results are not committed. Resource RSS is
sampled process-tree RSS, may double-count shared pages and may miss short
peaks; it is not exact peak unique memory. Profiled timings include observer
cost and should not be used as a performance comparison. Ten-tier depth totals
are sums of separate selected circuits, not one composite circuit depth.

No approved production file, official Checker/Oracle/Helper/configuration,
release branch or ZIP is changed. No competition submission is uploaded.
