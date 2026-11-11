# Junqi Sheng — final quantum technical review

Reviewed 2026-11-11. Deadline: 2026-11-13, 12:00 EST (17:00 UTC).

**Conclusion:** the pinned RC contains the approved Tier 8 hybrid permutation compiler, Tier 9 v2, and Tier 10 v2. Their mathematical constructions and measurement-to-key paths are consistent with the included code. Existing operator tests and execution records support these implementations, with the qualifications below. This is a source/evidence review, **not a new simulation run or Youyang's independent audit of the combined RC and ZIP**. That audit remains pending. No production code, official files, release refs or submission artifacts were changed.

## 1. Exact scope and provenance

Repository: `qsc032376-hash/quantum-cryptography-ten-locks`.

- Read-only detached worktree: `release/ten-locks-v6-rc@c4455782ea9388d5897fc27270f42dd3786ed35d`.
- Documentation branch: `docs/junqi-final-technical-review`, based on that exact RC.
- Frozen v5: `41c7c6775b8fc499c2acdd878b4829bd17e1210d`.
- Tested submission tree: `5d825abd0f0c82546c83574bf4148c3a92238d83`.
- RC archive SHA-256: `b6e40b2d3b1802c7cd193c3307ac442a816599b34ded196b89dca72ca65747c3`.

The report's `submission-tree:...` label identifies a Git **tree**, not a different release commit. This review checked `git rev-parse RC:submissions/team3` against that label, the archive digest, and all 30 archived file digests against [the manifest](v6-rc/manifest.json). All matched; the archive was read without extraction or modification. This verifies artifact identity, not runtime correctness.

| Actual RC implementation | Exact approved source | Source correspondence checked here |
|---|---|---|
| Tier 8 hybrid | `b92a17fae7cf14c880e6457bce4f3c339626fc94` | Entire `submissions/team3/tier08/` directory identical |
| Tier 9 v2 | `00fee41ee8707ccdd2b6920dd95cc877d2d506bf` | Entire `submissions/team3/tier09/` directory identical |
| Tier 10 v2 | `be78cc11d6e5e778c2ecfd2d0efa79fe740b3274` | Entire `submissions/team3/tier10/` directory identical |

Tier 10's measured source `191f1f0abcb21dd9ad19b3ebaff1d7cacefd4dcd` also has the same Tier 10 directory as `be78cc1`. Tier 9's reused order-recovery and RSA modules match its approved source. The shared `permutation_table()` contract remains unchanged. The updated shared inverse-QFT function retains `reverse_input=True` by default, so Tier 9 still receives its original full SWAP-containing transform. Tier 8 and Tier 10 explicitly absorb SWAPs into their control wiring instead.

**Excluded:** Tier 9 research v3 (55,971 two-qubit gates), Tier 10 research v3 (46,038), and Tier 10's 20-qubit clean-ancilla alternative. None supplies the final metrics or correctness argument in this review.

## 2. Resource evidence and its meaning

These are the actual official-scoring rows retained in [RC report.md](v6-rc/report.md) and [report.json](v6-rc/report.json), not estimates from removed CCX gates. Qiskit 2.6.1 and Aer 0.18.2 are recorded. The unchanged [scoring configuration](../tools/scoring_config.yaml) uses `rz,sx,x,cx`, all-to-all coupling, optimization level 1 and transpiler seed 12345. The official solve and scoring-transpile limits are each 120 seconds; they are not a single limit on the entire Checker process.

| Tier and comparison | 2Q gates | Depth | Total gates | Active qubits |
|---|---:|---:|---:|---:|
| 8: immediately preceding baseline → RC hybrid | 42,792 → **33,904** | 123,300 → **96,055** | 130,171 → **102,561** | 18 → **18** |
| 8: reduction | **20.77%** | **22.10%** | **21.21%** | unchanged |
| 9: frozen v5 → approved v2 in RC | 89,075 → **55,999** | 235,048 → **120,242** | 263,601 → **168,116** | 21 → **22** |
| 9: reduction | **37.13%** | **48.84%** | **36.22%** | increases by one |
| 10: frozen v5 → approved v2 in RC | 82,804 → **46,910** | 218,263 → **109,763** | 245,153 → **132,023** | 19 → **19** |
| 10: reduction | **43.35%** | **49.71%** | **46.15%** | unchanged |

