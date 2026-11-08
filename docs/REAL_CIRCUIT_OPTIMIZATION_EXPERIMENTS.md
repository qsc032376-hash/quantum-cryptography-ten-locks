# Research toolkit on real circuit construction

This research branch begins at the unchanged toolkit commit `f9c66be4cbb64568292a6c809a7ac1b3ed0abf02`. It imports its existing GF(2), QFT, MCX and commutation modules without editing them. The original 12 toolkit tests pass. Source candidates are Tier 5/8 `optimization/tier05-tier08-v2@0988ac44d88d08cc12258f2010afaf792dd53e7b` and Tier 7 `optimization/tier01-tier04-tier07@7aef6e714dbbc8d222ef168b4bd691078f823b6e`. Frozen v5 `41c7c6775b8fc499c2acdd878b4829bd17e1210d` remains the verified fallback. The experiment reads team-owned construction code and public ciphertext/parameters; it does not inspect protected Oracle definitions, hidden answers, or other developers' production branches.

## Decision and full-circuit evidence

The only new full scoring improvement is in Tier 5. Each official result below came from the **unchanged** `tools/check_submission.py` on an isolated, renamed, disposable team directory containing only the Tier 5 entry point. All three executed one real 128-shot Aer circuit and returned `full`, SHA-256 match, valid metrics and `flags=[]`. Production source files are not changed on this branch.

| Tier 5 circuit | 2Q gates | Depth | Total gates | Active qubits | Decision |
|---|---:|---:|---:|---:|---|
| Latest candidate `0988ac4` | 14,700 | 28,478 | 41,086 | 19 | Reference |
| GF(2) on compiled native CNOT windows | **14,552** | **28,132** | **40,938** | **19** | **ACCEPT, research candidate** |
| Two-clean MCX9 diffuser and GF(2) | **14,552** | **27,282** | 41,088 | 19 | **ACCEPT for depth, with total-gate tradeoff** |

GF(2) alone saves 148 two-qubit gates, 346 depth layers and 148 total gates against the **latest** Tier 5 candidate. The combined candidate saves the same 148 two-qubit gates and 1,196 depth layers, but adds two total gates against that reference (150 more than GF(2) alone). Active qubits stay 19. These are official single-tier scored-circuit measurements, not a new full-package result or a competition point estimate. Evidence: [baseline](../research/real_circuits/results/baseline_official/report.json), [GF(2)](../research/real_circuits/results/gf2_official/report.json), [combined](../research/real_circuits/results/combined_official/report.json).

## Exact Tier 5 transformations

The eligible object is the team-owned 19-qubit Grover circuit after its normal Qiskit/Aer basis compilation in `solve()`. The original 25 phase-oracle/diffuser iterations, public marked-key predicate, work/flag preparation, and final `q[j] -> c[j]` key measurement remain as constructed. [`experiments.py`](../research/real_circuits/experiments.py) finds maximal **consecutive** positive-control CX runs in that compiled circuit. It does not cross H, SX, RZ, X, MCX, measurement or any opaque operation. Each run defines a little-endian binary linear map $y=Mx$ on its touched wires. The existing toolkit's Gauss–Jordan synthesis returns the same matrix and carries the original global phase. Because CNOT is a +1 basis permutation, equal $M$ means equal quantum operator on all basis states, superpositions, entanglement with the untouched wires, and relative phases. Every non-CX operation stays in the same order on the same arguments. No ancilla assumption is needed for this rewrite.

A concrete three-wire window from the actual compiled circuit is `CX(0,1); CX(0,2); CX(1,2)`. Its matrix, with bit $j$ on wire $j$, is

$$
M=\begin{pmatrix}1&0&0\\1&1&0\\0&1&1\end{pmatrix}.
$$

`CX(1,2); CX(0,1)` realizes exactly the same map, including the cancellation of the two paths from input 0 to output 2. Across the full circuit, **248** windows were accepted, removing **148** CX; the widest touched five wires. The [focused evidence](../research/real_circuits/results/equivalence.json) checks all columns of the complete complex operator for **every** replaced window (each at most five qubits), with maximum error zero. It also verifies unchanged non-CX sequence, global phase and all ten measurement wire/bit pairs. The proof applies compositionally to the full circuit; a dense 19-qubit operator was not constructed. Recompilation under the official basis confirms the scored figures above. Source-level GF(2) on the uncompiled top-level circuit found no change because Grover blocks are wrapped gates; expansion is restricted to team-owned compiled operations.

The second candidate changes only the *disposable* Tier 5 diffuser's exact clean MCX9 template: the existing M15 version uses four clean work wires, while KG24 uses two. For all $2^{10}=1,024$ control/target basis columns with the two auxiliaries initialized zero, the proposed template gives the exact positive MCX action with +1 amplitude and restores both auxiliaries; the largest complex error was $5.34\times10^{-15}$. By linearity this verifies the entire zero-auxiliary subspace, including control superpositions and external entanglement. The original phase oracle restores the eight work wires before each diffuser, so the two selected wires meet that clean-state precondition. The other work and flag wires and the diffuser's global phase are untouched. The combined GF(2) pass separately checks another 248 complete small operators with zero error. It retains the same 25 Grover iterations and measured-key-only classical recovery. This is a scoped clean-ancilla equivalence, not an assertion of equality on arbitrary dirty-ancilla inputs.

