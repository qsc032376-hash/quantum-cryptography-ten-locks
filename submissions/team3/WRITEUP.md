# Team 3 — Quantum Cryptography Challenge Write-up

**Members:** Sicheng Qian, Junqi Sheng, Youyang Shang, Junrui Yu
**Attempted tiers:** 1–10
**Verified source:** `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d`

## Executive summary

We solved all ten locks with quantum circuits executed on Qiskit Aer, measurement-driven classical recovery, and cryptographic verification. In a renamed team directory, the unchanged official Checker recorded a circuit for every tier, returned `full` in all ten cases, matched every plaintext SHA-256 hash, produced valid metrics, and raised no flags. The verification is documented in the [v5 integration report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/41c7c6775b8fc499c2acdd878b4829bd17e1210d/docs/OPTIMIZED_V5_READINESS.md) and its [Checker JSON](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/41c7c6775b8fc499c2acdd878b4829bd17e1210d/docs/evidence/v5/report.json). We have not uploaded a submission or established a competition score.

The computational chain is **public challenge → quantum circuit → measurement → classical recovery → decryption and hash verification**. Quantum interference exposes a hidden string, period, phase, marked key, or relation. Classical algorithms interpret the resulting samples and verify candidates. The small challenge parameters make the methods demonstrable; they do not make this a scalable cryptanalytic implementation or a claim of quantum hardware advantage.

## Reading the evidence and resource tables

The [official template](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/41c7c6775b8fc499c2acdd878b4829bd17e1210d/submissions/TEAM_TEMPLATE/WRITEUP.md) requests, for each tier, shots and executions, Oracle use, measured outcomes with frequencies, scored resources, and classical work. Each tier below reports those categories. **The published v5 Checker JSON stores aggregate status and resource metrics, not secret-bearing raw outcome strings or their exact frequency tables. We do not invent or disclose those observations.** The method of interpreting each observed string is specified below; a private measurement ledger would be needed to supply actual per-outcome frequencies to judges. The existing `solve()` paths retain measurement-derived evidence in memory and verify it before returning. The official Checker establishes a circuit execution and matching output hash, but it does not itself certify every intermediate measurement frequency or a hardware success rate.

Circuit sketches use chronological arrows and name the logical operations. The four metrics in each table are the official selected Aer-input circuit after the fixed `rz,sx,x,cx` scoring transpilation, with all-to-all connectivity, optimization level 1, and seed 12345. If multiple circuits execute, the Checker selects the one with the most two-qubit gates, breaking ties by depth. Measurements, resets and barriers do not count as gates. Shots, logical Oracle applications, and classical work are separate costs. No measured qubit is reset and reused as feedback in the selected v5 designs.

## Tier 1: The Parity Vault

### What the file hid, and how we identified the approach
A repeating-XOR mask is determined by a hidden 24-bit parity string. The supplied Boolean Oracle has the Bernstein–Vazirani form `f_s(x)=s·x (mod 2)`.

### Why the approach works
Preparing a uniform input and a phase-kickback target gives phase `(-1)^(s·x)` on each input x. Hadamards on the inputs interfere to return s in the ideal model. The measured 24-bit string is used as the fixed-width XOR key; the plaintext hash checks the result. The supplied Oracle remains opaque.

### Circuit diagram with qubit and gate counts
`|0⟩^24 — H^24 — U_f — H^24 — measure` with one target prepared for kickback. The selected 25-qubit circuit has 151 two-qubit gates, depth 44, and 298 total gates after official scoring transpilation.

### Measurement result and key extraction
One 24-bit measurement maps input qubit j to classical bit j; no string reversal or classical key search is needed. The actual key-bearing string and frequency were not archived in the shareable v5 report.

### Classical cost for comparison
Parsing one fixed-width string and applying repeating XOR is linear in message length. Constructing a candidate by exhaustive search over 24 bits would take up to `2^24` parity candidates in this toy model.

| Item | Our result |
|---|---|
| Shots / executions | 1 shot, one Aer circuit. |
| Oracle applications | One opaque Oracle application per shot; one total. |
| Outcomes / frequencies | One key-bearing 24-bit outcome in the run; raw value withheld, frequency 1/1. |
| Scored metrics | 151 two-qubit; depth 44; total 298; active 25. |
| Classical work | Fixed-width parsing, repeating XOR, SHA-256 verification; no key lookup table. |

