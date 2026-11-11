# v6.2 integration and release review handoff

**ACCEPT_INTEGRATION_RC.** Junrui Yu integrated and tested this RC. Separate source and package approval by another reviewer is pending.

## Provenance and scope

| Role | Git commit |
|---|---|
| v6 runtime | c4455782ea9388d5897fc27270f42dd3786ed35d |
| v6.1 parent | 0c043a40d3ae10b579be312c72a7adfe1e26e9a4 |
| Tier 7 level 2 | 556dd7dfc0d080aceec1a519302ba34c5f436eee |
| Tier 9 search and accepted operation arrays | d294a5a6f26b8abe96b1117928f8857e95750040 |
| Tier 10 global synthesis | 7edfe872aec8651ca28e1721ef4e322ba942d113 |
| Frozen final fallback | ca7290c7f6b35e37e4ef94f3d5f79110309f594f |
| Tested submission Git tree | 7e6c68e817fa19c7a504aefab502ff77b612f4af |

Relative to v6.1, the only production changes are the Tier 9 public operation arrays, a local multiplier module and one import in the solver. The module preserves the original generic builder for non-challenge dimensions or multipliers. All fourteen official powers use the five cached arrays. A missing required cached entry raises an error. The operations replay matches every ordered triple. The maximum forward/inverse entry error was 1.33e-13; the compiled clean-domain maximum error was 3.60e-13 and the largest scratch leakage amplitude was 2.81e-14. The original recovery, two-batch limit, 64 shots per batch, control wiring and full inverse QFT are unchanged. All other tiers and official sources retain their Git blobs. See [file digests, dependency versions, fallback ZIP digest and operator residuals](v62-evidence/source-audit.json).

## Cache and equivalence

Tier 9's JSON is the ordered candidate field from the accepted search result, compactly serialized with a final LF. The original 96-configuration search at seed 20261111 regenerated the same operation arrays, including target order and control polarities. Its inputs are public modular permutations, affine wire coordinates and deterministic search options. The deployed schema contains only mask, polarity value and target triples under public multipliers. The production grouping and gate emitter match the research functions verbatim. The official execution used a renamed directory in an isolated extraction without research imports.

Required runtime assets beyond Python, relative to the team root:

| Path | SHA-256 (Git bytes) |
|---|---|
| tier09/public_operations.json | 06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b |
| tier10/public_operations.json | b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6 |

For each of 2, 4, 9, 16 and 25, the test independently computes the ideal basis indices with the control at bit zero. It compares every complex entry of the 256-by-256 operator and its inverse, including control-off identity and all 51 padding states. No per-column phase alignment is used. A separate nine-wire probe compiles each block with the control and seven work wires live and one clean synthesis wire. It tests all 256 clean-input columns, including amplitudes in the nonzero scratch sector. The native logical block never addresses the extra wire. The full-circuit argument composes the verified blocks with the unchanged counting/QFT/measurement circuit; no dense 22-wire operator was computed.

An initial diagnostic compiled a bare nine-wire program under the compiler's default zero-input assumption and compared the resulting circuit on arbitrary inputs. For multiplier 2 this yielded an order-one error. The corrected test applies H to all eight live wires before the block, separates that preparation with a barrier, and cancels it on the input side of the reference comparison. Only the ninth wire is available as a known-zero input. Both diagnostics concern isolated compilation; the actual solver and official scorer were unchanged.

## Full official execution

[Candidate per-tier metrics and flags](v62-evidence/full-checker/report.md), [raw candidate report](v62-evidence/full-checker/report.json), [matched baseline](v62-evidence/baseline-checker/report.json). Both full runs executed quantum circuits on all ten tiers, with ten matching hashes, valid metrics, no flags and no timeouts.

