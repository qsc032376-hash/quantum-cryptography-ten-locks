# Independent review of Junrui's v6.3.1 Checker evidence

This subreview inspected existing immutable Git blobs and both ZIP byte streams.
It did **not** run a Checker or simulator. The root audit's fresh execution is
separate evidence and must be used for the final release decision.

## Source identity and evidence location

The user-pinned package commit is
`2fe40b2d096d87875244d5ccbb8a76ef979ac499`. That commit contains the new archive,
the two edited submission documents and `docs/V631_PACKAGE_MANIFEST.md`, but no
new Checker result.

The remote `release/v6.3.1-documentation-fix` branch was observed at
`24b3c53181e184050973528903fd31abcc7f36b1`, the direct child of the package commit.
It adds only `docs/V631_FULL_CHECKER.md` and `docs/V631_RELEASE_REVIEW.md`.
The object was fetched read-only; no branch was checked out, reset or updated.
The archive blob is identical at the package and evidence commits.

The actual archive bytes independently hash to:

`4f1b2de8c7b554bed75319ab7f965937bad85906aa11a26172f5573dc24dfb52`

The new report's Commit field explicitly binds to this digest. The 37 member
names and order match the old approved ZIP. Direct decompressed-byte comparison
finds exactly `team3/README.md` and `team3/WRITEUP.md` changed; the other 35
members are identical. These checks confirm the manifest's stated scope; they
do not by themselves certify the accuracy of the new prose.

Exact copies of the two prior evidence Markdown blobs are retained as
[junrui-checker-report.md](junrui-checker-report.md) and
[junrui-release-review-record.md](junrui-release-review-record.md). Their
source commits and raw SHA-256 values are in
[prior-checker-evidence.json](prior-checker-evidence.json).

## Full per-tier report review

Every row says `full`, `match`, Circuit run `yes`, Metrics `ok`, and Flags `-`.
All ten rows were parsed independently, not merely the aggregate statement.

| Tier | 2Q | Depth | Total gates | Active qubits |
|---|---:|---:|---:|---:|
| 1 | 151 | 44 | 298 | 25 |
| 2 | 0 | 3 | 3 | 1 |
| 3 | 7,808 | 8,771 | 19,497 | 7 |
| 4 | 183 | 195 | 455 | 20 |
| 5 | 10,950 | 19,703 | 28,413 | 19 |
| 6 | 3,000 | 5,715 | 8,752 | 22 |
| 7 | 209 | 154 | 536 | 15 |
| 8 | 7,856 | 18,804 | 22,861 | 18 |
| 9 | 34,186 | 71,632 | 102,830 | 22 |
| 10 | 38,823 | 92,604 | 111,337 | 19 |
| Sum of separate circuits | **103,166** | **217,625** | **294,982** | — |

Recomputed totals match the user and the release-review record. Every metric
row also matches the approved v6.3 reference report at `ce75c072...`, whose
runtime files are byte-identical. Identical values are compatible with a fresh
run on the same platform; they alone neither prove nor disprove that a fresh
run occurred. We do not treat the old v6.3 JSON as a new v6.3.1 JSON result.

## What the evidence establishes and what it does not

The published Markdown is a complete ten-row, official-style result tied to
the new digest. The follow-up review record explicitly states a fresh official
checkout, actual circuits, empty flags and zero timeouts. It declares checkout
`fce7c3950d06bb4d23e3c057b4625f901c396de4`; a read-only tree comparison with
upstream `340e1ce18cafa69f4cea906f88f93741738dc0fa` finds only the added
`docs/TIER01_THEORY.md`, with no official executable/scoring changes.

However, at `24b3c531...` there is no new-digest raw JSON report, run log,
extraction command record, environment manifest, phase timing or resource
record. Python and all actual installed dependency versions for this run
therefore cannot be independently established from the committed evidence.
The repository pins Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4 and PyYAML 6.0.3;
these are declared requirements, not observed installed-version proof.

The inspected official scoring file specifies basis `[rz,sx,x,cx]`, level 1,
seed 12345, no coupling map/initial layout and 120-second solve/transpile
limits. A source configuration is not by itself a historical process trace.
The reported `Circuit run=yes` is meaningful Checker output, but this
subreview did not observe that earlier Aer process or its input circuits.
Zero timeouts is explicitly asserted in the release review rather than backed
by a separate published timeout log. These are provenance limits, not findings
of falsification or a correctness failure.

## Relation to previous independent metric investigation

The earlier independent audit at
`be105035dee6cdbbf30f1dc06a95100f4c9e49f5` recorded three fresh full Checker runs:
30 FULL/hash matches, zero flagged tiers and stable local totals
103,166 / 217,602 / 294,857. It gave **SAFE_WITH_VARIANCE**, with the exact
cross-environment compiler trigger unresolved. Its conclusion and all prior
reports remain unchanged.

The new ZIP's unchanged 35 runtime members support carrying forward the
known metric-variance explanation and algorithm provenance, but approval of
the old ZIP does not automatically approve the new documentation package.
Documentation accuracy and the exact new digest require their own sign-off.

## Subreview conclusion

No contradictory result or runtime change was found in Junrui's published
report. The ten rows and totals are internally consistent, digest-bound and
match the declared unchanged runtime. The record's "RELEASE_BLOCKED pending
independent sign-off" describes an unmet review gate at that time, not a
reported execution failure.

An independent full run of the exact new ZIP is recommended to close the
missing raw-machine-evidence and observed-environment gaps before the root
review's final release decision. Do not delay the release merely to force the
historical depth/gate values if the known, disclosed local variation recurs
with all correctness and compliance checks passing.