## Tier 2: Two Links

### What the file hid, and how we identified the approach
The key is carried through two quantum links, one disturbed by the challenge's intercept–resend process. BB84 basis matching and the published check positions make channel comparison possible.

### Why the approach works
When Alice's and Bob's bases match, an ideal clean link preserves their bit; a random intercept–resend basis causes a 25% sifted error rate in expectation. Bob chooses bases before disclosure, measures each received qubit once, estimates QBER only on matched public check positions, selects the lower-error link, and reconciles the remaining sifted bits. This is a finite-sample channel decision, not a general BB84 security proof.

### Circuit diagram with qubit and gate counts
For each received qubit: `incoming state — [H for X basis] — measure`. The selected one-qubit measurement circuit has zero two-qubit gates, depth 3, and 3 total gates; the Channel log recorded 2,048 measurements across the links.

### Measurement result and key extraction
The actual bit outcomes and check-position frequencies are private. In the recorded run, the measured sequence passed public reconciliation and led to a hash match. Each position is used once; the public check bits are excluded from key material.

### Classical cost for comparison
Basis sifting, error counting and reconciliation are linear or near-linear in the number of received bits. A classical simulation of this small link does not establish secure key distribution under realistic attacks.

| Item | Our result |
|---|---|
| Shots / executions | One measurement per received qubit; 2,048 Channel-recorded measurement circuits. |
| Oracle applications | Not applicable; the Channel prepares and delivers the states. |
| Outcomes / frequencies | One bit per position; private sequence and empirical QBER counts are not in the public Checker JSON. |
| Scored metrics | 0 two-qubit; depth 3; total 3; active 1. |
| Classical work | Basis comparison, public-check QBER, link choice, reconciliation, XOR decryption and hash. |

## Tier 3: Twenty-Four Seals

### What the file hid, and how we identified the approach
Twenty-four supplied Oracles are promised constant or balanced. Their classifications form the key; this is Deutsch–Jozsa's promise setting.

### Why the approach works
With the target in `|−⟩`, the post-Hadamard zero-input amplitude is `2^-6 Σ_x (-1)^f(x)`. Its magnitude is one for a constant function and zero for a balanced one. One Oracle application per classification therefore suffices ideally. The 24 measured decisions are assembled in Oracle order before decryption.

### Circuit diagram with qubit and gate counts
Each circuit has six input qubits and one target: `H^6 — U_f — H^6 — measure inputs`. The Checker selected the largest of 24 executed circuits: 7,808 two-qubit gates, depth 8,771, 19,497 total gates, and 7 active qubits.

### Measurement result and key extraction
One measurement was taken per Oracle, giving 24 classification bits. Actual classifications are not published; their ordered encoding and the recovered plaintext passed the hash check.

### Classical cost for comparison
A deterministic classical black-box promise test can require exponentially many queries in the six-bit input width, though this toy width is tiny. Postprocessing 24 bits and decrypting is inexpensive.

| Item | Our result |
|---|---|
| Shots / executions | 1 shot per Oracle circuit; 24 circuits. |
| Oracle applications | 1 per circuit, 24 across the experiment. |
| Outcomes / frequencies | One zero/nonzero classification outcome per Oracle; private 24-bit sequence withheld. |
| Scored metrics | 7,808 two-qubit; depth 8,771; total 19,497; active 7. |
| Classical work | Promise classification, fixed-order bit packing, keystream XOR and SHA-256. |

## Tier 4: The Echo

### What the file hid, and how we identified the approach
The supplied two-to-one function hides a nonzero XOR period s: `f(x)=f(x⊕s)`. This is Simon's problem.

### Why the approach works
Interference suppresses all measurement strings y for which `y·s=1 (mod 2)`. The solver gathers rows satisfying `y·s=0`, solves the nullspace over `F₂`, and accepts a unique nonzero candidate when the rank reaches nine. The period is then encoded as the key and checked through decryption.

### Circuit diagram with qubit and gate counts
Ten input and ten output qubits: `H^10 — U_f — H^10 — measure input`. One Oracle block is used per shot. The selected circuit scores 183 two-qubit gates, depth 195, 455 total gates, and 20 active qubits.

