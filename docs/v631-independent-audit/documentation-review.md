# v6.3.1 archive documentation — independent accuracy review

Review target: commit `2fe40b2d096d87875244d5ccbb8a76ef979ac499`, archive
`drafts/ten-locks-team3-v6.3.1-docs.zip`, actual SHA-256
`4f1b2de8c7b554bed75319ab7f965937bad85906aa11a26172f5573dc24dfb52`.

**Documentation verdict: PASS WITH NON-BLOCKING NOTES.** The substantive algorithm,
measurement, final-candidate, resource and limitation descriptions agree with the
unchanged runtime and the identified evidence. Three wording/citation caveats are
listed explicitly below; they should not be presented as silently corrected in this
immutable ZIP. This is a documentation subreview, not a replacement for the parent
review's archive and official Checker verdict.

## Method and exact documents

The reviewer read `team3/README.md` and `team3/WRITEUP.md` directly from the ZIP and
compared their bytes with the source checkout. Both match their approved source
files exactly. The old comparison ZIP was read directly from Git object
`ce75c0721622d363e77912191a52a02c34f92472:drafts/ten-locks-team3-v6.3-rc.zip`.
The new member-name order matches the old archive, and only these two documents
have changed; all other 35 members compare equal. No ZIP/member was rewritten,
no line endings were normalized and no JSON cache was reserialized.

| Member | New raw SHA-256 | Lines old → new |
|---|---|---:|
| `team3/README.md` | `93565ee417492bd27648907363fadb54637b323682bcce7a269201adabc91042` | 62 → 94 |
| `team3/WRITEUP.md` | `759a1f7de2f21775d67117dfd8594b5bdbaaec5b3f3e367b48e3286f46723a51` | 135 → 268 |

Line references below refer to the actual ZIP members, whose bytes match source.
The review reads public algorithm/source contracts and safe test aggregates; it
neither expands an opaque hidden Oracle nor reads private keys or plaintext.
No additional quantum simulation was run by this subreview.

## Substantive checks

| Claim / member location | Evidence inspected | Finding |
|---|---|---|
| README 45–57: ten per-tier metrics, aggregate 103,166 / 217,625 / 294,982 | `docs/v63-evidence/zip-checker/report.json`, `docs/V63_INTEGRATION_REPORT.md` | Exact approved reference vector, labelled as reference rather than the only possible compiler output. |
| README 25–27; WRITEUP 246–259: independent approval belongs to original Candidate A, new ZIP needs separate review | Prior audit and three-run reconciliation; explicit text in new archive | Correct separation of old artifact approval from this documentation artifact. Local variance 217,602 / 294,857 is disclosed. |
| WRITEUP 31–119: BV, BB84, DJ, Simon, Grover and QPE measurement-to-key workflow | Actual `tier01`–`tier07/solution.py` and QPE/readout public interfaces | Register sizes, one-query/one-shot claims where applicable, Simon rank 9, bounded shots and QPE phase-check structure match code. BB84 sifting is measurement-driven and not a general channel-security proof. |
| WRITEUP 121–136: final Tier 8, 7,856 CX, 18 wires, last-pivot synthesis | `tier08/solution.py`, `docs/v63-evidence/tier08-equivalence.json` | Correct final implementation, not the superseded 33,904-CX candidate. Twelve reversed power controls, six-bit work initialized to 1, QFT-body wiring, full padding/control behavior and borrowed-wire restoration are described correctly. |
| WRITEUP 138–149,179: final Tier 9, 34,186 CX / 22 wires | `tier09/solution.py`, `public_multiplier.py` interface; `docs/V62_INTEGRATION_REPORT.md`, `docs/v62-evidence/source-audit.json` | Correct v6.2 integrated implementation, not old v2's 55,999 or unaccepted v3's 55,971. Clean ninth local synthesis wire is initialized and available to scoring synthesis; work output is not incorrectly required to return to zero. |
| WRITEUP 179: five paired v6.2 trials, median solve 13.275 → 10.616 seconds | Recomputed medians from the five baseline and five candidate records in `docs/v62-evidence/paired.json` | Actual medians 13.274980499991216 and 10.61645810000482. Claim is scoped to that later local experiment. It does not replace or re-label the earlier v2 OSC INCONCLUSIVE benchmark and does not claim universal simulator acceleration. |
| WRITEUP 151–165,181–185: final Tier 10, 38,823 CX / 19 wires | `tier10/circuit.py`, `readout.py`, `solution.py`, `docs/V61_INTEGRATION_REPORT.md`, source audit and pinned research `7edfe872aec8651ca28e1721ef4e322ba942d113` | Correct final mixed-polarity public-cache implementation, not v6's 46,910 or an unaccepted later candidate. Two six-bit controls, seven-bit work, public `g^x A^z` mapping, half-up frequency rounding and bounded measurement-derived candidate checking agree with code. See the numerical citation caveat below. |
| WRITEUP 177,250–252: four nine-wire Tier 8 operators, all 512 columns | `docs/v63-evidence/tier08-equivalence.json` | Multipliers 2,4,11,16; all control/padding/dirty-input branches included. Largest complex-entry error 2.753560189158126e-14, correctly bounded by 2.8e-14; no per-column phase fitting. |
| WRITEUP 249: Tier 5 independent phase error about 9.1e-16 | `5b86f71c058193ea0b94070d76524ecef2455fe7:docs/v63-audit/tier05-phase-check.json` | Exact recorded maximum 9.12194076100314e-16. Tiny negative leakage residual is numerical roundoff, so “no detectable leakage” is appropriate, not a negative physical probability claim. Integration's separate 7.92e-16 record is not confused with this audit. |
| WRITEUP 251–252: five fresh seeds each for Tier 5 and Tier 8 | `docs/v63-evidence/seeds.json`, `seeds.py` | Ten retained records, seeds 5301–5305 and 8301–8305, all PASS/hash and resource `ok`; finite-seed limitation stated. |
| README 59–60; WRITEUP 17–19,187–242,254–259 | New documents and official scoring definitions | Correct distinction between depth sum and one circuit, query cost and gate cost, ideal Aer and hardware, toy explicit-table synthesis and scalable Shor arithmetic, hash validation and unitary equivalence. No practical cryptographic speedup or guaranteed contest rank claimed. |

