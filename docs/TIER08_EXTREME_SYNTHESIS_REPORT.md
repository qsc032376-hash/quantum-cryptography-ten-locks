# Tier 8 extreme reversible synthesis — Team 3 / Junqi Sheng

Research date: November 11, 2026 (America/New_York). Working branch: `research/tier08-extreme-synthesis`. The session used a one-hour wall-clock ceiling. The initial capped search is counted below; a subsequent user-authorized extension permits additional bounded iterations inside that same time ceiling. Extension candidates and tests must be recorded separately rather than represented as part of the original 500/60/12 stage caps. This does not claim a globally optimal circuit.

## Result and protected baseline

The selected implementation combines affine-coordinate synthesis, mixed-polarity exact row elimination, shared-predicate fanout, ESOP/Reed–Muller simplification, and certified gate-conjugation rewrites. It retains genuine measurement-driven Shor order finding, the 12 public controlled powers, 12 counting plus six work qubits, SWAP-absorbed inverse QFT, and the original classical recovery and sampling budgets.

| Official single-tier metric | Pinned v6 baseline | Selected candidate | Reduction |
|---|---:|---:|---:|
| Two-qubit gates / CX | 33,904 | **7,856** | **76.8287%** |
| Depth | 96,055 | **18,804** | **80.4237%** |
| Total gates | 102,561 | **22,861** | **77.7099%** |
| Active qubits | 18 | **18** | unchanged |
| Checker / hash / metrics / flags | FULL / match / valid / [] | **FULL / match / valid / []** | both executed Aer |

All requested CX milestones, including the below-20,000 stretch target, were met by the **executed official-scoring circuit**, not just an isolated estimate. The candidate was selected by complete-circuit measurements; no linear-window rewrite was accepted when it failed to improve them.

- Runtime baseline: `c4455782ea9388d5897fc27270f42dd3786ed35d`.
- Read-only final package: `ca7290c7f6b35e37e4ef94f3d5f79110309f594f`.
- Transfer references: Tier 9 `d294a5a6f26b8abe96b1117928f8857e95750040`; Tier 10 `7edfe872aec8651ca28e1721ef4e322ba942d113`.
- Original exact-block audit reference: `3dac27e9d5c9ea9cf98a6a90edbb3afcbaca02bc`.
- Production changes on this research branch: append a scoped dispatch in `submissions/team3/tier08/modular.py`, and add `submissions/team3/tier08/extreme_synthesis.py`. The prior validated hybrid remains the fallback for other public parameters and synthetic dimensions.
- Tier 8 `solution.py` and `order.py`, Tier 7/9/10 implementations, official files, frozen releases and ZIPs are unchanged. No OSC job, release merge, competition submission or form action occurred.

The runtime cache contains public gate networks, not periods, factors, keys or plaintext. On each construction it checks the emitted network against the entire public modular permutation. `candidate.json` and `selected.json` identify the selected operations and production-file digests; the source/operation fingerprints in the validation evidence identify the actual tested candidate before this research commit was created.

## 1. Executed architecture and actual bottleneck

For each public multiplier m, the required work permutation is

\[
P_m(x)=\begin{cases}mx\bmod35,&0\le x<35,\\x,&35\le x<64.\end{cases}
\]

The controlled block must implement `|c,x,d> → |c,P_m^c(x),d>` on the full domain, not only the work-|1> orbit. The distinct multipliers produced by the unchanged public power construction are 2, 4, 11 and 16, occurring 1, 1, 5 and 5 times. This information is used only to compile public gates and weight resource estimates; it is never returned to order recovery.

The baseline's actual double-transpiled complete circuit reproduces 33,904 / 96,055 / 102,561 / 18. Its isolated multiplier costs are 1,804, 2,448, 2,952 and 2,952 CX; the inverse-QFT core alone uses 132 CX. The expensive repeated controlled permutations, rather than the small Fourier body, are the main opportunity. Isolated block figures are diagnostic and are not assumed to add exactly after whole-circuit cancellation. See `baseline_profile.json`.

