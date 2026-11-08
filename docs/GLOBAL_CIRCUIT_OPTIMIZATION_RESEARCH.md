# Global quantum circuit optimization research

This is a **research toolkit**, based on frozen v5 `41c7c6775b8fc499c2acdd878b4829bd17e1210d`. No production tier imports it. This work changes only `research/circuit_optimizer/` and this new report. It does not integrate changes from other branches or modify final submission documents, official tools, challenge data, or release artifacts. All new experiments are small synthetic circuits: no protected Oracle inspection, Aer solve, full Checker, or competition-score claim is made.

## 1. Inventory: reused reasoning, not repeated tier experiments

These are historical results read from the cited commits, **not measurements performed in this research**. Development acceptance and integration into a verified release are distinct.

| Tier | Existing transformation and evidence | Reusable condition |
|---|---|---|
| 2 | [689c998: template reuse](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/689c998ca03a49154c1f29dd2fa99fd8fa4af180/docs/TIER02_BB84_OPTIMIZATION_RESULTS.md): construct two Bob receiver templates instead of 2,048, still execute all independent measurements. Scoring metrics unchanged. | Cache immutable operation templates, never states, secret inputs, or measurement results. Official Channel copies each circuit. This is classical construction efficiency. |
| 5 | v5 folds public S-box/permutation constants through the known-byte comparison: 21,150 → 15,150 2Q. [0988ac4: additional MCX8 work](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/0988ac44d88d08cc12258f2010afaf792dd53e7b/docs/TIER05_TIER08_ADVANCED_OPTIMIZATION.md) uses exact M15 dirty synthesis, 15,150 → 14,700, with three borrowed key wires instead of six. | Reversible compute/mark/uncompute must retain every marked state, restore scratch, and preserve controlled phases. The later report has five paired seeds, fewer than the independent protocol's ten-seed gate. |
| 6 | [5a73467: pretranspilation](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/5a73467f57684e4dbf4fb4d9fe1d7b76e56f71c2/docs/TIER03_TIER06_OPTIMIZATION_RESULTS.md): level 2 retains 3,000 2Q, reduces depth 5,883 → 5,715 and total gates 9,534 → 8,752. | Compiler effects require measuring the actual executed circuit after the official scoring pass; settings alone are not a mathematical improvement. |
| 7 | [7aef6e7: input reversal](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/7aef6e714dbbc8d222ef168b4bd691078f823b6e/docs/TIER01_TIER04_TIER07_OPTIMIZATION_RESULTS.md): 230 → 209 2Q, same-host depth 268 → 265. | Conjugate all relevant wires and use a permutation-invariant prepared count register; retain QFT sign and classical bit labels. |
| 8 | [v5 independent acceptance](TIER08_INDEPENDENT_ACCEPTANCE.md): exact M15 MCX6 reduces borrowed wires 4 → 2 and 49,920 → 42,810 2Q. Later [0988ac4 QFT work](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/0988ac44d88d08cc12258f2010afaf792dd53e7b/docs/TIER05_TIER08_ADVANCED_OPTIMIZATION.md): 42,810 → 42,792. | Borrowed counting wires can be entangled; both external controls and borrowed wire arguments must be conjugated. |
| 9 | [17df36d: shared predicate](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/17df36d1c31cd441cd3bd840157caadd3062cada/docs/TIER09_OPTIMIZATION_RESULT.md): adjacent equal-predicate MCX targets replaced by an exact fanout conjugation; 117,739 → 89,075 2Q. | Targets lie outside the predicate, equal targets cancel modulo two, and each primitive has phase +1. |
| 10 | [7c9d032: fanout and QFT](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/7c9d03238835a8b02fbf489440440059cad4ee13/docs/TIER10_FULL_OPTIMIZATION_RESULT.md): 107,168 → 82,804 2Q with 19 active qubits. | The ancilla-free pivot fanout is an exact conjugation; both Fourier registers and high-Z/low-X readout must remain consistent. |

The common identities are reversible linear row addition, exact conjugation by wire or fanout permutations, clean-workspace isometries, dirty-workspace identity, and cancellation through proven commuting operations. For the prior shared-predicate construction, let $F$ fan out pivot $p$ into the other targets. Then $F^{-1}X_p^{f(c)}F$ flips every selected target iff $f(c)=1$. Predicate wires must be disjoint from all targets. The toolkit does not rerun that already validated production experiment. Its MCX resource survey also omits the standalone four/five-control one-clean KG24 cases already reported for Tier 9; API unit tests still validate the relevant contracts.

## 2. GF(2) extraction and synthesis

