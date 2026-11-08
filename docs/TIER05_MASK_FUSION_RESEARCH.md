# Tier 5 mask transition fusion research

Decision: **REJECT for the requested two-qubit-gate reduction**. An exact prototype is a depth/total-gate tradeoff, not a CX improvement. No production source, official tool, frozen release, other tier, or ZIP was modified. Research base `4d79b7fa66d0acd4786d71be3c3ac2d291618c69`; actual candidate construction from `0988ac44d88d08cc12258f2010afaf792dd53e7b`, with its existing post-native GF(2) pass. The earlier cost decomposition was provided in the preceding task; it was not a committed file.

## Structure and proof

Let key bits be `k[0..9]`, work bits `w[0..7]`, and flag `f`. The public mask at byte index i is the XOR map `M_i: (k,w,f) -> (k,w xor m_i(k),f)`, with rotated key index `r_j = k[(j-3i) mod 10]` and `m_i,j = r_j xor r_(8+j mod 2) xor (r_(j+1) and r_(j+3))`. Each mask consists of 16 CX and 8 CCX. Key controls never change and all targets are work bits, so the XOR gates commute; each mask is self-inverse on arbitrary work inputs. There are no secret inputs, key searches, or factoring answers in this construction.

Write `A=M_0`, `B=M_1`; `C` is the first public equality comparator (including its X wrappers), and `D` is the second comparator conjugated by H on the flag. In execution order the original is `A C A^-1 B D B^-1 A C^-1 A^-1`. The first comparison toggles the flag; its borrowed key wires and work controls are restored by its exact MCX. Before the original B computation, A is uncomputed so B sees the correct initially zero work. After D, B is uncomputed before recomputing A and reversing C; at exit work and flag are restored on the intended zero-work/zero-flag input. Diffuser clean-ancilla preconditions and measurement `q[j] -> c[j]` remain unchanged.

We replace the two **adjacent** pairs `A^-1 B` and `B^-1 A` by `F` and `F^-1`, where `F` XORs `m_0(k) xor m_1(k)` into work. This does not move any gate across C or D; the work after F equals the original work immediately before D. Hence the complete operator is exactly unchanged for arbitrary key, work and flag inputs, not just basis populations: each constituent is a positive-phase reversible permutation and the unchanged H/MCX/H and equality wrappers retain their phases. Compositional equality covers control superpositions and external entanglement, while the original algorithm's clean-work restoration follows from its original contract. It does not imply arbitrary dirty work is a valid Grover oracle.

Commuting a work-targeting mask through a comparator is generally invalid because the comparator controls depend on those work bits. Delaying reset or sharing a value across a comparison without an equivalent transition was therefore not done. The two rotated masks have **48 distinct target/control monomials out of 48**, so there are no identical terms to cancel for this adjacent pair. This rules out direct common-term cancellation for this pair, not more general nonlinear synthesis or all possible shared subexpressions. A combined linear GF(2) map was also synthesized with the existing optimizer; it did not find a shorter source CX realization. Reordering commuting linear and quadratic gates did improve depth, but it destroyed some favorable compiled GF(2) windows.

## Measurements

Measured locally on Python 3.13.9, Qiskit 2.6.1/Aer 0.18.2; Aer-target native compilation with `rz,sx,x,cx`, level 1, transpiler seed 12345, no coupling restriction, then the existing consecutive-CX GF(2) rewrite and the official level-1 scoring pass. Counts exclude measurements; allocated/active qubits are shown where relevant. Times are one-shot compiler observations, not simulation benchmarks. Resource counts for the complete circuit were measured directly rather than extrapolated.

| Circuit | 2Q CX | Depth | Total gates | Allocated / active qubits |
|---|---:|---:|---:|---:|
| Adjacent pair, original | 126 | 201 | 318 | 19 / 18 |
| Pair, commuting-term reorder | 128 | 120 | 310 | 19 / 18 |
| Pair, linear GF(2) then quadratic | 128 | 98 | 280 | 19 / 18 |
| Whole oracle, original | 536 | 1,015 | 1,424 | 19 / 19 |
| Whole oracle, fused | 540 | 840 | 1,356 | 19 / 19 |
| Full 25 iterations, existing candidate | **14,552** | **28,132** | **40,938** | 19 / 19 |
| Full 25 iterations, fused prototype | **14,652** | **23,757** | **39,238** | 19 / 19 |

The full circuit's unrewritten native CX count was 14,700 in both cases. The old pass removed 148 CX; the prototype pass removed 48. Actual full compilation therefore costs 100 more CX while reducing depth by 4,375 and total gates by 1,700. These numbers cannot be obtained reliably by multiplying isolated pair costs because compilation crosses block boundaries. The GF(2) pass and native compile costs are classical overhead; isolated one-shot compile observations are in `research/tier05_mask_fusion/results.json`. No controlled simulator runtime comparison was made.

## Verification and checker

`experiment.py` checks exact parity of the complete linear and quadratic ANF term sets, all **1,024 key branches**, and equality of the complete GF(2) linear maps. Since masks only XOR a key function into work and never modify a control, equality for zero work extends exactly to all 256 work values and both flag values. It also compares the complex operator of a four-qubit shared-control fragment without global-phase alignment and a 19-qubit state with all key bits in superposition, nonzero work, and flag in superposition. Both maximum amplitude errors are zero. This is a compositional proof plus bounded tests, not a dense full-oracle unitary verification or an independent verification of Qiskit's transpiler.

The prototype was considered viable as a depth tradeoff and checked in an isolated, correctly named Tier 5 submission copy using the unmodified official checker. It returned **full**, SHA-256 match, metrics ok, no flags, one circuit executed; the checker measured 14,652 CX, depth 23,757, total 39,238 and 19 active qubits. One solve took 13.001 seconds; it is not a paired runtime comparison. Safe result: `research/tier05_mask_fusion/checker_result.json`. No full-package Checker or OSC validation was run. The candidate does not achieve the requested CX objective, and this experiment does not change the official scoring configuration or establish competition points.

Reproduce from this branch in the existing compatible virtual environment:

```sh
PYTHONPATH=. python -B -m research.tier05_mask_fusion.experiment
PYTHONPATH=. python -B -m research.tier05_mask_fusion.check_candidate
```

The latter runs the Tier 5 checker and uses a disposable snapshot. To seek a true CX improvement, investigate nonlinear factoring with exact temporary-state restoration, comparator-aware reversible synthesis, and phase-safe relative-phase constructions with rigorous operator proofs. Any candidate must be measured as a complete circuit; depth savings alone do not establish fewer CX or faster simulation.
