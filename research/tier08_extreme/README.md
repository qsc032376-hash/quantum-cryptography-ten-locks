# Reproduce the Tier 8 extreme-synthesis research

Use Python 3.12 with repository-pinned Qiskit 2.6.1, Aer 0.18.2 and NumPy 2.5.4. Validation also uses psutil 7.2.2 and the existing benchmark harness at `ab9676749e00da904d0b8076811a2407d3b7205f`. No OSC connection is needed. Keep the RC/final package read-only; run research in its own worktree.

Set `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OMP_NUM_THREADS=2` and `QISKIT_PARALLEL=FALSE`. Use one thread for dense operator audits. Run commands from the repository root. None should print secret order/factors/keys/plaintext or private counts.

## Re-run the selected implementation

The final selected public gate cache is in `submissions/team3/tier08/extreme_synthesis.py`, using **native MCX and the last target as fanout pivot**. Its complete static pipeline has **7,856 CX / 18,804 depth / 22,861 gates / 18 active qubits**. `modular.py` dispatches only the four scoped Tier 8 multipliers to it. The original general-width hybrid is retained. No research module is imported during production `solve()`; renamed team directories are supported by relative imports.

Evidence versions are distinct: `verification.json` and `validation.json` concern the earlier **9,302-CX fallback**, whose ten paired seeds passed. `final_verification.json` and `final_validation.json` concern the newly selected **7,856-CX** implementation. The latter's status must be read from its own records; never transfer the fallback's ten-pair result to the final candidate. `first_verification.json` is earlier still, for 9,832 CX.

```bash
python -B research/tier08_extreme/verify.py --output /tmp/tier08-equivalence-new.json
python -B research/tier08_extreme/validate.py \
  --harness ../tier08-handoff-harness \
  --output /tmp/tier08-validation-new.json --total-seconds 1200 \
  --seeds 1000 2000 3000 4000 5000
python -B research/tier08_extreme/validate.py \
  --harness ../tier08-handoff-harness \
  --output /tmp/tier08-validation-new.json --phase cross --resume \
  --total-seconds 1200 --seeds 6000 7000 8000 9000 10000
```

The validation runner archives `c4455782ea9388d5897fc27270f42dd3786ed35d` for the control and overlays only the research candidate's Tier 8 files in the other isolated snapshot. It invokes the unchanged official `check_tier`, then the pinned strict cross-seed worker. Duplicate attempts are not retried; outputs are not overwritten. A resumed run requires the same source fingerprint, environment and limits. The per-invocation budget may stop the requested phase before every seed if not enough time remains for a complete bounded worker; report that honestly.

The research parent commit recorded during testing can still be the baseline, because the candidate is a working-tree overlay. The production-file SHA-256 map identifies the tested implementation; the eventual research commit records those same runtime bytes. Artifact/source digests and full source branch names are in the report and JSON files.

## Replay the search in a disposable research copy

Do not overwrite the retained evidence if comparing a new run. Timing fields naturally differ; semantic network fingerprints should reproduce.

```bash
python -B research/tier08_extreme/search.py --configs 500
python -B research/tier08_extreme/boolean.py \
  --input research/tier08_extreme/search.json --top 15 \
  --output research/tier08_extreme/boolean_results.json
python -B research/tier08_extreme/compile_candidates.py
python -B research/tier08_extreme/boolean_second.py \
  --input research/tier08_extreme/search.json --top 15 \
  --output research/tier08_extreme/boolean_second_results.json
python -B research/tier08_extreme/boolean_third.py
```

Search seed is `2026111108`. Each `(bit permutation, XOR mask, forward/inverse direction, guard policy, target order)` is one configuration applied to all four public multipliers. Cache identity incorporates compiler-source bytes and the complete configuration. Every generated network is checked against all 64 work inputs and the inverse; emitted exact MCX circuits add the external control.