The unchanged solver initializes work to integer one, runs the 12 controlled powers and inverse-QFT body, then measures `q[j]→c[j]`. Aer counts feed the original continued-fraction, bounded-LCM, candidate-order verification and GCD path. The symmetric-key unwrap and plaintext hash remain downstream of those measured factors. No factor lookup, modulus trial division, hidden-order extraction or classical-answer fallback was introduced.

## 2. Exact synthesis and phase argument

### Affine coordinates

Let `E(x)=π(x) XOR f`, where π is a bit permutation and f a public fixed mask. Construct the conjugated table by

\[
P'[E(x)]=E(P_m(x)),\qquad P'=E P_m E^{-1}.
\]

Every original state, including padding, is encoded before synthesis. Padding must not be redefined as “encoded integer at least 35.” Decode every emitted gate by `E^-1 G E`; the resulting chronological network is `E^-1 P' E=P_m`. The bit permutation relabels targets/controls; an encoded positive literal becomes an original positive or negative literal according to `1 XOR f[j]`. Target XOR translations cancel around a toggle. No physical E register or extra logical qubit is introduced.

### Safe row elimination

Maintain the full output permutation T. Before fixing row i, all earlier rows are fixed, hence bijectivity implies `y=T(i)≥i`. A positive guard contained in y with numerical mask at least i cannot touch any earlier row. Missing bits can be set with this fixed guard; surplus bits are cleared with the row mask or a shorter safe guard excluding the target. The target is never a control. After all rows become the identity, reverse the self-inverse gate sequence to implement P'. The inverse-table variant synthesizes the inverse and reverses its result once more. Guard, clear-policy and target-order variations are exact alternatives, not approximations.

### Mixed predicates and fanout

An operation `(M,V,t)` means

\[
G_{M,V,t}(x)=x\oplus e_t[(x\mathbin{\&}M)=V],
\qquad t\notin M,\quad V\subseteq M.
\]

Because the predicate excludes the target, this is an involution and a positive-phase permutation matrix. Negative literals are implemented by X conjugation around an exact MCX. The external counting control is included in every predicate. With it off, the X conjugations and fanout pairs cancel; with it on, the exact required work network acts.

Consecutive identical predicates combine target masks by XOR. For pivot p among those targets, apply fanout F from p to the other targets, the predicate-controlled pivot flip, then `F^-1`. This flips every selected target iff the predicate holds, for arbitrary pivot/target states; zero initialization is not assumed. No uncorrected relative-phase Toffoli replacement is used.

### Boolean and conjugation refinements

- Same-target ESOP cubes obey exact indicator XOR identities, including complementary-literal merging and `C XOR C·l=C·¬l`. Distance-two/three EXORLINK alternatives use a telescoping product identity.
- Fixed-polarity Reed–Muller recoding is restricted to functions of the **other** wires in a same-target run. All 32 polarities are screened, then a bounded subset is refined. This is a reversible `target ^= F(other bits)` transformation, not naive in-place execution of unrelated output ANFs.
- Dependency-DAG scheduling preserves every pair whose commutation has not been established. Additional certified commutation uses contradictory shared literals when neither gate can change the conflicting literal.
- For A toggling t by F and B toggling u by `D·L(t)`, where u is outside F and D excludes t, `A B A` toggles u by `D·L(t) XOR D·F` and restores t. That one- or two-cube conjugate allows distant A gates to cancel without dropping their action. The implementation checks the required variable restrictions and exhaustively tests the small identities before full-domain use.
- The public identity `11*16 mod 35=1` permits reversing an exact network for one multiplier to implement the other. This is compiler reuse of a public inverse operation, not extraction of the unknown order or factors.

Each rewrite uses exact positive-phase permutations, so basis-map equality extends by linearity to relative phases, superpositions and external entanglement. Actual complex-operator tests below independently support the emitted implementation; classical output tables alone would not establish phase correctness.

## 3. Native MCX and auxiliary-state contract

The selected local builder retains the existing nine-wire ABI: one control, six work and two spare dirty-wire argument slots. In the selected **native MCX** network those two slots are idle. They are existing counting wires when embedded, not two additional logical qubits. The logical block is controlled P tensor identity on both arbitrary spare states. The complete circuit still has 18 active qubits.