### Measurement result and key extraction
The private measured y rows and frequencies were not saved in the public Checker JSON. The circuit samples in batches of 32 up to 128 shots; the actual run reached a valid nullspace and hash match. The output register is not interpreted as a secret key.

### Classical cost for comparison
Gaussian elimination over ten-bit rows is small. Classical birthday-style collision search has a different query scaling from Simon sampling, though here the problem size is intentionally modest.

| Item | Our result |
|---|---|
| Shots / executions | 32-shot batches, at most 128 shots; v5 Checker records one unique circuit, but not the run's batch count. |
| Oracle applications | 1 per shot; total equals the unarchived shot count. |
| Outcomes / frequencies | Ten-bit orthogonality rows; private rows and histogram unavailable from public evidence. |
| Scored metrics | 183 two-qubit; depth 195; total 455; active 20. |
| Classical work | `F₂` row reduction, nullspace verification, fixed-width key encoding, keystream and hash. |

## Tier 5: The Small Safe

### What the file hid, and how we identified the approach
A ten-bit toy-cipher key is uniquely marked by the first two decrypted bytes matching the public `QC` condition. A reversible Grover phase oracle searches this marked predicate.

### Why the approach works
With `sin²θ=1/1024`, 25 Grover iterations rotate amplitude toward the marked key. The v5 Oracle folds public S-box and permutation inverses into two public comparison constants. For key k and clean work/flag, the original and optimized circuits both implement `|k,0,0⟩ → (-1)^(e₀(k)e₁(k))|k,0,0⟩`. The key-dependent mask remains reversible and is uncomputed; the diffuser is unchanged. Exact borrowed-bit synthesis preserves coherent phases. The resulting measured candidate is decrypted and verified.

### Circuit diagram with qubit and gate counts
`H^10 — [phase Oracle → diffuser]^25 — measure key`, using eight byte-work qubits and one flag. The selected 19-qubit circuit has 15,150 two-qubit gates, depth 29,503 and 42,211 total gates, down from 21,150 two-qubit gates in v1.

### Measurement result and key extraction
The solver measures 128 candidate keys and requires a valid measured candidate; the actual key histogram is not published. A passing candidate is encoded at the exact ten-bit width, used for toy-cipher decryption, and checked by prefix and hash.

### Classical cost for comparison
Public constant inversion and circuit construction are preprocessing; candidate decryption is linear in ciphertext length. Grover's `O(√N)` black-box query scaling does not mean its reversible Oracle is free, and classical search is trivial at `N=1024`.

| Item | Our result |
|---|---|
| Shots / executions | 128 shots in one circuit. |
| Oracle applications | 25 phase-Oracle calls per shot; 3,200 shot-weighted applications. |
| Outcomes / frequencies | Measured key candidates; private histogram not archived publicly. |
| Scored metrics | 15,150 two-qubit; depth 29,503; total 42,211; active 19. |
| Classical work | Public inverse constants, candidate toy-cipher decryption, prefix and SHA-256. |

## Tier 6: The Bigger Safe

### What the file hid, and how we identified the approach
This 14-bit search has many keys matching the first-byte `Q` predicate. A public checksum selects the intended key after measurement; it is not added to the quantum Oracle.

### Why the approach works
For `M` marked keys among `N=2^14`, Grover amplification gives marked-subspace probability `sin²((2r+1)arcsin√(M/N))`. The solver uses quantum calibration and bounded search, then checks only measured candidates with the toy cipher and checksum. A high marked-subspace probability does not imply a single-shot hit on the unique checksum-valid key.

### Circuit diagram with qubit and gate counts
Calibration and search circuits each contain the appropriate reversible first-byte phase check. The selected search circuit scores 3,000 two-qubit gates, depth 5,883, 9,534 total gates and 22 active qubits; the calibration circuit is separately recorded.

### Measurement result and key extraction
The public v5 Checker report records two circuits but does not publish their histograms. The verified recovery used measured candidates and the public checksum before hash verification; the precise candidate frequencies are private.

### Classical cost for comparison
Estimating the marked population and deduplicating measured keys add classical work. Classical enumeration over `2^14` toy keys is cheap in absolute terms, so the point is the quantum search method and its explicit Oracle cost.