| Measured | v6.1 same host | v6.2 | Reduction |
|---|---:|---:|---:|
| Tier 9 two-qubit gates |55,999|34,186|38.95%|
| Tier 9 depth |120,242|71,632|40.43%|
| Tier 9 gates |168,116|102,830|38.83%|
| Tier 9 active wires |22|22|0|
| Sum of two-qubit gates |154,629|132,816|21,813|
| Sum of separate tier depths |351,915|303,305|48,610|
| Sum of gates |452,493|387,207|65,286|

Tier 7 measured 209 / 154 / 536 / 15 and Tier 10 measured 38,823 / 92,604 / 111,337 / 19 (2Q/depth/gates/active), identical to the local v6.1 rerun. Relative to the historical v6.1 report, Tier 6 contributes +24 depth and +72 gates, Tier 7 +1 depth and +9 gates. All unaffected tiers match the local baseline exactly. The comparison controls for this drift; its specific compiler/platform cause was not isolated.

Tier 9 Pareto-improves three scored metrics with constant width. With fixed comparison bests equal to the new candidate on the three improved metrics, the upper bound on the gain is 2.25 times the sum of the fractional reductions weighted 0.4/0.3/0.2, or 0.7982 points. If rivals have best values 80% of the candidate values on those three axes, the corresponding gain is 0.6386 points. Actual eligible rival metrics are unknown.


## Focused Tier 9 reliability and simulator performance

All five pairs (9200, 9210, 9220, 9230, 9240) passed. Each process produced a matching official hash. The v6.1 harness instrumented the actual Aer run call, recording the seed and 64 shots for every batch, and timed the solver transpilation. Up to two batches were permitted; the second uses the next seed. Fresh workers alternated order within pairs, under the existing 120 s and 2 GiB outer limits. Peak RSS is a 20 ms process-tree sample and can miss short peaks. [Every run, forwarded arguments, times and batch counts](v62-evidence/paired.json).

| Variant | Passes | Median solve s | Median solve-transpilation s | Median sampled peak RSS MiB |
|---|---:|---:|---:|---:|
| baseline | 5/5 | 13.275 | 0.076 | 144.25 |
| candidate | 5/5 | 10.616 | 0.080 | 142.22 |

The full Checker reported Tier 9 solve times of 16.610 s and 13.276 s, respectively. The paired timings above are more suitable for comparison because the two full checks ran concurrently. Five pairs do not establish a universal success probability. Local Aer and the historical OSC Cardinal runs use classical computing; no hardware speedup was measured.

## Release and reproduction

The original Windows archive converted text to CRLF and the first pair of full checks passed, but the extracted cache digests differed. These preflight outputs are preserved separately. Final runs used Git blobs with LF. A packager must include both JSON files explicitly, preserve their bytes and check their digests after extraction. The older Python-only ZIP builder cannot reproduce this runtime. No submission ZIP was built or uploaded. Preserve the existing frozen final package until separate review.

Use the pinned requirements with Python 3.12 and psutil for resource sampling. From the RC repository root, create separate temporary directories. For each of the parent and RC, extract the following paths into a clean directory BASE or RC (substitute the actual ref and paths):

~~~text
git -c core.autocrlf=false archive -o snapshot.tar REF common tools hashes.txt submissions/team3 tier01 tier02 tier03 tier04 tier05 tier06 tier07 tier08 tier09 tier10
tar -xf snapshot.tar -C DEST
~~~

Keep a second identical RC extraction named PAIR with team3 unchanged. Rename RC/submissions/team3 to audit_team. In an isolated checkout at d294a5a run python research/tier09_global/search.py and retain its regenerated search.json. Run each full Checker from its own extracted root using its own tools/check_submission.py, the respective team directory and --out pointing at the appropriate evidence folder. Set --sha to the parent commit or the RC submission-tree label. From the RC checkout:

~~~text
python docs/v62-evidence/audit.py HEAD RC/submissions/audit_team RESEARCH/research/tier09_global/search.json
python docs/v62-evidence/paired.py BASE PAIR
~~~

Use disposable output directories or a disposable checkout for a new review. Compare all per-tier metrics and cache digests to the recorded values. The committed full reports and seed records refer to this integration run.