The solver compiles the **whole prepared circuit** with the official basis before Aer execution. Qiskit high-level synthesis can allocate workspace according to its state tracking. Do not independently compile a local block under an assumed-zero spare state and then embed that compiled block on an arbitrary dirty wire. The nine-wire logical operator audit does not certify every possible isolated HLS outcome. Distinguish the logical full-domain proof, complete prepared-circuit execution evidence, and dependence on the pinned compiler.

The intended modular work output is not uncomputed: it can remain entangled with counting qubits, as required by Shor. Only temporary synthesis state must be restored. The existing dirty-template alternatives also have exact restoration contracts; none treats a Hadamard-prepared counting wire as clean.

## 4. Bounded search, measured selection and unsuccessful directions

| Stage | Actual scope | Evidence |
|---|---|---|
| A: cheap search | 500 distinct configurations × four public multipliers = 2,000 distinct networks; seed 2026111108; all 64 work mappings and inverses checked | `search.py`, `mixed.py`, `search.json` |
| Boolean refinement | Top 15 existing networks per multiplier, three increasingly strong rewrite families; no new affine configurations | `boolean*.py`, `boolean*_results.json` |
| B: isolated scoring | 60 distinct selected multiplier candidates, with actual pinned-basis compilation | `compiled_candidates.json` |
| C: complete circuit scoring | 12 alternatives, including pivot/dirty allocation, native MCX, refined networks and a final linear probe | `whole_candidates.json` |
| Primitive diagnostics | 10 representative exact MCX-template compilations, separate from the 60 multiplier candidates | `mcx_ablation.json` |
| D/E: execution | Official baseline/candidate and bounded paired seeds; counts reported in Section 6 | `validation.json` |

All 500 configurations and every generated network are retained, with configuration/source cache keys and operation fingerprints. A repeat of the same configurations after JSON compaction was a reproducibility check, not another 500 independent searches. The original and current source identities are recorded. Search storage was compacted without removing candidate data. Stage B's exact input is retained separately as `boolean_stage_b_input.json`.

Selected complete-circuit progression:

| Screen | CX | Depth | Gates | Qubits |
|---|---:|---:|---:|---:|
| Initial affine, explicit dirty templates | 9,832 | 23,297 | 28,142 | 18 |
| Scored Boolean blocks, explicit dirty templates | 9,362 | 22,223 | 26,601 | 18 |
| Same blocks, native MCX | 9,358 | 22,013 | 26,619 | 18 |
| Additional certified commutation/conjugation | 9,334 | 21,954 | 26,562 | 18 |
| Two-cube conjugation + inverse transfer: initial checkpoint | **9,302** | **21,902** | **26,475** | **18** |

These are whole runtime-pipeline screens, then reproduced for the winner by the official Checker. Cost proxies rank candidates but do not replace those measurements.

Rejected or bounded directions:

- The existing cycle-anchor/hybrid baseline remains available, but its measured block costs are substantially higher than the selected full-domain synthesis. No shortcut confined to the useful orbit was accepted.
- Exact Iten, KG24 dirty, V24 and isolated native-MCX alternatives did not beat the current M15 template in the representative isolated comparison: six-control M15 uses 36 CX versus Iten 42, KG24 54, V24 140 and isolated native 122. Full-circuit native HLS has different context and was tested separately, rather than inferred from this table.
- Changing pivot or dirty allocation can trade CX, depth and gate count; all six complete-circuit emission combinations were measured. None introduced a new clean register.
- An expensive all-polarity/high-order ESOP refinement attempt exceeded roughly three minutes and was stopped without promoting incomplete output. The bounded replacement screens all polarities and refines only the strongest eight. Completed evidence is retained; the abandoned attempt supplies no performance claim.
- Further monotone passes on the final Boolean winners immediately stagnated. This is a stopping condition for these rewrite families, not a lower-bound proof.
- Reusing the accepted generic GF(2) CX-window pass from unchanged Tier 5 examined 8,974 windows, accepted **zero**, removed **zero CX**, and left the final complete metrics unchanged. It was not inserted into production.
- No cross-block cancellation was justified merely by equal work predicates: different external controls are not interchangeable. No unproved merging of powers or deletion of required controlled blocks was performed.