[`gf2_synthesis.py`](../research/circuit_optimizer/gf2_synthesis.py) accepts an explicitly supplied CNOT-only block with no classical bits. It never decomposes or reads an opaque gate. For column vectors of little-endian wire bits, $y=Mx$ over $\mathbb F_2$. Starting with $M=I$, CX(control $c$, target $t$) performs row addition $M_t\leftarrow M_t\oplus M_c$.

Gauss–Jordan elimination records elementary row additions $E_1,\ldots,E_k$ with $E_k\cdots E_1M=I$. Each $E_j$ is self-inverse, so $M=E_1\cdots E_k$; a circuit must execute the recorded operations in **reverse chronological order**. Pivot exchanges are three row additions, equivalent to three CX gates, and do not silently relabel physical wires. Singular or nonbinary matrices are rejected. For CNOT networks all nonzero matrix amplitudes are +1, so equal binary maps imply equal quantum operators on every superposition and entangled extension. The extractor represents only the linear map; `optimize()` additionally preserves the original circuit's global phase.

The implementation uses polynomial-size binary matrices and elementary elimination, not a dense quantum unitary. It is not a minimum-CNOT or minimum-depth solver. A guard retains the original if logical gate count or depth increases, or if neither improves. That guard cannot promise lower resource metrics after a separate compiler; compiled comparisons remain mandatory. Mixed X/CNOT affine maps, Toffolis, measurements, and custom gates named `cx` are rejected rather than treated as linear.

## 3. Systematic QFT boundary relabeling

[`qft_relabeling.py`](../research/circuit_optimizer/qft_relabeling.py) recognizes a complete **explicit** leading or trailing reversal layer: exactly the disjoint SWAP pairs prescribed by a caller-supplied ordered register. A missing swap, wrong pair, interleaved gate, or opaque QFT wrapper is rejected. Registers may be noncontiguous. The operation is applicable to any unitary core, not just Fourier transforms. It does not infer the algorithm's register semantics or open a protected Oracle.

For an input reversal, write the original operator as $U=CRP$, where $P$ is the supplied prefix, $R=R^{-1}$ reverses a register, and $C$ is the core. Rewiring **every** quantum argument in $P$ gives $P'=RPR$, including targets, borrowed ancillas, and controls. The returned candidate is

$$
V=CP'=CRPR=UR.
$$

Thus $V(R|\psi\rangle)=U|\psi\rangle$ for arbitrary input. If $R|\psi\rangle=|\psi\rangle$, the prepared outputs are exactly equal with no input operation. `InputReversalPlan.required_input_permutation` is returned explicitly; the toolkit never assumes that an arbitrary input state is invariant. The arbitrary-input operator relation is tested, not inferred from one classical count string.

For an **output** reversal, $U=RC$. If the original immediate computational-basis measurement maps physical wire $j$ to classical bit $m(j)$, the core-only circuit must measure wire $R(j)$ into $m(j)$. For any density operator the measurement projector is conjugated by $R$ in exactly the same way, so the complete distribution on those classical bits is equal. This is a measurement-preserving change, not unrestricted unitary equality. It requires immediate computational-basis readout and does not authorize dropping swaps before further quantum gates. Caller-supplied classical indices include register offsets; no reversal of displayed strings is performed.

The inverse-QFT helper is checked against $F^{-1}_{yx}=2^{-n/2}\exp(-2\pi ixy/2^n)$ for every matrix column at widths 1–4. Tests also cover arbitrary complex inputs, noncontiguous count wires, a prefix touching borrowed wires, partial readout, and an asymmetric high-Z/low-X classical layout.

## 4. Exact MCX budgets and phase correction

[`mcx_benchmark.py`](../research/circuit_optimizer/mcx_benchmark.py) separates no-ancilla, one/two-clean, and one/two-borrowed KG24/HP24 candidates under declared budgets. These budgets are caller obligations, not facts inferred from spare wire labels. A clean contract is

$$
W(|\psi\rangle\otimes|0^a\rangle)
=(\operatorname{MCX}|\psi\rangle)\otimes|0^a\rangle.
$$

It does not specify the dirty-input subspace. A borrowed contract is $W=\operatorname{MCX}\otimes I_a$ on all inputs, including entangled ancillas. The bounded survey verifies every relevant complex operator column before and after transpilation: zero-ancilla columns for clean candidates, all columns for borrowed/no-ancilla candidates. It checks amplitude +1, no leakage, and restoration without fitting a global phase. Thus these **small instances** also remain equivalent under an added external control. The dense check is capped at eight qubits; no large-circuit operator is constructed.

Relative-phase Toffoli is intentionally tested as a failure case. In Qiskit's little-endian ordering, RCCX sends $|3\rangle\mapsto i|7\rangle$, $|7\rangle\mapsto-i|3\rangle$, and $|5\rangle\mapsto-|5\rangle$. Applying