| Item | Our result |
|---|---|
| Shots / executions | 2,048 calibration shots; search uses bounded batches (v1 integration recorded 640 shots); v5 Checker records two circuits but no exact search-shot count. |
| Oracle applications | One phase Oracle per Grover iteration; total depends on measured calibration and selected search iterations. |
| Outcomes / frequencies | Calibration and search histograms are private; checksum-valid candidate is measurement-derived. |
| Scored metrics | 3,000 two-qubit; depth 5,883; total 9,534; active 22. |
| Classical work | Marked-count estimate, deduplication, toy-cipher checksum, full decryption and hash. |

## Tier 7: The Hidden Angle

### What the file hid, and how we identified the approach
A one-qubit unitary carries a phase corresponding to a 14-bit integer. Quantum phase estimation reads it without computing the unitary's hidden eigenphase classically.

### Why the approach works
For `U|u⟩=e^(2πiφ)|u⟩`, the controlled powers `U^(2^j)` imprint binary phase information. A complete inverse QFT concentrates the readout at the encoded phase. A second phase-cancellation circuit checks the measured candidate; the full controlled global phase is retained.

### Circuit diagram with qubit and gate counts
`H^14 — controlled powers — inverse QFT — measure`, with one target qubit and a separate check circuit. The larger scored circuit has 230 two-qubit gates, depth 271, 763 total gates and 15 active qubits.

### Measurement result and key extraction
The QPE circuit maps `q_j→c_j` for a direct 14-bit integer interpretation; no bit reversal is applied. The measured integer and its private frequency are not published. The check circuit used 32 verification shots in addition to 64 QPE shots.

### Classical cost for comparison
Public matrix powers are generated by repeated squaring without extracting the hidden eigenvalue. Integer parsing and keystream decryption are small at this size.

| Item | Our result |
|---|---|
| Shots / executions | 64 QPE shots plus 32 phase-check shots; two Aer circuits. |
| Oracle applications | 14 controlled-power blocks per circuit; 28 physical blocks across the two circuits (not 28 separate black-box queries per shot). |
| Outcomes / frequencies | QPE phase string and zero-check counts; private phase value not archived in public evidence. |
| Scored metrics | 230 two-qubit; depth 271; total 763; active 15. |
| Classical work | Repeated public matrix squaring, measured phase validation, 14-bit encoding and hash. |

## Tier 8: The Wrapped Key, N = 35

### What the file hid, and how we identified the approach
An RSA-wrapped key requires factoring `N=35`. Shor order finding uses quantum phase sampling of public modular multiplication instead of classical trial division.

### Why the approach works
For coprime public a, controlled powers act as `|x⟩|1⟩ → |x⟩|a^x mod 35⟩`. Measured Fourier peaks yield candidates for `ord₃₅(a)`; continued fractions, order minimality checks and nontrivial half-order gcds recover factors when the selected base permits it. RSA decryption and key-width encoding follow classically. The v5 M15 synthesis exactly replaces local controlled-X templates, borrowing two rather than four dirty wires for six controls. Internal relative phases cancel, all borrowed values and phases return, and padding labels and the counting-register mapping are preserved.

### Circuit diagram with qubit and gate counts
`H^12 — 12 controlled modular powers — inverse QFT — measure`, with six work qubits. The selected circuit scores 42,810 two-qubit gates, depth 123,320, 130,190 total gates and 18 active qubits. The v4 figures were 49,920, 135,160 and 148,085 at the same width.

### Measurement result and key extraction
The actual 12-bit counts histogram and private factor witness are not published. The run used 64 shots in one batch; continued-fraction candidates were checked for exact order and nontrivial factors before RSA unwrapping and SHA-256 verification.

### Classical cost for comparison
The public small-modulus permutation table is exponentially sized in work width, so this compiler is a toy implementation, not scalable arithmetic. Continued fractions and gcds are efficient once measurement evidence is available. Ten paired seeds passed in independent acceptance; that finite set is not a universal success bound.

| Item | Our result |
|---|---|
| Shots / executions | 64 shots in one Aer batch for the recorded integration; one circuit recorded. |
| Oracle applications | 12 controlled modular-power blocks per shot; 768 shot-weighted block applications. |
| Outcomes / frequencies | 12-bit order-finding samples; raw histogram and factor witness private. |
| Scored metrics | 42,810 two-qubit; depth 123,320; total 130,190; active 18. |
| Classical work | Public permutation synthesis, continued fractions, order checks, gcd, RSA and hash. |