Tier 8's comparison baseline is `0988ac44d88d08cc12258f2010afaf792dd53e7b`, after earlier wiring optimizations; it is **not** the older frozen-v5 row of 42,810 / 123,320. Reductions use `(before-after)/before`; comparison endpoints must be labeled on slides.

Recalculation of the stored RC JSON confirms: all ten tiers `full`, all `hash_ok=true`, actual circuit execution, valid metrics, and empty flags. The sums are **162,716 two-qubit gates**, **369,186 sum of per-tier depths**, and **473,370 gates**. These remain **reported RC results pending independent audit**, not fresh results from this review.

Under [SCORING.md](../SCORING.md), one actually executed circuit is selected per tier by greatest post-transpilation 2Q count, then depth. These aggregates sum the ten **selected** circuits; they are neither the cost of every shot/execution nor the depth of one combined circuit. The JSON records 2,082 circuit executions in total, mostly Tier 2 measurements. Simplicity weights are 40% / 30% / 20% / 10%, using eligible teams' best/team ratios; percentage gate savings do not determine a final competition score.

## 3. Tier 8: quantum order finding and the accepted hybrid

### Algorithm and actual wiring

[`tier08/solution.py`](../submissions/team3/tier08/solution.py) uses public base 2, 12 counting qubits and six work qubits. It prepares work as little-endian integer one, prepares counting qubits with Hadamards, and applies the 12 controlled public multipliers `pow(2, 2**j, 35)`. This coherently encodes the periodic map `x → 2**x mod 35`.

The current implementation absorbs the inverse-QFT SWAP network into power-control wiring: logical power index `j` uses physical control `11-j`, followed by the inverse-QFT body. It does **not** retain physical SWAP gates simply because the original implementation did. With reversal permutation `S`, inverse QFT `D S`, and controlled mapping `U`, the replacement is `D(S U S)`; because the prepared uniform counting state is `S`-invariant, this produces the same final state as `D S U`. This is equivalence for the stated preparation, not equality of the two bare operators on arbitrary inputs. Measurement still maps `q[j] → c[j]`; counts convert directly with `int(bits, 2)`.

Actual Aer counts supply `y/2**12`. [`order.py`](../submissions/team3/tier08/order.py) uses error-screened continued-fraction denominators and bounded subset-LCM combinations to propose an order. It tests `pow(2, r, 35)==1`, reduces an already verified candidate to its minimal order, checks the even-order/nontrivial-half-order conditions, and uses GCD to obtain factors. The RSA module then unwraps the symmetric key. No factors or hidden order are hardcoded or obtained by trial-dividing the modulus. The minimality routine does trial-factor a **measurement-derived candidate order**; disclose this toy postprocessing cost rather than calling the entire implementation scalable. Sampling is 64 shots per batch, at most two batches, with bounded failure.

### Full controlled operator, not only the useful orbit

[`tier08/modular.py`](../submissions/team3/tier08/modular.py) constructs

\[
P_m(x)=\begin{cases}mx\bmod35,&x<35,\\x,&35\le x<64.\end{cases}
\]

The public multipliers are coprime to 35, so this is a bijection on **all** six-bit states, including zero and padding. Each block must implement

\[
|c,x,d\rangle\longmapsto|c,P_m^{\,c}(x),d\rangle,
\]

where `d` denotes borrowed dirty wires. Control-off must be identity; control-on must preserve the complete modular permutation. Correctness on the work-|1⟩ orbit alone would not establish this contract.

### Two exact synthesis choices

**Cycle-anchor synthesis.** Decompose the public permutation into disjoint cycles. A cycle `(a,c1,...,cl)` is implemented, in chronological gate order, by endpoint transpositions `(a,c1),...,(a,cl)`. Rotating which member is the anchor preserves the same cycle. A Hamming-distance-`d` endpoint exchange uses a Gray path forward and then backward excluding its last edge: `2d-1` adjacent exchanges, with intermediate states restored. Choosing the anchor with the least sum of Hamming distances reduces that construction's cost; it is not a proof of globally optimal reversible synthesis.

