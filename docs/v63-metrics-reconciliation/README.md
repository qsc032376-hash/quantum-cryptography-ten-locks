# v6.3 metrics reconciliation evidence

The approved ZIP and all production/official files remain unchanged. These scripts and results live only on `audit/v63-metrics-reconciliation`. The previous `docs/v63-final-verification/` evidence is retained unchanged.

Read `../V63_METRICS_RECONCILIATION.md` for the qualified **SAFE_WITH_VARIANCE** decision. This does not mean the historical exact gate counts or their cross-environment numerical cause were fully reproduced.

## Evidence map

- `three-runs.json`, `run-{1,2,3}/checker/report.{json,md}`: exactly three new sequential full official executions, with all results preserved.
- `actual-circuits.json`: all actual official scoring-input records for Tiers 5/6/7 captured from live scoring-worker input paths; all per-record metrics, selected winners and cross-run native gate/parameter/wire/global-phase equality booleans.
- `environmental-comparison.json`: verified configuration matches, definite Python patch difference, historical environment unknowns and immutable source citations.
- `mechanism-probe.json`, `historical-countops-search.json`: bounded hash-seed/process-state public-circuit probes and Tier 5's specific historical/current X-count difference. These are not additional Aer executions.
- `scoring-impact.json`, `scoring-impact.md`: official score formula, exact conditional own-score bounds, and compliance/close-ranking limitations.
- `reconciliation.json`: acceptance predicates, immutable-byte checks after all runs, and removal of temporary private circuit payloads.

No circuit QPY, private parameter values, fingerprints of private circuits, measured bitstrings, keys or plaintext are committed. Temporary recorded native circuits and fresh execution trees were removed after safe comparisons were recorded. Source-file hashes are retained normally.

## Replay without overwriting historical evidence

Use the recorded Python 3.12/Qiskit 2.6.1/Aer 0.18.2 environment. Run from a checkout containing the approved Git objects. Choose a **new empty** evidence directory; the runners refuse to overwrite existing results. The private directory must not exist before a run. Do not execute analysis with `-I`, because the analysis process must honor `PYTHONHASHSEED=0` just as the official scoring workers do.

```bash
python -I docs/v63-metrics-reconciliation/repeat_three.py \
  --repository "$PWD" \
  --evidence /tmp/v63-metrics-replay-new \
  --private-root /workspace/scratch/v63-metrics-private

PYTHONHASHSEED=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 QISKIT_PARALLEL=FALSE \
python docs/v63-metrics-reconciliation/analyze_actual_circuits.py \
  --repository "$PWD" \
  --evidence /tmp/v63-metrics-replay-new \
  --private-root /workspace/scratch/v63-metrics-private

python -I docs/v63-metrics-reconciliation/finalize_evidence.py \
  --repository "$PWD" \
  --evidence /tmp/v63-metrics-replay-new \
  --private-root /workspace/scratch/v63-metrics-private \
  --remove-private-copies
```

The cleanup flag is deliberately restricted to the task-owned `/workspace/scratch/v63-metrics-private` directory. On another host, choose an appropriate private path, omit that cleanup flag and securely remove only your newly created private replay directory after analysis. Do not publish raw recorded circuits.

The official Checker and solver limits are unchanged. An external resource failure stops further large launches; no failed run is replaced. Normal completion makes all three requested runs, including any ordinary correctness failure, visible. The same fixed interpreter, dependency directory and environment dictionary are reused, with their versions/interpreter bytes checked again at the end. Host load is not controlled, so timings are descriptive rather than a benchmark speedup claim.

The official parent uses `-I`, while its unmodified worker launcher creates fresh non-`-I` workers with `PYTHONHASHSEED=0` and `QISKIT_PARALLEL=FALSE`; the external observer verified these worker settings. Source simulator seed policies, including Tier 5's unspecified Aer seed, are preserved. These repetitions are not advertised as a three-independent-seed statistical study.

The optional `--evidence` arguments only select new output locations; their defaults preserve the commands used in the retained run records.