The static Pareto frontier and measured runtime frontier are separated in `pareto.json`; missing runtime/RSS for nonfinalists is not treated as zero. Offline public permutation tables, synthesis search and caches are extra classical work with exponential scaling in work-register width, not a free scalable modular-arithmetic algorithm.

### User-authorized extension and final selection

After completing the original funnel and preserving the independently validated 9,302-CX checkpoint, the user requested additional attempts within the same hour, including notification of larger architectural changes. The added work is separate from the original limits:

- `adaptive_search.json`: **4,000 additional distinct configurations**, none repeated from the initial 500, seed `2026111109`, 80.31 s. Each is applied to four public multipliers: 16,000 complete forward/inverse checks, 15,991 distinct networks. All configuration costs and fingerprints are retained; the top ten operations per multiplier are retained for exact refinement/replay.
- `adaptive_boolean.json`: frozen third-stage Boolean rules refine those **40** networks (3.54 s), including public inverse transfer. Weighted proxy cost is 7,756 CX before whole-circuit compilation; this is not a measured official metric.
- `affine_linear.json`: 1,000 attempts / **996 distinct configuration-network pairs**, 24 refinements, 9.15 s, exploring a larger invertible linear coordinate transform L built from CNOTs. If E=B∘L, decoding only bit-permutation/XOR B leaves the controlled middle L P L⁻¹; chronological unconditional L, controlled middle, L⁻¹ implements P when enabled and identity when disabled. The full encoded table, including original padding, is conjugated. This architecture required no extra qubits and passed full-domain symbolic/inverse checks, but scored **8,566 CX / 19,822 depth / 24,092 gates**, worse than the selected adaptive scheme. It is retained as an experiment, not installed or claimed officially validated.
- **Five additional complete-circuit screens**, including `adaptive_whole.json` and the four alternatives in `extension_candidates.json`. No old twelve-candidate ledger was reset. Native first-pivot scored 7,876 / 18,794 / 22,881; native last-pivot scored **7,856 / 18,804 / 22,861**; dirty first-pivot 7,878 / 19,098 / 22,893; dirty last/external-first 7,858 / 18,813 / 22,859. All use 18 active qubits.

The final native last-pivot choice saves 20 CX and 20 total gates over native first, for ten extra depth units. Dirty-last trades two fewer total gates for two more CX and nine more depth units. Native-last was selected by prioritizing CX and depth; dirty-last remains a Pareto alternative. Unknown rival metric minima prevent a universal ordering of their actual competition scores. The mathematical fanout identity is valid for either pivot and arbitrary target states; final emitted operators were tested independently. The final production code uses no general-L boundary, new quantum register or new classical answer-recovery algorithm. It is not a globally optimality proof.

Native-last complete-circuit construction/scoring compilation took **0.21855 / 0.15726 s** in its screen (0.37581 s total); these are measured single runs, not timing guarantees. `extension_verification.json` belongs to the intermediate 7,876-CX first-pivot version. `final_verification.json`, `candidate.json` and `final_validation.json` identify the installed last-pivot version. Neither intermediate audit nor checkpoint seeds are relabeled as final runs.

## 5. Mathematical verification evidence

`final_verification.json` audits the **installed 7,856-CX production implementation**; `verification.json` separately records the retained 9,302-CX checkpoint. For each actual multiplier it constructs the complete 512×512 complex operator on all nine local wires and compares it directly with an independent analytic modular permutation and its inverse.