**Fixed-mask elimination.** Maintain the complete output table `T`. When fixing row `i`, all smaller rows are already fixed, so bijectivity implies `y=T(i)≥i`. Use the **original** bitmask `y` as positive controls to set missing bits of `i`, obtaining `y OR i`; then use `i` as the control mask to clear surplus bits. The targets are outside their masks. Any affected value contains the mask and is therefore at least `i`, so no earlier row is disturbed. Induction reaches the identity table. Reversing these self-inverse gates realizes the original entire permutation. Adding the external control to each gate preserves the control-off identity and the control-on permutation without conditional phases.

**Hybrid selection.** For each public multiplier, the compiler compares exact cycle-anchor and fixed-mask networks using isolated MCX-template cost estimates. It chooses fixed masks for multipliers 2 and 4, and cycle anchors for 11 and 16. These are public modular powers, not recovered factors or orders. The heuristic selects a circuit; only whole-circuit official transpilation establishes the savings in the table above.

### Phases, restoration and verification scope

The existing complete exact MCX templates are retained, including the M15 dirty-ancilla construction. The local multiplier has one control, six work and two borrowed counting wires: nine wires, **512 basis branches**. Dirty wires may already be entangled, so each block must restore them for every initial value. The work register's intended modular result need not be cleared: it may remain entangled with counting qubits. Temporary borrowed state and Gray-path intermediate state are what must be restored.

The author tests checked all 512 branches for each of the four actual multipliers. That symbolic branch interpreter alone cannot test phase. Separate complex-operator tests of actual 1–6-control templates had maximum error ≤3.78e−15, and complete-block random-complex-state comparisons had maximum observed error 2.90e−14 [T8-A]. Independent validation constructed each actual **512×512 complex operator** and its inverse, including both control values, padding and both dirty-wire values. Maximum element error was approximately **2.9333e−13** [T8-O]. It did not merely align a global phase or test output probabilities. Together with the exact construction, this supports extension by linearity to superpositions and external entanglement. No full 18-qubit dense operator was claimed.

The independent Cardinal record [T8-O] reports ten paired seeds 1000–10000, actually forwarded to Aer, 64 shots each: all 20 runs `full`, hash match, valid metrics, zero flags/timeouts. A separate unmodified candidate Checker also passed. Mean solve was 34.1145 → 27.6141 seconds; mean sampled process-tree peak RSS was 522.75 → 458.98 MiB. These are configuration-specific observations: some pairs used different nodes, jobs could overlap, and 50 ms RSS sampling can miss peaks or double-count shared pages. The report's recommendation is ACCEPT subject to integrated validation. This review checked retained Git reports/operator-audit evidence, not the private raw OSC logs anew.

## 4. Tier 9: approved global fixed-mask v2, not research v3

### Quantum path and full-domain synthesis

[`tier09/solution.py`](../submissions/team3/tier09/solution.py) uses base 2, 14 counting and seven work qubits for N=77, plus one clean synthesis qubit. Work starts at integer one. The logical `j`th counting qubit controls multiplication by `2**(2**j) mod 77`. Unlike Tier 8, Tier 9 retains the default **full inverse QFT including SWAPs**. Measurement is `q[j]→c[j]`, with no string reversal. The shared continued-fraction/LCM/order-validation/GCD path consumes actual `y/2**14` samples; the recovered factors feed `rsa_classical.decrypt_tier9`. It uses 64-shot batches, at most two, and no classical factor-search fallback.

The full work operator is multiplication modulo 77 for states 0–76 and identity for padding 77–127. [`global_permutation.py`](../submissions/team3/tier09/global_permutation.py) applies the same fixed-original-mask row-elimination invariant proved above to the **whole seven-bit permutation**. Tier 9 v5 already used global row elimination: the v2 change keeps the original output mask fixed during the set stage, rather than growing it after each newly set bit. This permits fewer or shorter control groups. It does not calculate the secret order from the table or substitute an answer for the quantum measurement.

