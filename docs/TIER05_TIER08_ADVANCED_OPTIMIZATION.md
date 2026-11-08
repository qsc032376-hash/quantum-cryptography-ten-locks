# Tier 5 and Tier 8 advanced circuit optimization

## Baseline, environment, and decision

This branch starts from frozen `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d`. It changes only `submissions/team3/tier05/oracle.py` and `submissions/team3/tier08/solution.py`; the official inputs, helpers, Checker, other tiers, classical recovery, and verified release remain unchanged. The v5 full Checker [record](OPTIMIZED_V5_READINESS.md) reported `full`, SHA-256 match, and no flags for both tiers. Baseline and candidates were independently rerun on the same macOS host with Python 3.13, Qiskit 2.6.1, Aer 0.18.2, official `rz,sx,x,cx` basis, all-to-all coupling, optimization level 1, seed 12345, and no initial layout. The Checker scores the largest circuit actually sent to Aer.

The candidate source SHA-256 values used in the experiments are `99b3aa98b2445faf9e4fe868c09d95dd278b4c5b542fb54065061cb965bed016` for Tier 5 `oracle.py` and `8c377d9f3fa6d4f10190faf15d9889d1bea0fe0b782a1cebafc2bd48f7547abe` for Tier 8 `solution.py`. The single-tier Checker reports do not themselves bind a Git commit; these source hashes and the final branch commit identify the tested implementations.

Earlier, already integrated work reduced Tier 5 from 21,150 two-qubit gates and depth 33,055 to 15,150 and 29,503 by folding public comparison constants through the S-box and permutation. The verified M15 Tier 8 work reduced 49,920 / 135,160 to 42,810 / 123,320 and borrowed MCX6 wires from four to two; see the [independent acceptance](TIER08_INDEPENDENT_ACCEPTANCE.md). The changes below are additional to those v5 results.

| Tier / variant | Two-qubit gates | Depth | Total gates | Active qubits | Checker |
|---|---:|---:|---:|---:|---|
| 5 v5 | 15,150 | 29,503 | 42,211 | 19 | full / hash match / metrics ok / no flags |
| 5 candidate | **14,700** | **28,478** | **41,086** | **19** | full / hash match / metrics ok / no flags |
| 8 v5 | 42,810 | 123,320 | 130,190 | 18 | full / hash match / metrics ok / no flags |
| 8 candidate | **42,792** | **123,300** | **130,171** | **18** | full / hash match / metrics ok / no flags |

Tier 5 saves **450** two-qubit gates, **1,025** depth layers and **1,125** total gates; Tier 8 saves **18**, **20** and **19**, respectively, with no additional active qubits. The sums of these two independent scored circuits change by **468** two-qubit gates, **1,045** summed depth and **1,144** total gates. These are not resources of one joint circuit, and no competition points follow without other teams' metrics. Both changes are **ACCEPT** as single-tier development candidates, subject to integration and a future full-package Checker. Neither is a verified v6 release.

## Tier 5: exact dirty-MCX8 synthesis

The verified v5 Grover oracle already folds the public S-box and bit permutation through the known two-byte comparison. For ciphertext byte $c_i$ and public target byte $b_i$, it compares the reversible key mask against $c_i\oplus RC_i\oplus S^{-1}(P^{-1}(b_i))$. This is public constant propagation, not a key search, and is unchanged here. The circuit still uses 25 Grover iterations, one 128-shot Aer run, the same 10 key qubits, eight scratch qubits, one flag, the same diffuser, and the same measured-key-only classical check.

Only `_dirty_comparison_gate()` changes. Its exact eight-control X on the comparison flag is synthesized by Qiskit's full Maslov M15 dirty-ancilla construction instead of its full Iten I15 construction. On local wires, both implement

$$
|c_0\ldots c_7,t,d\rangle\longmapsto
|c_0\ldots c_7,t\oplus\bigwedge_{j=0}^{7}c_j,d\rangle
$$

with amplitude **+1** on the mapped basis vector, for every value or superposition of borrowed dirty wires $d$. The three M15 borrowed wires are key qubits 0–2; the former I15 template borrowed six key wires. The remaining key wires are identity in both embedded 19-qubit operations. Thus the old and new gates are the *same exact unitary*, not merely the same classical truth table or a relative-phase Toffoli. They restore every borrowed key wire even when it is entangled. Replacing each occurrence inside the compute/mark/uncompute oracle preserves the complete oracle phase and the full Grover iterate $G=DO$ exactly. No marked state or relative phase changes, and the scratch/flag restoration from v5 remains valid. There are three comparison MCX8 occurrences per oracle and 25 identical iterations. The standalone pinned-basis templates have 58 CX (I15) versus 52 CX (M15); $3\times25\times6=450$ matches the measured full-circuit CX saving. The full depth and total-gate savings are **measured compiler results**, not inferred by multiplying standalone values.