$$
D=\operatorname{diag}(1,1,1,i,1,-1,1,-i)
$$

after RCCX gives $D\,\mathrm{RCCX}=\mathrm{CCX}$ exactly. The prototype verifies this identity and its externally controlled form. The correction is explicit; a bare RCCX substitute is rejected. The corrected circuit costs more CX than a native exact CCX here. A global scalar can also become a relative phase under control, so no general equivalence test in this toolkit discards global phase.

## 5. Commutation-aware inverse cancellation

[`commutation_rules.py`](../research/circuit_optimizer/commutation_rules.py) scans backward from each gate, stopping at the first operation for which commutation is unproven. It removes a matching inverse only after crossing proven commuters. If $G$ commutes with every factor of a window $A$, then $G^{-1}AG=A$. Every accepted rule is an exact operator identity on the full Hilbert space; no ancilla initialization assumption is used.

Supported rules are disjoint native gates; diagonal native gates commuting with one another; CX(c,t) and CX(d,u) when $c\ne u$ and $d\ne t$; a single-wire diagonal gate on a CX control; and X/RX on a CX target. Self-inverse gates cancel on identical ordered quantum arguments. S/Sdg and T/Tdg are exact pairs; rotations cancel only when the finite numeric angles are exact negatives. No modulo-$2\pi$ reduction is used: RX($2\pi$) is $-I$. Measurements, resets, barriers, symbolic parameters, control flow, and unknown/custom gates stop the search even on disjoint wires. Anti-commuting X/Z, crossed CX, and noncanonical control states receive no rewrite.

The output keeps the original quantum/classical registers and global phase. Cancellation can make a wire inactive but never reorders or deletes a wire. The whitelist is deliberately incomplete, and the scan is quadratic in the worst case; this is a small-block research pass rather than a general compiler.

## 6. New experiments and measured resources

Run from this worktree with the existing pinned environment; there are no added dependencies beyond repository Qiskit/NumPy. No Aer simulation is needed.

```bash
python -m unittest research.circuit_optimizer.equivalence_tests -v
python -m research.circuit_optimizer.run_benchmarks --out research/circuit_optimizer/results/synthetic_qiskit261.json
```

The [machine-readable results](../research/circuit_optimizer/results/synthetic_qiskit261.json) contain settings, platform, raw compilation timings, logical and compiled metrics, and maximum complex-amplitude residuals. The settings match the official static-circuit basis/configuration (`rz,sx,x,cx`, all-to-all, level 1, seed 12345, no initial layout). The measured object is a **synthetic standalone circuit**, not an actual tier's scored Aer circuit. Qiskit 2.6.1 and NumPy 2.3.5 were used. Measurements/barriers/reset/delay do not count as gates; allocated and active widths are reported separately. Timings are one observation per circuit, include compiler startup/cache effects, and do not support a compilation-speed claim.

| Synthetic case | 2Q before → after | Depth | Total gates | Allocated / active qubits before → after | Compile ms before → after |
|---|---:|---:|---:|---|---:|
| gf2_seed144_6w_40cx | 36 → 19 | 27 → 13 | 36 → 19 | 6/6 → 6/6 | 108.262 → 1.482 |
| commutable_inverse_window | 3 → 1 | 4 → 2 | 5 → 3 | 4/4 → 4/3 | 2.540 → 1.260 |
| input_reversal_3count_2work | 22 → 19 | 49 → 46 | 74 → 71 | 5/5 → 5/5 | 3.477 → 1.745 |
| output_reversal_3w | 9 → 6 | 20 → 17 | 23 → 20 | 3/3 → 3/3 | 2.791 → 3.270 |
| corrected_relative_toffoli | 6 → 9 | 13 → 18 | 18 → 22 | 3/3 → 3/3 | 1.986 → 4.646 |

The GF(2) fixture is a deterministic six-wire random 40-CX block (seed 144); official-equivalent compilation alone reduces it to 36 CX, while row synthesis gives 19. The inverse-window example removes six source operations, including two CX; its compiler result improves as shown. QFT rows use explicit mapping contracts, and the output row compares $U=RC$ rather than incorrectly comparing $U=C$. Corrected RCCX is mathematically valid but is rejected as a resource optimization in this context.