[`shared_controls.py`](../submissions/team3/tier09/shared_controls.py) preserves v5's already existing shared-control grouping; that grouping is not a new v2 contribution. For identical control predicate `C` and targets including pivot `p`, let `F` fan out `p` to the other targets using CX. The chronological sequence `F; MCX(C,p); F` flips all targets iff `C` is true. When control is false, the fanouts cancel. Controls and targets are disjoint. X/CX/exact MCX are positive-phase permutation matrices, so the transformation preserves relative phases, not only classical outputs.

### What the additional clean qubit does

The actual circuit passed to Aer declares **22** qubits. The `synthesis_work` wire starts at zero; native Aer retains exact MCX operations and leaves this wire idle (21 native active wires). Official basis synthesis can use it, producing **22 scored active qubits** and cheaper exact MCX decompositions. It is not a scoring-only dummy added to an unrelated circuit.

The valid clean-ancilla contract is

\[
V(|\psi\rangle\otimes|0\rangle_a)=(U|\psi\rangle)\otimes|0\rangle_a.
\]

This does **not** promise the same behavior for an initially-|1⟩ clean wire. Temporary borrowed wires must also be restored where used by exact decomposition templates. Original work data may remain entangled; requiring the modular work register to finish at zero would be incorrect. Relative-phase Toffoli fragments are acceptable only inside a complete, phase-correct exact construction, not as an uncorrected drop-in replacement.

### Evidence and the unchanged benchmark label

Author tests cover the five actual multipliers, complete control/work/padding branches, synthetic complex operators, small Shor states and clean-subspace leakage [T9-A]. A separate audit checked **1,280 actual branches** (five multipliers × 128 work inputs × two controls), small complete complex operators with maximum error 7.77e−15 without phase fitting, and reran the author's tests. Reported small-state error was 8.04e−14 and clean leakage 2.30e−29; clean-template tests had error 4.01e−15 [T9-I]. These are finite/compositional checks, not an exhaustive 22-qubit compiled operator or proof of every possible transpiler path.

The later OSC report [T9-O] records ten paired PASS results, actual forwarded seeds, 64 shots, hash matches, and both official Checker results `full` with valid metrics and no flags. Mean solve **increased from 28.2307 to 36.0989 seconds**, about **27.87% slower**; mean sampled RSS increased from about 168.59 to 170.74 MiB. **Do not claim a runtime or memory improvement.**

The original overall benchmark label remains **INCONCLUSIVE**, including unset human rules/reliability attestations. The integration decision [T9-D] is a later evidence-based **INCLUDE_V2** recommendation; it does not retroactively change the benchmark's label. Earlier Linux baseline timeout and a candidate solve of 111.225 seconds remain in the historical evidence; later passes do not erase them. The prior independent audit's own INCONCLUSIVE decision also remains historical fact. Private OSC raw JSON/logs were not re-audited here.

Research Tier 9 v3 saved only another 28 two-qubit gates and lacked comparable independent reliability validation. It is excluded; no v3 resources or assurances are transferred to v2.

## 5. Tier 10: measured two-dimensional discrete logarithm

### Public problem and quantum computation

The actual public parameters are **p=83, g=3, subgroup order r=41**. Given public `A=g**a mod p`, recover `a mod r`; the order is already supplied, so this tier is not another unknown-order-finding problem. The classical module subsequently derives `B**a mod p` and the specified keystream. No secret exponent or plaintext is included here.

The production path is `build_circuit()` → `build_qpe_circuit()` → `fanout_qft_circuit()`, not the old reference constructor. It uses six X counting qubits, six Z counting qubits and seven work qubits, **19 total**. Work starts in |1⟩. Public powers of `g` and `A`, controlled separately by the two uniform registers, implement

\[
|x,z,1\rangle\longmapsto |x,z,g^x A^z\bmod83\rangle.
\]

