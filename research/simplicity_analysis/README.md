# Simplicity score research calculator

Standard-library Python 3.10+; no Qiskit, network access or quantum simulation. Run from the repository root. All generated scores are **hypothetical**, not official rankings.

```bash
python -B research/simplicity_analysis/score_model.py --test
python -B research/simplicity_analysis/score_model.py > simplicity-results.json
python -B research/simplicity_analysis/score_model.py --report
```

The first command checks the audited baseline, official worked examples, direct parity with the official pure ratio function, invalid inputs, zero handling, saturation, monotonicity and positive-candidate gain bounds. The second emits all scenario assumptions, per-tier and per-metric scores/losses, and all 1/5/10/20/30% sensitivities. It creates a local output file; do not add that file to a submission. The last regenerates only `docs/SIMPLICITY_SENSITIVITY_ANALYSIS.md`. No command invokes the Checker or changes circuits, archives or official files.

## Custom inputs

Use a JSON object whose keys are strings `"1"` through `"10"`. Each tier must contain all four integer-valued keys: `two_qubit_gates`, `depth`, `total_gates`, `active_qubits`. Alternatively, `--ours` accepts the official report schema with `tiers` and nested `metrics`. Our team is assumed eligible on all ten tiers; eligibility must be established externally.

```bash
python -B research/simplicity_analysis/score_model.py \
  --ours docs/v6-rc/report.json --best hypothetical-global-best.json
python -B research/simplicity_analysis/score_model.py \
  --ours hypothetical-candidate.json --competitors hypothetical-rival-minima.json
```

`--best` requires global minima no larger than our corresponding values and rejects invalid inputs. `--competitors` accepts independent rival minima, including values above ours, then computes the global minimum. Use the **same rival file** before and after an optimization; otherwise the before/after comparison changes the opponent model. The two flags are mutually exclusive. Do not pass actual private competitor information.

The Python functions `score(ours, best)` and `against(ours, competitors)` use exact rational arithmetic internally. JSON and Markdown round only for display. Contributions plus losses equal each metric's weighted tier pool. `gain` changes only the nominated tier/metrics and recomputes the global best. Inputs are nonnegative integers; the calculator is not a physical circuit feasibility validator. The baseline loader rejects deviations from the requested audited rows and totals rather than silently updating them.

## Modeling choices

B/C/D use ceiling-rounded 10/25/50% lower positive gate/depth metrics. Widths are conservatively held at the documented architecture size except T9, whose 21-qubit predecessor supports a narrower comparison. These width floors are assumptions for this study, not universal lower bounds; no fractional qubit or extrapolation beyond a supported architecture is called feasible. E's per-metric gaps are defined explicitly in `scenarios`. Different metric leaders are permitted by the official formula. All exported sensitivity entries include the integer candidate value and exact-model point change (serialized as a float).

Percentage experiments and simultaneous 10% gate/depth improvements are planning sensitivities, not implemented candidates. The documented T5/T9/T10 candidate comparisons provide the concrete combined changes. Counterfactual scores assume eligibility even for the rejected T5 candidate; actual timeout runs are ineligible and cannot earn the modeled Simplicity points. No probabilities, performance predictions or final-package modifications are implied.

See [full analysis](../../docs/SIMPLICITY_SENSITIVITY_ANALYSIS.md).