| Controls | Family | Workspace contract | 2Q | Depth | Total | Allocated / active | Compile ms |
|---:|---|---|---:|---:|---:|---|---:|
| 3 | noaux_hp24 | 0 none | 20 | 37 | 48 | 4/4 | 2.800 |
| 3 | one_clean_kg24 | 1 clean | 12 | 30 | 40 | 5/5 | 1.447 |
| 3 | two_clean_kg24 | 2 clean | 12 | 30 | 40 | 6/5 | 1.293 |
| 3 | one_dirty_kg24 | 1 dirty | 18 | 38 | 53 | 5/5 | 17.358 |
| 3 | two_dirty_kg24 | 2 dirty | 18 | 38 | 53 | 6/5 | 12.584 |
| 4 | noaux_hp24 | 0 none | 48 | 98 | 124 | 5/5 | 15.219 |
| 4 | two_clean_kg24 | 2 clean | 18 | 48 | 62 | 7/6 | 11.361 |
| 4 | one_dirty_kg24 | 1 dirty | 30 | 77 | 97 | 6/6 | 17.645 |
| 4 | two_dirty_kg24 | 2 dirty | 30 | 77 | 97 | 7/6 | 3.913 |
| 5 | noaux_hp24 | 0 none | 88 | 156 | 223 | 6/6 | 23.619 |
| 5 | two_clean_kg24 | 2 clean | 24 | 60 | 84 | 8/7 | 22.943 |
| 5 | one_dirty_kg24 | 1 dirty | 42 | 109 | 141 | 7/7 | 1.997 |
| 5 | two_dirty_kg24 | 2 dirty | 42 | 101 | 141 | 8/7 | 14.223 |

Workspace is the template's allocated ancillary width, even if a small-case decomposition leaves some wires untouched. For example, five-control two-clean KG24 allocates eight wires but touches seven; allocation and active-qubit scoring are different costs. Extra clean workspace reduces gates in this survey but can increase statevector memory or scheduling constraints in a full application. These tables do not authorize substituting clean-ancilla templates for dirty ones.

**Validation:** 12 unittest cases pass. They cover all 168 invertible three-wire GF(2) matrices with all computational-basis amplitudes; 40 seeded random CNOT circuits at widths 2–6 with nonzero global phase; 30 random native circuits for cancellation; every Fourier matrix column at widths 1–4; arbitrary-state input-permutation identities; output probabilities for all 16 basis states plus a complex superposition in a two-register layout; exact MCX clean/dirty contracts; controlled phase correction; and rejected symbolic, opaque, nonunitary, singular, and phase-unsafe inputs. Benchmark circuits are independently checked again after transpilation with `atol=1e-10, rtol=0`. These floating-point checks support the algebraic proofs; they are not symbolic arithmetic or production Checker evidence.

## 7. Potential applicability across Tier 1–10

| Tier | Potential future use | Boundary |
|---|---|---|
| 1 | Explicit team-owned CNOT blocks, if any are later introduced. | Current BV exterior has no nontrivial CNOT block; required opaque Oracle remains untouched. |
| 2 | Immutable receiver-template reuse and conservative native cancellations. | Channel ownership, blind basis choice, independent shots and classical position mapping must be preserved. No new score opportunity established. |
| 3 | Native preparation/readout cancellation if a legal block exists. | Opaque DJ Oracle cannot be read to obtain its classification or rewritten by this toolkit. |
| 4 | GF(2) synthesis of eligible quantum linear blocks. | Classical nullspace solving is separate; do not extract a hidden period from Oracle gates. Current exterior offers no such block. |
| 5 | Whitelisted local cancellation and budget-aware MCX evaluation around public reversible predicates. | Preserve all marked keys, number of Grover iterations, exact phases and scratch restoration. Existing constant folding/M15 gains are historical. |
| 6 | Same public-Grover blocks plus explicit compiler comparisons. | Existing pretranspilation savings must not be counted again. Preserve measured-candidate filtering and search iteration count. |
| 7 | Input-reversal plan and phase-sign/readout tests. | QFT relabeling already exists on a development branch; this toolkit offers a reusable check, not another new gain. |
| 8 | Whole-register conjugation including borrowed counting wires. | Modular padding semantics, measured order recovery and dirty restoration remain mandatory. Existing QFT work is not rerun. |
| 9 | CNOT fanout blocks and exact MCX-budget tests. | Preserve shared predicate/target disjointness and full controlled modular unitary; no merger of different controls without proof. |
| 10 | The same fanout analysis plus two Fourier-register mapping plans. | Preserve high-Z/low-X layout and decrypt interface; no direct transfer of small benchmark savings. |

Before any integration, isolate an authorized team-owned block, write its exact domain and workspace contract, retain complete complex phase, and validate the corresponding mapping on small/full feasible cases. For a larger block use the compositional identity and focused subblock checks. Compare the **actual executed** circuit under the original official scoring configuration, run the original single-tier Checker in a renamed submission directory, require `full`/SHA match/valid metrics/no flags, and use the applicable independent benchmark protocol (including at least ten actual paired seeds, resource limits and rules review where required). Then perform package validation before any release. Existing evidence from a different branch, tier, seed set or compiler environment is not acceptance of this prototype. This branch ends with research code and evidence only.