- All 64 work inputs, both external controls and all four values of the two spare/dirty slots are included: **512 columns per multiplier**, four multipliers.
- Original padding 35–63, control-off identity, arbitrary extra-wire initial values and restoration are checked.
- Maximum final complete-operator/inverse error: **3.352913e−14**; no global-phase fitting is applied. Acceptance tolerance is 1e−9; the measured error is reported explicitly rather than substituted by that tolerance.
- Maximum observed spare-wire leakage is **0.0** for this selected native network, whose two compatibility slots are logically idle.
- Eight arbitrary-target/mixed-predicate fanout fixtures pass using the generic dirty emitter; the selected native emitter is covered separately by the four complete controlled-operator tests. A small modulus-5 full Fourier comparison exercises the retained general-width fallback and unchanged Fourier wiring, not the modulo-35 cache by itself. Register initialization, all 12 power labels and measurement mapping also pass.
- The final production-file digests match `candidate.json` and the runtime dependency identities recorded with the audit. The earlier 9,832-CX candidate has its own separate `first_verification.json`; its evidence is not mislabeled as the final audit.
- Boolean identities include exhaustive three-wire cases and full 64-input forward/inverse checks on every retained refined network. The second-family synthetic suite records 1,209 checks; the third-family report adds the two-cube conjugation checks.

**Additional complete prepared-state check for the 9,302-CX checkpoint.** `full_state.json` removes only final measurements in validation copies, compiles each full 18-qubit prepared circuit as production does, and compares all **262,144 complex amplitudes** in RAM without phase alignment. Baseline/checkpoint maximum amplitude difference is **1.8816e−13**, maximum joint-probability difference **1.4955e−14**, and maximum counting-register marginal difference **1.6245e−13** (acceptance tolerance 1e−8). This directly checks the actual prepared state after whole-circuit HLS; it is not a full 18-qubit operator comparison for arbitrary input states. Compilation took **0.8198 / 0.1822 s** and validation-only Aer evolution **50.3258 / 9.4629 s**. No private state arrays were written and production measurement circuits were not changed. The runtime digests identify this checkpoint, not an untested extension.

**Final complete prepared-state check.** `final_full_state.json` separately repeats the full 18-qubit comparison for the installed **7,856-CX** runtime. All 262,144 complex amplitudes are compared without phase fitting: maximum amplitude error **1.8512480e-13**, maximum joint-probability error **1.5990681e-14**, counting marginal error **1.7585933e-13**; **PASS** at 1e−8 tolerance. Baseline/final validation-only Aer evolution took **45.7861 / 9.5766 s**, compilation **0.89990 / 0.15895 s**. These audit timings are distinct from the five-pair mean. This verifies the actual prepared-state result after complete-circuit synthesis, while the independent nine-wire operators cover arbitrary local control/work/dirty inputs. Arrays stayed in memory; only safe scalar discrepancies and source hashes were saved.

These are exact mathematical constructions supported by finite numerical implementation tests. They are not a dense full 18-qubit operator proof, a formal verification of Qiskit, or quantum-hardware experiments. A hash match verifies the recovered plaintext, not unitary equivalence or the causal role of measurement.

## 6. Official execution and paired reliability

<!-- VALIDATION_SUMMARY_START -->
### Final selected 7,856-CX candidate — independent new validation

`final_validation.json` records the final native-last implementation, runtime fingerprint `b92abecb8e2ddaf76550f900e267cf2a350555392346676fa436b7ef40b9cf9d`, and production module SHA-256 `05de0badc51b92a1422d1471d2697e50108b9915b3f54a13a0eba2e7584a8187`. The original strict benchmark code and acceptance function were reused unchanged.

Both official baseline and final candidate returned **FULL / SHA-256 match / actual Aer / valid metrics / flags []**, with resource state `ok`. Official solve times were **40.962 / 6.481 s**, whole-Checker wall times **43.9746 / 8.2733 s**, sampled process-tree peak RSS **366.6211 / 170.5273 MiB**. The final scoring circuit is **7,856 CX, 18,804 depth, 22,861 gates and 18 active qubits**.

Five fresh paired seeds completed: **10/10 individual PASS, 5/5 complete paired PASS**, no FAIL, UNCONTROLLED, SKIP, timeout or memory failure. Each run recorded its actual requested seed forwarded to Aer, one executed circuit/job and 64 shots. Each recovered/decrypted output matched SHA-256. The five-pair final study is distinct from the earlier ten-pair 9,302-CX checkpoint; it is not reported as ten final pairs. Additional final seeds were not launched because the remaining one-hour budget was reserved for full-state verification, evidence review and Git handoff.