## Tier 9: The Wrapped Key, N = 77

### What the file hid, and how we identified the approach
The second RSA-wrapped key uses `N=77` and a larger modular-multiplication circuit. The same Shor order-finding structure applies.

### Why the approach works
Fourteen phase bits control public modular powers on seven work bits. From measured phase estimates, continued fractions suggest an order; minimality and `a^r=1 mod 77` checks precede half-order gcds and RSA unwrapping. The v5 exact shared-predicate synthesis groups consecutive flips with identical controls. A pivot fanout, one controlled pivot flip and inverse fanout reproduce their full permutation with phase +1 on every basis column. No extra ancilla is used, and no hidden period is inferred from permutation cycles.

### Circuit diagram with qubit and gate counts
`H^14 — 14 controlled modular powers — inverse QFT — measure`, with seven work qubits. The selected circuit has 89,075 two-qubit gates, depth 235,048, 263,601 total gates and 21 active qubits, down from 117,739 two-qubit gates in v1.

### Measurement result and key extraction
The actual 14-bit histogram, order and factors are private. One 64-shot batch supplied the recorded evidence; the algorithm has a bounded second batch if necessary. Key material is obtained only after checked order and gcd recovery.

### Classical cost for comparison
Compilation enumerates the public small permutation table and does not scale as general modular arithmetic. Continued fractions and gcds are efficient; factoring the tiny public modulus classically would be trivial but is not the submitted recovery method.

| Item | Our result |
|---|---|
| Shots / executions | 64 shots in the recorded batch; one circuit recorded. |
| Oracle applications | 14 controlled modular-power blocks per shot; 896 shot-weighted blocks. |
| Outcomes / frequencies | 14-bit phase samples; private histogram and factors not archived publicly. |
| Scored metrics | 89,075 two-qubit; depth 235,048; total 263,601; active 21. |
| Classical work | Public permutation synthesis, continued fractions, order validation, gcd, RSA and hash. |

## Tier 10: The Handshake

### What the file hid, and how we identified the approach
A public Diffie–Hellman value `A=g^a mod p` hides one exponent a in an order-41 subgroup. The two-register discrete-log Fourier method studies `f(x,z)=g^x A^z mod p`.

### Why the approach works
Equal function values satisfy `Δx+aΔz=0 mod 41`. Two inverse QFTs sample approximate frequencies `(u,v)` whose ideal relation is `u a=v mod 41`. Six-bit binary readouts are rounded to group frequencies; off-peak equations can be wrong, so every measurement-derived candidate is checked by `g^a=A` before computing the shared secret `B^a`. The v5 circuit uses exact ancilla-free modular fanout and absorbs both QFT swap networks by consistently reversing control wiring. The uniform count preparation is invariant under that reversal, preserving the complete output state and the `z5…z0 x5…x0` readout layout.

### Circuit diagram with qubit and gate counts
`H^6_X H^6_Z — 12 controlled public modular powers — two inverse QFT bodies — measure X,Z`, with seven work qubits. The selected circuit has 82,804 two-qubit gates, depth 218,263, 245,153 total gates and 19 active qubits; the v1 two-qubit count was 107,168.

### Measurement result and key extraction
The run recorded one 128-shot circuit, but the full 12-bit counts table and exponent witness are private. The left six characters are Z, the right six X. Integer half-up rounding and the pair `(-v mod 41,u)` feed the classical congruence solver; a verified exponent determines the shared integer, then decryption and hash verification follow.

### Classical cost for comparison
Public modular powers and permutation synthesis are small here but exponential-table construction is not scalable. The candidate check is one public exponentiation for each measurement-derived candidate, not enumeration of the hidden exponent space.

| Item | Our result |
|---|---|
| Shots / executions | 128 shots in one recorded Aer circuit. |
| Oracle applications | 12 controlled public modular-power blocks per shot; 1,536 shot-weighted blocks. |
| Outcomes / frequencies | Paired 6-bit samples; raw counts and private exponent witness not archived publicly. |
| Scored metrics | 82,804 two-qubit; depth 218,263; total 245,153; active 19. |
| Classical work | Public powers and permutation compiler, finite-grid rounding, congruence and public-relation checks, DH, keystream and hash. |