Each controlled multiplication is defined on all 128 work states: multiply modulo 83 below 83, fix padding 83–127, and act as identity when the external control is zero. The relation `A=g**a` gives the subgroup kernel `x+a z=0 mod 41`. Fourier interference reveals its dual relation `v=a u mod 41`; it does not output `a` as a precomputed classical constant.

### Actual v2 optimization

[`tier10/synthesis.py`](../submissions/team3/tier10/synthesis.py) shortens the positive predicates used to fix each permutation row. With earlier rows fixed, `y=T(i)≥i`. Instead of controlling on every set bit of `y`, choose a subset mask `m` with `m≥i`. Any affected value `z` satisfies `(z & m)=m`, hence `z≥m≥i`: earlier rows are safe. Missing target bits lie outside the mask. Clearing a surplus target uses a guard from the other currently set bits, so the same invariant holds. Selecting the highest available bits until the threshold is reached minimizes mask cardinality within this guard rule, not the entire circuit globally.

Reversing the self-inverse elimination sequence yields the original permutation. The compiler also considers an inverse-table construction, whose gate order is reversed back, and compares five exact networks with a cheap cost heuristic. Constructing that inverse table swaps input/output indices; it is **not** computing a discrete logarithm. The default emitter uses the exact pivot-fanout identity from Tier 9 with **no extra or borrowed ancilla**. Its pivot is an existing work bit, not a temporary clean wire. Work keeps the intended modular result.

Both inverse-QFT SWAP networks are absorbed into reversed control wiring, as in the prepared-state equivalence in Section 3. Thus the mathematical transform is preserved for uniform counting-register initialization, although physical SWAP gates are removed. Full controlled-multiplier equivalence applies to arbitrary inputs; the separate SWAP-absorption argument relies on the stated initial-state symmetry. These two claims must not be conflated.

### Actual readout and bounded classical recovery

Measurements use `X_j→c_j`, `Z_j→c_(6+j)`. A displayed 12-bit key is **left Z, right X**, with no reversal. The transform grid is 64, not 41. For raw X/Z integers `bX,bZ`, [`readout.py`](../submissions/team3/tier10/readout.py) and `dh_classical.py` compute integer half-up rounding:

\[
u=\left\lfloor\frac{41b_X}{64}+\frac12\right\rfloor\bmod41,
\qquad
v=\left\lfloor\frac{41b_Z}{64}+\frac12\right\rfloor\bmod41.
\]

The classical interface receives `(k1,k2)=(-v mod 41,u)`, hence `k2*a=-k1 mod 41`. Nonideal frequency locations can produce false rounded equations. The implementation rejects uninformative/inconsistent samples and does not enumerate solutions to partial-modulus equations. For generic order, a coefficient gcd must divide the right side before reduction; an unresolved reduced modulus is not a unique full exponent. Here 41 is prime, so nonzero coefficients are invertible.

It aggregates support for **measurement-derived full-modulus candidates**, checks at most eight new candidates per batch against the public relation `pow(g,a,p)==A`, and allows at most two 128-shot batches. It does not merge every off-peak rounded equation unconditionally or traverse all possible exponents. A verified observed witness is passed to the shared classical interface and then to decryption. Failure to obtain such evidence raises a bounded failure; there is no classical-answer fallback.

### Evidence and limitations

The approved report [T10-A] records five specialized tests plus two existing integration tests: minimum guards, synthetic permutation synthesis, small full complex operators, all **256 control/work branches for each of 12 actual public power blocks**, and a reduced two-register complex-state/probability comparison with the full-QFT reference. Absolute tolerance is 1e−12, without fitting away a global phase. It does not claim a dense full 19-qubit operator comparison.

Retained paired-seed JSON records seeds 1000–1009, forwarded seed=requested seed, one completed Aer job and 128 shots per run: 10/10 PASS on each side, with hashes matching. The report's recommendation is ACCEPT for this 19-qubit candidate. Its Windows benchmark nonetheless reports official solve **2.091→2.724 seconds** and median paired Aer time **1.8878→2.4723 seconds**. Reduced gates did not accelerate that simulation. Official-stage sampled RSS decreased 228.47→178.51 MiB, while sampling-only RSS medians were 122.07→123.11 MiB; do not combine unlike phases into a blanket memory-saving claim.