## Screening of Tier 5, Tier 8, and Tier 7

The [scout results](../research/real_circuits/results/scout.json) use the same official-equivalent static compilation twice: first to match the executed native circuit, then to match the Checker's scoring pass. They are screening measurements, not Checker results. The tables below retain the four score metrics; the JSON also records separate compilation and research-pass times.

| Real accessible circuit | Technique and result | Classification |
|---|---|---|
| Tier 5 byte-mask transforms, both public byte indices | Consecutive-CX GF(2), source/native commutation: 64 2Q / depth 120 / total 160 for each before and after | REJECT: no gain |
| Tier 5 phase Oracle alone | Compiled GF(2): 540 → 536 2Q, depth 1,025 → 1,015, total 1,428 → 1,424 | Useful local evidence; full-circuit comparison above controls the decision |
| Tier 5 full Grover | Source GF(2) and source/native inverse cancellation: no gain. Compiled GF(2): 14,700 → 14,552 2Q, depth 28,478 → 28,132 | ACCEPT with official Checker above |
| Tier 5 diffuser MCX9 | Under the existing four-clean-wire budget, two-clean KG24 has 48 2Q and depth 80 versus M15's 48 and 114; full circuit using KG24 alone gives 14,700 / 27,628 / 41,236 / 19 | REJECT as a standalone option: combined candidate has the same qubits and lower 2Q, depth and total |
| Tier 8 controlled multipliers for all four distinct public powers | Source commutation removes 528–746 native source operations depending on the multiplier, but the official-equivalent two-qubit counts, depths and total gates are **unchanged** after recompilation; GF(2) yields no change | REJECT: compiler already captures these cancellations |
| Tier 8 full N=35 circuit | 42,792 / 123,300 / 130,171 / 18 before and after all eligible toolkit passes | REJECT: no new gain beyond `0988ac4` |
| Tier 7 optimized inverse-QFT core | 182 / 105 / 497 / 14 before and after; no explicit input reversal remains for the toolkit detector | REJECT: existing QFT wire optimization is already applied |

The [MCX budget screen](../research/real_circuits/results/mcx_screen.json) compares actual control widths under the fixed available workspace. Tier 5's current exact dirty MCX8 is 52 CX; one- and two-borrowed KG24 alternatives each need 78 CX, so no full Grover run was justified. Tier 8's exact dirty MCX6 is 36 CX; those alternatives need 54 CX. Tier 5's diffuser M15 and two-clean KG24 each need 48 CX; the depth reduction motivated the combined full test. The QFT detector correctly found that Tier 7 and Tier 8 latest candidates have already absorbed their input SWAPs. No new QFT rewrite was attempted. Other restricted Helpers and Tier 9/10 production code were not transformed.

## Compilation, Aer, and limits

The [profile file](../research/real_circuits/results/profiles.json) records a **separate** real 128-shot Aer solve for each Tier 5 variant with simulator seed 2026. It times the normal solve compilation, the research GF(2) pass, and Aer submission through `result()` separately. All three profile solves returned the correct official hash; no keys, counts, or plaintext are logged. The official Checker runs above use the original solve behavior and its own seed handling. The profiling numbers are one-run observations on macOS, Python 3.13, Qiskit 2.6.1/Aer 0.18.2; they do not establish a speed advantage.

| Variant | Official solve s | Profile compile s | GF(2) pass s | Profile Aer s | Profile solve s |
|---|---:|---:|---:|---:|---:|
| Latest candidate | 13.810 | 0.091 | — | 13.158 | 13.258 |
| GF(2) | 16.759 | 0.059 | 0.912 | 14.084 | 15.069 |
| Combined | 13.390 | 0.053 | 0.888 | 13.384 | 14.339 |

The GF(2) pass adds roughly 0.9 seconds of classical preparation on this host. It lowers the scored gates but need not make statevector simulation faster. The three official runs and three seeded profiles are a bounded correctness check, not a cross-seed failure-rate estimate. The prior independent benchmark protocol requires at least ten actual paired seeds and rules review for adoption; this **research ACCEPT** does not certify that gate. Aer ideal-statevector metrics do not establish noisy-hardware performance.

## Reproduction and integration conditions

Run from this branch with the pinned environment:

```bash
python -m unittest research.circuit_optimizer.equivalence_tests -v
python -m research.real_circuits.experiments
python -m research.real_circuits.verify
python -m research.real_circuits.screen_mcx
python -m research.real_circuits.validate_candidates
```

The first command is the original toolkit's 12 tests; the latter commands rebuild disposable snapshots and safe aggregate JSON under `research/real_circuits/results/`. Only `validate_candidates` invokes the original single-tier Checker. For a future Tier 5 integration, insert the GF(2) rewrite **after** the solver's existing basis transpilation and before its Aer run, retain the ten-bit measurement and 25 Oracle calls, and verify the *actual* recorded scoring circuit. The combined template additionally requires proof that the work wires are initialized zero at each diffuser and restored afterward. An independent ten-seed paired run, resource limits, and full-package Checker would be required before promoting either research candidate into a verified release. No production implementation or final submission ZIP was modified here.