| Actual Aer seed | Baseline / final | Solve seconds baseline / final |
|---:|---|---:|
| 1000 | PASS / PASS | 32.949 / 23.007 |
| 2000 | PASS / PASS | 49.450 / 7.134 |
| 3000 | PASS / PASS | 58.939 / 6.896 |
| 4000 | PASS / PASS | 68.254 / 7.474 |
| 5000 | PASS / PASS | 52.730 / 5.800 |

| Final paired statistic | Baseline | Final 7,856-CX candidate |
|---|---:|---:|
| Mean solve, s | 52.4644 | 10.0622 |
| Median solve, s | 52.7300 | 7.1340 |
| Maximum solve, s | 68.2540 | 23.0070 |
| Mean sampled peak RSS, MiB | 354.9750 | 157.3844 |
| Maximum sampled peak RSS, MiB | 357.3125 | 158.6211 |
| Mean observed Aer job elapsed, s | 51.8605 | 9.9369 |

The paired means show a local observed solve-time reduction; they do not imply unconditional quantum speedup or a universal simulator speedup. Five seeds are a finite reliability sample. Runtime and RSS remain comfortably within the unchanged competition limits in these runs.

### Validated 9,302-CX checkpoint — evidence retained independently of the extension

`validation.json` binds the **9,302 / 21,902 / 26,475 / 18** checkpoint to runtime source fingerprint `c9ddd0e022d3e4a74883582bf7e58fb037c883998af1b464aa7851936f1f4120`. Its `extreme_synthesis.py` digest is `f32f03cae1c0c69ea0a5b7f004e76d0b0a526df5ce5ce53b1230e3875562224f`. The checkpoint complete prepared-state comparison in Section 5 has the same runtime digests. These results do not automatically validate a later network with a different fingerprint.

Both separate unmodified official checks returned **FULL**, matching SHA-256, actual Aer execution, valid metrics, empty flags, and no timeout or resource error. Baseline official solve was **80.484 s**; checkpoint solve was **9.040 s**. Their whole-Checker wall times were **84.3375 / 10.9747 s** and sampled process-tree peaks **358.61 / 180.54 MiB**. Those single official timings are not the paired-sample statistic.

All **ten paired seeds** (1000 through 10000, step 1000) passed: **20/20 PASS**, zero FAIL, UNCONTROLLED or SKIP. Every worker recorded the actual requested seed at Aer, one completed job/circuit and **64 shots**, with a matching plaintext hash. The paired workers verify recovery and seed control; the separate official stage establishes the scoring metrics and empty flags.

| Actual Aer seed | Baseline / checkpoint | Solve seconds baseline / checkpoint |
|---:|---|---:|
| 1000 | PASS / PASS | 32.414 / 7.627 |
| 2000 | PASS / PASS | 61.776 / 10.397 |
| 3000 | PASS / PASS | 64.813 / 14.603 |
| 4000 | PASS / PASS | 37.779 / 19.453 |
| 5000 | PASS / PASS | 41.668 / 7.534 |
| 6000 | PASS / PASS | 43.082 / 13.732 |
| 7000 | PASS / PASS | 71.079 / 12.861 |
| 8000 | PASS / PASS | 53.906 / 12.491 |
| 9000 | PASS / PASS | 38.920 / 11.109 |
| 10000 | PASS / PASS | 69.415 / 8.621 |

| Paired statistic | Baseline | 9,302-CX checkpoint |
|---|---:|---:|
| Mean solve, s | 51.4852 | 11.8428 |
| Median solve, s | 48.494 | 11.800 |
| Maximum solve, s | 71.079 | 19.453 |
| Mean sampled peak RSS, MiB | 351.0105 | 166.3496 |
| Maximum sampled peak RSS, MiB | 357.2461 | 168.0703 |

Environment: local Linux x86_64, Python 3.12.14, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4, psutil 7.2.2. No OSC jobs were used. Search/compilation activity and changing host load limit causal runtime claims; the observed means are descriptive, not a hardware-speedup or future-runtime guarantee.

**Evidence separation:** the final 7,856-CX candidate now has its own complete operator, official and five-pair results above. This checkpoint retains its original ten-pair evidence and may be restored from `accepted_checkpoint_9302/`; neither study is relabeled as the other.
<!-- VALIDATION_SUMMARY_END -->