Selection is deterministic: the first checkpoint takes `search.json.best[d].operations`; Stage B ranks actual compiled metrics by CX, depth, total gates; later checkpoints compare the previous winners and Boolean variants by their public proxy, including reversing an exact 11/16 inverse network. The retained `first_selected.json`, `scored_selected.json`, `second_selected.json` and `third_selected.json` preserve the original funnel. The final `selected.json` contains the adaptive-search operations with last-pivot emission. `PUBLIC_NETWORKS` is the final selected array rendered as Python tuples, not a classical answer table. `verify.py` independently checks its complete quantum action.

To replay one retained complete circuit without consuming/replacing the historical twelve-candidate ledger:

```bash
python -B research/tier08_extreme/screen.py \
  --selected research/tier08_extreme/third_selected.json \
  --mode native --output /tmp/tier08-static-new.json
```

`whole_search.py` refuses more than twelve complete candidate records; `linear_probe.py` consumes the final slot and reuses the unchanged generic Tier 5 GF(2) pass. To reproduce the complete historical funnel, use a disposable copy of the initial ledger/checkpoint files, not a force-reset of preserved results. The chosen runtime does not include the unsuccessful linear pass.

## Authorized extension: adaptive and general-linear coordinates

After the initial bounded funnel, the user explicitly requested continued optimization, including a different architecture, inside the original one-hour ceiling. The original ledgers remain unchanged. `adaptive_search.json` records **4,000 additional distinct configurations**, disjoint from the initial 500, with **16,000** full mapping/inverse checks and **15,991 distinct generated networks** within that extension. This is 4,500 bit-permutation/XOR configurations across the two stages, not a relabeling of the original 500 limit.

`affine_linear.json` separately records **1,000 general-linear attempts, 996 distinct configuration/network pairs**, followed by 24 Boolean refinements. Its explicit unconditional pre/post CNOT boundaries are included in the full-domain checks and the actual circuit costs. The best such architecture scored 8,566 CX, so it was not selected over the adaptive result.

The adaptive top ten networks per multiplier underwent **40 exact Boolean refinements**. The frozen third-family optimizer was used; all 64-input forward/inverse mappings passed. The resulting operations score 7,876 CX with first-pivot native emission and 7,856 with last-pivot emission. The five extension whole-circuit screens are kept in `adaptive_whole.json` and `extension_candidates.json`, separate from the original twelve-candidate ledger. `pareto.json` includes all 17 candidates, with separate four-resource and resource-plus-compilation-time frontiers. Missing solve/RSS observations are `null`, never zero; final runtime must use final-candidate evidence.

In a disposable copy, run `python -B research/tier08_extreme/adaptive_search.py` and `python -B research/tier08_extreme/affine_linear.py`. The retained adaptive Boolean pass was a one-off invocation of frozen functions; this recipe reproduces its selected operation arrays without altering historical evidence:

```python
import json
from pathlib import Path
from research.tier08_extreme import boolean_third as third, mixed

folder = Path("research/tier08_extreme")
data = json.loads((folder / "adaptive_search.json").read_text())
third.b.transported_merge = third.transported_merge
selected = {}
for multiplier, rows in data["top_candidates"].items():
    choices = [third.b.optimize(row["operations"]) for row in rows[:10]]
    selected[multiplier] = min(choices, key=lambda ops: (third.b.cost(ops), len(ops)))
for multiplier, inverse_multiplier in (("11", "16"), ("16", "11")):
    inverse_ops = list(reversed(selected[inverse_multiplier]))
    mixed.verify(inverse_ops, mixed.table(int(multiplier)))
    if third.b.cost(inverse_ops) < third.b.cost(selected[multiplier]):
        selected[multiplier] = inverse_ops
Path("/tmp/tier08-adaptive-selected-new.json").write_text(json.dumps(selected))
```