## 6. Accuracy findings and presentation corrections

The following are corrections to the interpretation of existing material. Historical files and code comments are retained unchanged under this documentation-only task.

| Location / claim | Required accurate wording |
|---|---|
| `docs/TIER08_TIER09_INTEGRATION.md` §§Circuit path / Resource notes (lines 5, 17–20) | Initial historical implementation: its 49,920 / 117,739 2Q values, 21-qubit Tier 9 and both physical-SWAP descriptions are not the v6 RC. Use Sections 2–4 above. |
| `docs/TIER08_INDEPENDENT_ACCEPTANCE.md`, `OPTIMIZED_V5_READINESS.md` | Old M15/v5 evidence is not the hybrid's 42,792→33,904 comparison or its later OSC acceptance. |
| `docs/TIER10_INTEGRATION.md` lines 5, 18–19 | The 107,168-gate initial result and two physical three-SWAP networks are historical. Current v2 is 46,910 2Q and SWAP-absorbed. |
| Old T8/9 and T10 integration copy commands | Incomplete for current code: Tier 9 also needs `global_permutation.py`/`shared_controls.py`; Tier 10 needs `shared_control.py`/`synthesis.py`. Reproduce from the whole pinned team tree or manifest-bound ZIP, not those old snippets. |
| `tier10/solution.py` lines 213–215 | The comment describing unconditional merging in the shared classical module is stale. Current `dh_classical.py` uses individual-first/bounded-pair logic. Production still passes a verified full-order witness; no functional error identified from this stale comment. |
| `tier10/readout.py` introductory “full inverse QFT” | Mathematical equivalence including bit ordering, not a claim that physical SWAPs remain. |
| `docs/v6-rc/HANDOFF.md` “ten circuits executed” | Say **all ten tiers executed circuits**. The report records 2,082 executions and ten selected scoring circuits. |
| “v3” without qualification | Distinguish historical whole-team release v3 from rejected Tier 9/Tier 10 algorithm research v3. |
| SHA match / no flags proves equivalent unitary | False. Hash checks final plaintext; flags are review signals. Full operator/phase/restoration reasoning is separate. |
| All ancillas/work must return to zero | Restore temporary clean/dirty workspace; modular work registers intentionally contain results and may be entangled. |
| Fewer gates means faster simulation or hardware speedup | Unsupported. Report measured CPU samples separately; Tier 9 and Tier 10 were slower in cited comparisons. No hardware experiment is claimed. |
| “369,186 circuit depth” | **Sum of ten selected per-tier circuit depths**, not one combined depth or wall-clock time. |

No hidden-answer lookup or classical factor/exponent-search substitution was found in the reviewed production paths. This is a source-level finding, not a new formal verification of Qiskit or a guarantee of all future random runs.

## 7. Scaling, cost and judge-facing boundaries

- **Quantum algorithm versus toy compiler:** coherent controlled group operations, Fourier transforms and measurement-driven recovery implement the quantum algorithms on an ideal classical simulator. Their small public moduli allow explicit permutation synthesis. A table of `2**w` entries already requires exponential classical storage in work-bit count. Repeated whole-table updates can give a straightforward `O(w*4**w)` synthesis bound before further gate compilation; anchor searches, network selection and compilation add costs. This is not a scalable arithmetic implementation for real RSA/DH keys.
- **Classical recovery:** continued fractions, GCD, supplied-order validation, bounded LCM candidates and candidate-period factor reduction must be described honestly. No claim that this exact toy pipeline has an asymptotic end-to-end quantum advantage is justified. Realistic Shor needs efficient reversible modular arithmetic and fault-tolerant resources; this project supplies neither a practical key-breaking benchmark nor a hardware-noise result.
- **Runtime:** native Aer operations and official decomposed scoring circuits are different representations. Width, MCX handling, threading, synthesis/transpilation, caching and machine load affect elapsed time. Adding one statevector qubit can double dense state storage, but measured RSS depends on active-qubit elimination and execution details; it need not double. Fewer scored CX gates is not a runtime theorem.
- **Evidence layers:** analytic invariants → complex operator/ancilla tests → sampled measurement recovery → plaintext hash → independent environment/seed checks → combined RC audit. No single layer replaces the others. Ten seeds do not prove a zero failure probability. The reported RC solve times for T8/9/10 (6.503 / 14.849 / 3.612 seconds) are one combined-RC run, not a causal before/after experiment.
- **Current handoff:** use the three exact approved sources and RC metrics above; keep Tier 9's original INCONCLUSIVE label and runtime warning; do not substitute research v3 or announce independent RC sign-off. The [RC handoff](v6-rc/HANDOFF.md) also says the team README/write-up remain to be finalized. This segment supplements Sicheng's full presentation, without replacing it.