## Circuit optimization and experimental results

| Tier | v1 two-qubit gates | Verified v5 | Change | Exactness condition |
|---|---:|---:|---:|---|
| 5 | 21,150 | 15,150 | −6,000 | Same two-byte predicate and phase on zero-initialized work/flag; full uncomputation. |
| 8 | 49,920 | 42,810 | −7,110 | Exact M15 MCX, arbitrary borrowed state restored including phase. |
| 9 | 117,739 | 89,075 | −28,664 | Exact pivot fanout for equal-control adjacent flips, no ancilla. |
| 10 | 107,168 | 82,804 | −24,364 | Exact fanout plus QFT control relabeling on uniform count preparation, unchanged readout. |

Across the ten separately selected scoring circuits, v5 sums to **241,211 two-qubit gates**, **621,301 in per-tier depths**, and **711,705 total gates**. Historical v1 sums to 307,349 two-qubit gates and 787,876 in per-tier depths: reductions of **21.52%** and **21.14%**. These sums are arithmetic summaries of independent scored circuits, not one circuit's depth, gate count or simultaneous qubit requirement. The v1 and v5 reports were recorded on different hosts; per-tier paired experiments and the v5 full-package run support the implemented changes, but cross-host timings should not be compared as speedups. The [mathematical analysis](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/1e859a26e572b9ce6eb4ee1d2dea560cf2943e9f/docs/FINAL_QUANTUM_ANALYSIS.md) distinguishes proof, synthetic tests and Checker acceptance.

## Scaling

At toy sizes, classical brute force can be faster than constructing or simulating these circuits. In the black-box model, Bernstein–Vazirani, Deutsch–Jozsa and Simon exploit their respective promises, Grover changes unstructured search from `Θ(N)` to `Θ(√N)` Oracle queries at fixed success probability, and Shor's order and discrete-log methods use periodicity and Fourier sampling. A logical query can be a deep reversible circuit; query scaling alone omits modular arithmetic, error correction, repeated shots and compilation. The public permutation-table compilers used for small moduli have exponential construction cost in work-register width. A scalable cryptographic attack would need arithmetic circuits for large integers, substantially deeper fault-tolerant operations and far more physical qubits than shown here. No such large-key implementation or hardware resource estimate was validated.

## Hardware or noise

The reported runs used ideal Qiskit Aer, not a physical device. Real gates have errors, decoherence, connectivity limits, reset/measurement imperfections and calibration drift; the deep controlled arithmetic and Fourier circuits would be especially vulnerable. Finite shots can miss a marked key, fail to reach Simon rank nine, yield an unusable order or produce off-peak discrete-log equations. Ten paired Tier 8 seeds passed, but ten successes cannot prove zero failure probability. The same-machine Tier 10 optimization lowered scored gates while increasing measured solve time, illustrating that Aer native-gate simulation, compilation and memory differ from the official fixed-basis score. The [official scoring rules](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/41c7c6775b8fc499c2acdd878b4829bd17e1210d/SCORING.md) compare eligible teams relative to one another; this work does not claim an unverified point total or practical quantum advantage.

## Team contributions

| Member | Contribution |
|---|---|
| Sicheng Qian | Mathematical modeling, optimization proofs, resource interpretation and scientific presentation. |
| Junqi Sheng | Quantum circuit engineering, Qiskit synthesis and circuit optimization. |
| Youyang Shang | Classical cryptography, key recovery interfaces and software development. |
| Junrui Yu | Integration, independent testing, benchmarking and official Checker validation. |

## Submission evidence boundary

This write-up is formatted for `submissions/team3/WRITEUP.md` and linked from the same folder's README. It must be packaged beside the exact verified v5 solution modules in the final team folder; the documentation branch alone has no `solution.py` files under `submissions/team3/`. The published v5 reports omit raw secret-bearing readouts. Before private competition submission, the team should append a confidential readout appendix with observed outcomes, frequencies, retry counts and how each key was extracted, as requested by the official template. That step must use actual logged evidence, not reconstructed or synthetic values. No competition upload has been performed by this documentation change.