Then compile the final emission with `python -B research/tier08_extreme/screen.py --selected /tmp/tier08-adaptive-selected-new.json --mode native --pivot last --output /tmp/tier08-final-static-new.json`. `extension_compare.py` reproduces the general-linear architecture and the three additional adaptive emission comparisons; it refuses to overwrite `extension_candidates.json`, so use a disposable copy. These compilation screens are not new quantum execution or independent reliability tests.

## Artifact map

| Files | Meaning |
|---|---|
| `mixed.py`, `search.py`, `search.json` | Full-domain affine/mixed-polarity compiler; all 500 configurations and 2,000 generated networks, source fingerprints/cache records |
| `boolean.py`, `boolean_second.py`, `boolean_third.py`, matching result JSON | Exact ESOP/RM/dependency/conjugation refinements and synthetic tests |
| `boolean_stage_b_input.json`, `boolean_replay.json` | Exact Stage B input and separate reproducibility replay; elapsed times are not interchangeable |
| `emitter.py`, `compile_candidates.py`, `compiled_candidates.json` | Exact conditional fanout/MCX variants; 60 actual block-compilation records |
| `screen.py`, `baseline_profile.json`, `whole_search.py`, `whole_candidates.json` | Runtime-plus-official transpilation, baseline attribution and twelve complete-circuit candidates |
| `adaptive_search.py`, `adaptive_search.json`, `adaptive_boolean.json` | Authorized additional 4,000 coordinate configurations and 40 exact Boolean refinements; frozen sources and complete evidence |
| `affine_linear.py`, `affine_linear.json` | General-linear CNOT-coordinate alternative, 1,000 attempts / 996 distinct cases, all control/work/inverse checks |
| `adaptive_whole.json`, `extension_compare.py`, `extension_candidates.json` | Five extension whole-circuit compilation results, including explicit general-linear boundaries and last-pivot selection |
| `mcx_ablation.py`, `mcx_ablation.json`, `linear_probe.py`, `linear_probe.json` | Rejected primitive and linear-window alternatives with measured costs |
| `candidate.json`, `selected.json`, production `extreme_synthesis.py` | Exact chosen network, production fingerprints and runtime cache |
| `verify.py`, `final_verification.json` | Final 7,856-CX implementation's full complex controlled operators, inverse/padding/spare-wire checks and register tests |
| `verification.json`, `first_verification.json` | Earlier 9,302-CX fallback and 9,832-CX initial candidate audits; not final-candidate evidence |
| `validate.py`, `final_validation.json` | Final 7,856-CX implementation's own official/paired execution, actual seeds, hashes, time and sampled RSS |
| `validation.json` | Preserved 9,302-CX fallback official result and ten-pair validation; do not transfer to the new final source |
| `simplicity.json`, `pareto.json` | Clearly hypothetical scoring scenarios and separately scoped static/runtime frontiers |

All tables are public gate specifications, not recovered hidden orders. Basis labels inside test code are synthetic/public. Runtime plaintext and statevectors, if used for an additional comparison, must remain in memory and never be serialized into the repository.

## Final handoff evidence

Final `final_validation.json`: official FULL/hash match/valid metrics/no flags, five newly controlled paired seeds PASS. `final_full_state.json` verifies all 262,144 prepared-state amplitudes and counting marginal probabilities for the final 7,856-CX runtime; `full_state.json` remains the separate 9,302-CX checkpoint audit. Reproduce with:

```bash
python -B research/tier08_extreme/full_state.py --root "$PWD" --output /tmp/tier08-final-full-state-new.json
python -B research/tier08_extreme/screen.py --baseline --output /tmp/tier08-baseline-static-new.json
```

`scope_verification.json` records protected-file identity. `baseline_profile_recheck.json` uses the retained pre-dispatch baseline builder, so a baseline replay cannot accidentally profile the new candidate. `pareto.json` keeps the two runtime studies separate and marks unmeasured alternatives with null values. `simplicity.json` uses the final metrics; the checkpoint's earlier score sensitivity is preserved in its own folder.