## 8. Verified evidence index and reproduction scope

Links below pin the evidence version. Numerical findings were read from retained reports/JSON; this review did not launch new Aer, Checker or OSC jobs, access private OSC raw logs again, or time a speech rehearsal. The read-only RC and documentation worktree were kept separate. Only this document and `JUNQI_PRESENTATION_SEGMENT.md` are deliverables.

| ID | Pinned source | Evidence used |
|---|---|---|
| RC | [c445578 RC report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/c4455782ea9388d5897fc27270f42dd3786ed35d/docs/v6-rc/report.json), [manifest](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/c4455782ea9388d5897fc27270f42dd3786ed35d/docs/v6-rc/manifest.json) | Exact production tree, reported FULL/hash/metrics/flags; artifact-identity checks here |
| T8-A | [b92a17f advanced report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/b92a17fae7cf14c880e6457bce4f3c339626fc94/docs/TIER08_ADVANCED_OPTIMIZATION.md) | Hybrid proof; 512 branches, templates and complex-state tests; source selection |
| T8-O | [3dac27e independent OSC report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/3dac27e9d5c9ea9cf98a6a90edbb3afcbaca02bc/docs/TIER08_OSC_VALIDATION.md), [operator audit JSON](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/3dac27e9d5c9ea9cf98a6a90edbb3afcbaca02bc/research/tier08_osc/audit.json) | Independent full 9-wire complex blocks, ten paired seeds, resource caveats |
| T9-A | [00fee41 advanced report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/00fee41ee8707ccdd2b6920dd95cc877d2d506bf/docs/TIER09_ADVANCED_OPTIMIZATION.md) | Fixed-mask construction; clean-qubit contract; original tests/failures |
| T9-I | [c89c474 independent audit](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/c89c4744f07b436fcbd25e535a48b8bbd3276fc3/docs/V6_TIER09_INDEPENDENT_AUDIT.md) | Independent 1,280 branches, complex operators, clean tests; historical INCONCLUSIVE |
| T9-O | [e133887 OSC report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/e133887728a60065470205e66982a1f44f12f8b8/docs/TIER09_OSC_BENCHMARK.md) | Completed top-of-report ten-pair record, slower mean solve, unchanged benchmark label; older preparation text is historical |
| T9-D | [8501328 final decision](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/850132834d3a766a7cb7c66a9342ed71c2ad6340/docs/TIER09_FINAL_DECISION.md) | INCLUDE_V2 recommendation, v3 exclusion and preserved evidence limitations |
| T10-A | [be78cc1 advanced report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/be78cc11d6e5e778c2ecfd2d0efa79fe740b3274/docs/TIER10_ADVANCED_OPTIMIZATION.md), [comparison JSON](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/be78cc11d6e5e778c2ecfd2d0efa79fe740b3274/docs/evidence/tier10-advanced/comparison.json) | Short-predicate proof, tests, 19-qubit accepted metrics and slower runtime; adjacent paired-seed JSON inspected |

For a future authorized replay, use the **entire pinned RC** and [its handoff procedure](v6-rc/HANDOFF.md), pinned requirements and unchanged official tools. Record exact source/archive identity, actual Aer seed forwarding, sample budget, all failures and resource accounting. This review neither changes the official acceptance criteria nor authorizes a new release.