The previous diffuser's clean M15 MCX9 remains in place. The eight work wires serve as comparison controls and the key wires are in superposition, so they cannot be relabeled as clean ancillas. A separate clean-M15 MCX8 template has fewer standalone CX gates (42), but requires three *new* clean wires; a full-size run would increase active qubits and statevector memory. We did not claim a full-circuit saving for that untested design. Ancilla-free MCX8 templates were substantially larger in the pinned standalone comparison. Flattening all 25 oracle/diffuser blocks before transpilation produced the **same** 14,700 / 28,478 / 41,086 / 19 metrics as the retained opaque-block layout; the flattened layout also loses the existing explicit outer-Oracle count check, so it was rejected. No iteration count was changed. No additional eligible cross-boundary cancellation was observed after the official level-1 whole-circuit transpilation.

## Tier 8: inverse-QFT input reversal, including dirty wires

The v5 N=35 modular compiler already uses complete M15 dirty MCX6 templates with two borrowed counting wires. It builds the public permutation $x\mapsto ax\bmod35$ for $0\le x<35$, fixes $x\ge35$, decomposes it into disjoint cycles, and implements endpoint transpositions via reversible Gray paths. That compiler and its cycle table remain byte-for-byte unchanged; the outer power blocks are rewired as described below. The new change is confined to the two sides of the inverse-QFT input reversal.

Let $n=12$, let $R$ reverse **all** counting wires, and let $C$ be the original negative-angle inverse-QFT core without its six initial SWAPs. The baseline inverse QFT is $CR$. Write the ordered modular-power block product as $P$, including its borrowed dirty counting wires. The replacement is $P'=RPR$: power $2^j$ uses physical control $q_{n-1-j}$, and every borrowed wire that the original block would use at index $w$ is mapped to $q_{n-1-w}$, in the same order. The work register is untouched. Because the initial phase register is $|+\rangle^{\otimes n}$ and $R|+\rangle^{\otimes n}=|+\rangle^{\otimes n}$,

$$
CRP\bigl(|+\rangle^{\otimes n}|1\rangle\bigr)
=CP'\bigl(|+\rangle^{\otimes n}|1\rangle\bigr).
$$

This is exact final-state equality, including relative phases and the work register, on the specified initialized phase-register domain. It does not assert unrestricted operator equality on arbitrary pre-QFT input. Each M15 block is an exact controlled permutation that restores its two dirty wires for arbitrary, possibly entangled inputs; conjugation by $R$ preserves that guarantee. The full count/work state after the circuit is identical, so the output distribution, `q[j] -> c[j]` mapping, phase sign, 12-bit `c11...c0` integer interpretation, continued-fraction recovery, and classical RSA verification are unchanged. No power is omitted and no factor or order is computed classically as a shortcut.

Implementation pseudocode:

```text
prepare work register |1>; H on all n counting wires
for logical j in 0..n-1:
    multiplier = base^(2^j) mod N       # public gate construction only
    physical_control = n-1-j
    original_dirty = first two counting indices excluding j
    physical_dirty = [n-1-w for w in original_dirty]
    append the unchanged controlled multiplier on
        [physical_control, work wires, physical_dirty]
apply negative-angle inverse-QFT core without input SWAPs
measure physical q[j] into classical c[j]
```

Six initial SWAPs decompose to 18 CX in the official basis, matching the measured Tier 8 saving. The 19-total-gate and 20-depth savings depend on this transpiler. A simpler change that removed SWAPs without relabeling **both** the controls and borrowed wires would not implement $RPR$ and was not used. Adjacent controlled powers have different controls; sharing their multiplication merely because public multipliers repeat would require a separate proof of the joint controlled unitary. No such merger was accepted. The verified M15 modular synthesis was not repeated or altered.

## Equivalence and acceptance evidence