The README/WRITEUP correctly explain that fewer gates do not automatically mean
faster classical simulation. In particular, the later Tier 9 v6.2 five-pair result
has its own baseline and evidence. It is not an excuse to retrospectively relabel
the earlier 55,999-CX v2 OSC experiment, whose INCONCLUSIVE label remains applicable
to that experiment. The new archive does not assert such a relabelling.

## Non-blocking caveats — disclose without altering the ZIP

### 1. “Every result ... statevector” is broader than the actual Tier 2 contract

`WRITEUP.md:231` says every result comes from “Qiskit Aer statevector simulation”.
The Tier 2 official Channel's public measurement implementation instantiates
`AerSimulator()` without a `method` override (`tier02/helper.py:66`), whereas the
other production solvers explicitly request statevector. This review did not run
or record Tier 2's internal selected-method metadata and therefore cannot certify
that all ten use that particular simulation method.

More accurate presentation wording is “ideal Qiskit Aer simulation; the main
solvers use statevector, while the official BB84 Channel selects its Aer method”.
No hardware run is claimed either way. This is a method-label overstatement, not
an executable, quantum-measurement, hash, resource-scoring or packaging defect.
It does not justify changing the approved archive during this review.

### 2. The README compresses execution provenance and scoring transformation

`README.md:88–89` calls the scored circuit “the exact circuit passed to Aer”.
Strictly, the official scorer normalizes recorded circuits and transpiles them to
its scoring basis before counting. `WRITEUP.md:23–25` explains this subsequent
transpilation correctly. In addition, the official Tier 2 worker deliberately uses
`Channel.log` measurement circuits (`tools/check_submission.py:149–155`), rather
than the separately composed channel-state-preparation circuits received by Aer.
The general “every circuit sent to Aer” explanation should be read with that
explicit official Tier 2 exception.

Accurate wording is “the official scoring transpilation of recorded executed
circuits, with Tier 2 using the official channel log”. This avoids identifying a
native execution representation with its scoring representation. The archived
metrics and method are valid and the write-up supplies the main transformation;
this is a non-blocking explanatory shorthand, not evidence that the wrong circuit
was scored. `build_circuit()` is used for query checks in Tiers 1/3, so “never
scored” means it is not selected as an independent resource-scoring substitute.

### 3. The separate Tier 10 `6.5e-15` number lacks an identified source here

`WRITEUP.md:184–185` attributes “about 6.5e-15” to a separate 19-qubit statevector
comparison. The directly traceable accepted-cache research evidence is
`7edfe872aec8651ca28e1721ef4e322ba942d113:research/tier10_global/equivalence.json`:
it records full prepared-input and deterministic random-input comparisons with
absolute amplitude errors both **0.0**, no phase fitting, plus all twelve
256-column controlled-module/inverse checks. `docs/v61-evidence/source-audit.json`
binds that research source and the exact accepted cache.

A bounded check of this research JSON/report, the v6.1/v6.2 integration records,
the original v6.3 independent audit, and the earlier `be78cc1` Tier 10 advanced
evidence did not identify the claimed separate `6.5e-15` result. This is an
**unresolved citation/precision claim**, not proof that the number is fabricated
or that it belongs to the integrated implementation. Do not repeat it as an
independently traced result. If used in a presentation, cite the identified tests
and their scope instead, or supply the missing pinned source separately.

The artifact's numerical/algorithmic acceptance does not rely on this isolated
sentence: the runtime is unchanged, final metric provenance is identified, and
independent block/state/Checker evidence exists. No dense full-system unitary
proof is claimed by the document. On that basis this is non-blocking for shipping
the exact immutable documentation ZIP, while remaining an explicit documentation
qualification; this review does not silently endorse the unsupported numeral.

## Subreview recommendation

Release documentation is materially accurate for the final v6.3 implementation
and openly discloses platform metric variance and toy-scale limitations. The
caveats above should accompany handoff/presentation. They do not require another
ZIP rebuild or quantum run and do not show a correctness/compliance/package
failure. Final archive approval should be decided using the parent review's
independent digest/member comparison and complete unchanged-Checker evidence.
