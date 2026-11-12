# v6.3 metric variance: Simplicity and compliance impact

This note analyzes the recorded vectors from the approved v6.3 ZIP report and the first new independent ZIP check. It does not substitute synthetic inputs for actual Aer execution and does not claim an actual competition score. The parent audit retains three new uncensored runs separately.

## Exact official rule

`tools/scoring_config.yaml:7–17` sets weights `(CX, depth, gates, qubits)=(0.4,0.3,0.2,0.1)` and the tier pool `P_t=0.375 × tier_points`. Thus Tier 5 and Tier 6 each have 1.5 simplicity points; Tier 7 has 1.875.

`tools/rank.py:124–139` calculates a separate eligible minimum for each metric. For positive rival minima r and positive team metric v,

\[
S_t(v;r)=P_t\sum_m w_m\frac{\min(v_m,r_m)}{v_m}.
\]

The official zero-best case (`rank.py:83–86`, `SCORING.md:34–35`) uses `1/(1+v)` when v is positive. It is included in the calculation below and does not enlarge the bounds. If there is no better eligible rival in a metric, Team 3 leads it before and after and that metric contributes no point change.

For one metric, let x be the reference value and y the newly measured value. Holding all other eligible-team metrics fixed:

- Improvement y<x: `0 ≤ ΔS ≤ P w (x−y)/x`.
- Regression y>x: `−P w (y−x)/y ≤ ΔS ≤ 0`.
- Unchanged y=x: `ΔS=0`.

For positive r, each extremum of the one-metric function is at r=min(x,y): the lower-r branch is proportional to r, the interval between x and y is monotone, and r≥max(x,y) gives zero. The official r=0 branch is smaller in magnitude than this envelope. These are metric-wise bounds, not a claim that unknown physical rival circuit vectors jointly attain all extrema.

## Recorded differences and conditional point bounds

| Tier/metric | Reference → observed | Relative metric change | Team 3 point-change bound |
|---|---:|---:|---:|
| 5 total gates | 28,413 → 28,363 | −0.175976% | [0, +0.000527927357] |
| 6 depth | 5,715 → 5,691 | −0.419948% | [0, +0.001889763780] |
| 6 total gates | 8,752 → 8,680 | −0.822669% | [0, +0.002468007313] |
| 7 depth | 154 → 155 | +0.649351% | [−0.003629032258, 0] |
| 7 total gates | 536 → 533 | −0.559701% | [0, +0.002098880597] |

All ten tiers' CX and active-qubit metrics are unchanged between these two reports. The three affected tiers' conditional bounds are:

| Tier | Conservative lower bound | Conservative upper bound |
|---:|---:|---:|
| 5 | 0 | +0.000527927357 |
| 6 | 0 | +0.004357771092 |
| 7 | −0.003629032258 | +0.002098880597 |
| Combined | **−0.003629032258** | **+0.006984579046** |

The combined interval is a **conservative envelope for Team 3's own Simplicity points**, with other teams' eligible metric vectors held fixed. It is not a prediction of actual gain or loss, not a proof of joint attainability, and not a ranking bound. Exact rational values and an exhaustive check over integer rival minima from zero through max(x,y)+1 are in `scoring-impact.json`.

If organizers remeasure other teams as well, their minima can also change; those unknown movements are outside this conditional analysis. If Team 3 establishes a new minimum, the normalization of other teams' scores may change. Therefore one cannot infer the relative ranking change from Team 3's bound alone.

The 0.01 tie margin (`rank.py:31,149–157`, `SCORING.md:91–95`) is larger than this point envelope's individual magnitude, but **does not guarantee the ranking is unchanged**: a small shift can cross a tie-group boundary. Do not resubmit or rebuild a correct approved archive merely to match historical compiler counts; the official rules state that resubmission can move the trusted submission timestamp later.

## Compliance and proposed disposition criteria

The official rules require a matching plaintext hash, an actual circuit used by solve(), valid scoring metrics, and a legitimate measurement-driven recovery method (`SCORING.md:20–26,30`). A hash match alone does not prove unitary equivalence or genuine quantum recovery.

The Checker records the circuits actually submitted to Aer during solve(), or the official Channel log in Tier 2. It selects the largest **post-transpilation CX count**, breaking ties by depth (`check_submission.py:219–244`, `SCORING.md:54–64`). It does not score a standalone build_circuit() surrogate. Shot totals and number of executions are separate analysis evidence, not multiplicative gate-score factors.

Neither the scoring formula nor the published rules requires historical gate counts to reproduce identically across different environments. A difference in otherwise valid measured complexity is therefore **not itself** an automatic compliance failure or evidence that the ZIP is corrupted. Score the actual valid official measurement produced in the judging environment; preserve both historical and new reports and explain discrepancies honestly.

- **METRICS_RECONCILED:** appropriate if the differences are causally accounted for or reproduced under a documented like-for-like relation of actual input, compiler configuration and environment. Mere stable repetition or matching plaintext is insufficient to prove the cause.
- **SAFE_WITH_VARIANCE:** can be appropriate if approved archive/source bytes remain identical, required versions/configuration are satisfied, actual executed/scored-circuit provenance is established, all three uncensored runs pass required functional/metric/resource checks, and no prohibited operation occurs. State any unresolved compiler mechanism explicitly. This means acceptable submission/compliance evidence with bounded observed score sensitivity, not a universal proof of mathematical harmlessness or future runtime/metric determinism.
- **RELEASE_BLOCKED:** use when approved bytes or protected code differ; required correctness, execution, metrics, resource or compliance checks fail; or the submitted/executed circuit correspondence cannot be established sufficiently for the requested audit.

The final label belongs to the parent audit after its new execution and provenance evidence. This scoring calculation does not by itself approve a ZIP.