The runner reuses the pinned Benchmark Harness `ab9676749e00da904d0b8076811a2407d3b7205f`, including its **unchanged strict PASS/FAIL/UNCONTROLLED function**, process-tree monitor and safe-output worker. Baseline and candidate are separate snapshots, and only Tier 8 entrypoints remain enabled. Shared modules remain available. Official Checker calls use the solver's original seed; paired trials separately inject and record requested Aer seeds and finished jobs. These are distinct experiments, not repeated fixed-seed runs presented as independent samples.

The official solve and scoring-transpile limits remain 120 seconds each. The wrapper has the existing 370-second complete-official outer cap, 120 seconds per paired worker and a 2,048 MiB process-tree cap. Trials are sequential and retain every failure; no timeout or memory failure is silently retried. CPU simulation uses the pinned environment and two Aer threads. RSS is a 20 ms sampled sum across processes, which can miss peaks and double-count shared pages. Timing is environment/load-sensitive; a finite seed set does not establish universal speed or zero failure probability.

## 7. Simplicity opportunity

Tier 8's pool is 2.25 points. For a fixed hypothetical rival minimum vector R and an implementation V, the positive-metric score is

\[
S(V;R)=2.25\sum_m w_m\frac{\min(V_m,R_m)}{V_m},
\quad w=(0.4,0.3,0.2,0.1).
\]

For this dominating resource vector, the maximum possible increase over unknown eligible rivals is

\[
2.25\left[0.4(1-7856/33904)+0.3(1-18804/96055)
+0.2(1-22861/102561)\right]=\mathbf{1.58401264}.
\]

This is an upper bound, **not an actual competition score**. If we already led every metric, both implementations obtain the same maximum simplicity score and the gain is zero. Hypothetical rival minima equal to the candidate attain the bound; rival gate metrics at half the candidate values (18 qubits) halve that gain. `simplicity.json` contains exact scenario calculations and explicitly labels the competitor values as hypothetical. No other team's results were accessed or assumed.

## 8. Decision, limitations and handoff

<!-- DECISION_START -->
**9,302-CX checkpoint: ACCEPT_RESEARCH.** Its exact full-domain construction, complex block and full prepared-state tests, unchanged official Checker FULL/hash/valid-metric/no-flags result, ten strict controlled paired seeds, material resource improvement and bounded runtime/RSS support this research verdict. This is not release acceptance or a guarantee of every future seed. The original final submission package remains untouched.

**Final selected 7,856-CX native-last candidate: ACCEPT_RESEARCH.** All four complete controlled operators and the final full prepared-state comparison pass; the unchanged official Checker reports FULL/hash/valid metrics/no flags, five new controlled paired seeds pass, and all four scoring resources improve or stay equal to the pinned baseline. Local time and sampled RSS remain bounded. This verdict applies to the recorded source digests and pinned environment; it is not release integration, mathematical optimality, a hardware-speedup claim or an assurance for all future seeds.
<!-- DECISION_END -->

Before any separately authorized release change, another reviewer should verify the generated cache against the public compiler, the native-HLS whole-circuit contract and the exact tested source hashes; replay on the target environment; run the integrated submission checks; and separately rebuild/audit any changed submission artifact. Preserve the current final package as fallback. This research does not change its deadline, digest or submission status.

The result demonstrates an exact toy-sized quantum circuit improvement. It does not demonstrate scalable classical synthesis, practical cryptographic key breaking, real quantum hardware, or unconditional quantum speedup. The strongest statements are the actual reported metrics, the scoped phase-sensitive tests and the bounded real Aer execution records.

Reproduction steps and the full artifact map are in [the research README](../research/tier08_extreme/README.md).

Source integrity: `scope_verification.json` records 97 protected tracked Tier/official files identical to the pinned RC. Only the Tier 8 modular dispatcher changes an existing production file. `baseline_profile_recheck.json` confirms the retained hybrid still produces 33,904 / 96,055 / 102,561 / 18 after the research dispatcher is installed; the reproduction helper explicitly selects that retained baseline. The release branches and final-package ref were checked unchanged before handoff.