- `tests/test_tier05_tier08_advanced_equivalence.py` passes five synthetic tests. It exhausts all 64 basis inputs for the four-control M15 template, checking +1 amplitude and dirty restoration; checks selected eight-control inputs over nonzero borrowed states; compares old/new Tier 5 full phase-oracle amplitudes for selected keys, nonzero work/flag, and a key superposition; exhausts all 64 basis inputs of a synthetic controlled modulus-15 multiplier, including out-of-range state 15 and dirty values; and compares complete old/new small Shor final state amplitudes for all 16 initial work values plus a complex superposition. The Tier 5 full-size conclusion additionally relies on Qiskit's exact-MCX synthesis contract; the 8-control template was not exhaustively enumerated as a dense 12-qubit operator.
- Real Aer paired-seed evidence is recorded in [Tier 5 baseline](evidence/tier05_tier08_v2/tier05_baseline_seeds.json), [Tier 5 candidate](evidence/tier05_tier08_v2/tier05_candidate_seeds.json), [Tier 8 baseline](evidence/tier05_tier08_v2/tier08_baseline_seeds.json), and [Tier 8 candidate](evidence/tier05_tier08_v2/tier08_candidate_seeds.json). Tier 5 uses the same five seeds 900–904 at 128 shots each and passes **5/5 on both sides**. Tier 8 uses the same ten seeds 800–809 at 64 shots each and passes **10/10 on both sides**. The test runner records only seeds, shots, pass booleans, timings, and process RSS; no key, factor, order, count string, plaintext, or matrix is serialized. Finite seed sets cannot prove zero failure probability.
- Original official Checker runs use isolated, renamed team directories and the unchanged original Checker. Tier 5 [baseline](evidence/tier05_tier08_v2/tier05_baseline_checker.json) and [candidate](evidence/tier05_tier08_v2/tier05_candidate_checker.json) each executed one real 128-shot circuit, returned `full`, matched SHA-256, had valid metrics and `flags=[]`. Tier 8 [baseline](evidence/tier05_tier08_v2/tier08_baseline_checker.json) and [candidate](evidence/tier05_tier08_v2/tier08_candidate_checker.json) each executed one real 64-shot circuit, likewise returned `full`, matched SHA-256, had valid metrics and `flags=[]`. The comparison used the actual v5 Tier 5 Oracle and Tier 8 solution source from the frozen commit, with the same surrounding files.

The paired-seed timings below include the Aer result and the measured-outcome recovery/hash check; build and official-equivalent compilation are separate. An additional run of seed 900 (Tier 5) or 800 (Tier 8) recorded **pure Aer time** and recovery time separately in the corresponding `*_timing.json` evidence files. Durations are seconds; these short, sequential host runs are observations rather than stable speed claims.

| Timing / memory observation | Tier 5 v5 | Tier 5 candidate | Tier 8 v5 | Tier 8 candidate |
|---|---:|---:|---:|---:|
| Paired-seed successes | 5/5 | 5/5 | 10/10 | 10/10 |
| Paired build seconds | 0.052 | 0.004 | 0.065 | 0.038 |
| Paired compile seconds | 0.142 | 0.132 | 0.259 | 0.247 |
| Paired Aer + recovery median seconds | 15.857 | 14.096 | 30.596 | 30.498 |
| Paired Aer + recovery range seconds | 14.000–19.422 | 12.582–14.305 | 27.655–33.875 | 28.649–34.167 |
| Paired process max RSS, bytes | 195,330,048 | 222,937,088 | 419,020,800 | 403,423,232 |
| Repeated seed, pure Aer seconds | 14.675 | 13.066 | 27.838 | 32.363 |
| Repeated seed, recovery seconds | 0.001 | 0.001 | 0.002 | 0.007 |

| Same-host official Checker observation | Tier 5 v5 | Tier 5 candidate | Tier 8 v5 | Tier 8 candidate |
|---|---:|---:|---:|---:|
| solve() seconds | 14.535 | 12.779 | 27.500 | 29.890 |
| Whole Checker wall seconds | 16.62 | 14.26 | 29.68 | 32.11 |
| Process max RSS, bytes | 230,522,880 | 234,668,032 | 414,105,600 | 409,452,544 |

The short Checker timing pairs are noisy and include import, building, compilation, simulation, and scoring work; they do not establish a stable speed or memory advantage. The paired-seed experiment separates compilation from Aer plus recovery, while the repeated single-seed run separates pure Aer from recovery. Different maximum RSS observations in the two experiments also preclude a reliable memory-improvement claim. Aer statevector simulation is not a hardware benchmark or evidence of quantum advantage.

## Integration and remaining opportunities

Integrate only the two changed implementation files after an independent review of this exact commit; retain the current `solution.py`/classical modules for Tier 5 and `modular.py`/`order.py` for Tier 8. Run the full official Checker on an isolated, renamed submission directory before calling any future release verified. The M15 proof depends on an exact (not action-only or relative-phase) implementation and correct dirty-wire ordering. The QFT proof depends on reversing every counting wire used by a modular block, including borrowed wires, and on the initial uniform counting register. Different Qiskit versions, transpiler settings, connectivity, noise, or sampling seeds can change resource or reliability outcomes. Further improvements to Gray-path transpositions or shared controlled predicates remain hypothetical until exact-phase equivalence and full-circuit score are measured.
