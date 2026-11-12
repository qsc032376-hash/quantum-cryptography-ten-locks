# Quantum Cryptography: Ten Locks, One Message — Team 3 Write-up (v6.3.1 documentation edition)

**Sicheng Qian, Junqi Sheng, Youyang Shang, Junrui Yu**

The Ohio State University · Qiskit Fall Fest 2026

## Abstract

We solve ten encrypted-file challenges with Bernstein–Vazirani, BB84,
Deutsch–Jozsa, Simon, Grover search, multi-target Grover, quantum phase estimation,
Shor order finding and quantum discrete logarithms. Each `solve()` executes a Qiskit
Aer circuit and derives its key from measured outcomes; classical routines then decrypt
the file and the official Checker verifies its SHA-256.

The approved v6.3 Candidate A package passes the unchanged official Checker **10/10 FULL**, with
all ten hashes matching, actual Aer execution in every tier, no flags and no timeouts.
Its ten selected scoring circuits total **103,166 two-qubit gates**, **217,625** summed
depth and **294,982** total gates. These are ideal-simulator, all-to-all metrics, not a
hardware speedup claim.

## How the evidence should be read

The Checker records every circuit sent to Aer during `solve()`, transpiles each with the
official configuration (`rz, sx, x, cx`, all-to-all, optimization level 1, seed 12345)
and scores the circuit with the most two-qubit gates, breaking ties by depth. It hashes
the returned plaintext; a hash match verifies the answer, not the recovery method.
Accordingly, each section below states what was hidden, why the algorithm applies, what
the executed circuit computes, which measured outcomes become the key, and what the
classical cost is. `build_circuit()` is a diagram interface and is never scored.

## Tier 1: The Parity Vault — Bernstein–Vazirani

**What was hidden.** A 24-bit XOR mask behind a parity oracle. **Why it works.** Phase
kickback turns each oracle inner product into a phase; a final Hadamard layer maps the
phase pattern to the mask. **Circuit and extraction.** `|0>^24 — H — [parity oracle] —
H — measure`, with a `|1> — H` target supplying |−⟩. One shot, one oracle call; the
measured 24 bits are the key, converted with the recorded bit order. **Classical cost.**
A black-box classical search needs up to 24 independent bit queries; here the oracle is
supplied and the instance is small. **Scored resources.** 151 two-qubit gates, depth 44,
298 total gates, 25 active qubits.

## Tier 2: Two Links — BB84

**What was hidden.** Which of two intercepted links is clean, and the key carried by
that link. **Why it works.** Measuring in Alice's basis preserves an ideal BB84 bit;
intercept–resend introduces errors in matching-basis check bits. **Circuit and
extraction.** Bob applies identity or H according to his chosen basis and measures each
received qubit. The two 1,024-qubit links are measured once each; public bases and check
bits permit sifting, and the lower-error link supplies unrevealed matching-basis bits to
the public reconciliation helper. **Classical cost.** Sifting and reconciliation scale
with the transmitted data, not with a hidden key search. **Scored resources.** 0
two-qubit gates, depth 3, 3 total gates, 1 active qubit; 2,048 measurement circuits.

## Tier 3: Twenty-Four Seals — Deutsch–Jozsa

**What was hidden.** Whether each of 24 promised constant/balanced Boolean oracles is
constant or balanced. **Why it works.** Interference makes the all-zero input certain
for a constant oracle and impossible for a balanced one in the ideal promise setting.
**Circuit and extraction.** For each oracle: `|0>^6 — H — [oracle] — H — measure`, with a
|−⟩ target; one shot and one oracle call per oracle. All-zero means constant, anything
else balanced. The 24 classifications form the key. **Classical cost.** Deterministic
classical classification can require exponentially many queries in the input width in
the worst case; the advantage relies on the promise and an ideal oracle. **Scored
resources.** 7,808 two-qubit gates, depth 8,771, 19,497 total gates, 7 active qubits.

## Tier 4: The Echo — Simon

**What was hidden.** A nonzero 10-bit XOR period of a promised two-to-one function.
**Why it works.** Each measured sample yields a row `y` with `y·s = 0` over GF(2);
enough independent rows determine the unique nonzero null vector. **Circuit and
extraction.** `|0>^10 — H — [oracle] — H — measure`; a 10-qubit zeroed output register
enters the oracle and is not measured. The solver takes 32-shot batches up to 128 shots
and row-reduces observed equations until rank 9 fixes the period. **Classical cost.**
Black-box collision search is exponential in the input width under the usual model.
**Scored resources.** 183 two-qubit gates, depth 195, 455 total gates, 20 active qubits.

## Tier 5: The Small Safe — Grover search

**What was hidden.** A 10-bit toy-cipher key matching a public known-text prefix.
**Why it works.** With one marked item among 1,024, repeated phase marking and
diffusion amplify its measurement probability; 25 iterations are close to the optimal
`(π/4)√N`. **Circuit and extraction.** `|0>^10 — H — ([reversible cipher phase
oracle] — [diffuser])^25 — measure`; eight scratch qubits and one flag support the
oracle. The phase oracle computes the public prefix predicate, applies a phase, and
uses the true adjoint to uncompute its temporary work. One 128-shot circuit uses 25
phase-oracle calls per shot (3,200 shot-weighted calls). Only measured candidates are
checked; the solver requires a unique prefix-valid key with majority support before
decrypting. **Classical cost.** Exhaustive search is `O(2^10)` cipher checks, trivial at
this size; the quantum query advantage does not make the reversible cipher free.
**Scored resources.** 10,950 two-qubit gates, depth 19,703, 28,413 total gates, 19
active qubits.

## Tier 6: The Bigger Safe — multi-target Grover

**What was hidden.** A 14-bit key when roughly 64 keys satisfy the first-byte predicate.
**Why it works.** If `M` of `N` keys are marked, the success probability after `k` rounds is
`sin²((2k+1)θ)` with `sin²θ = M/N`; a calibration run estimates `M/N` and selects `k`.
**Circuit and extraction.** A 2,048-shot calibration circuit prepares the key
superposition, performs one phase/diffuser round and measures the predicate flag. The
solver then runs at most two search batches (1,024 shots total), checks only observed
candidates against the public predicate, and decrypts and filters by checksum, format
and hash. **Classical cost.** Up to `2^14` candidate checks; again trivial at this toy
size. **Scored resources.** 3,000 two-qubit gates, depth 5,715, 8,752 total gates, 22
active qubits.

## Tier 7: The Hidden Angle — quantum phase estimation

**What was hidden.** A 14-bit eigenphase of the supplied one-qubit unitary. **Why it
works.** Controlled powers imprint the phase on a counting register; an inverse QFT
converts the exact-grid phase into bits. **Circuit and extraction.** `|0>^14 — H —
[controlled U^(2^j)] — inverse QFT — measure`, with the supplied eigenstate as target.
The 64-shot QPE batch must give one consistent 14-bit outcome; a second 32-shot
phase-cancellation circuit built from that measured value must return all zeros. The
phase is converted to the keystream key and decrypted. **Classical cost.** Matrix powers
are constructed classically by repeated squaring; the compiled gate cost is a separate
accounting from abstract oracle queries. **Scored resources.** 209 two-qubit gates,
depth 154, 536 total gates, 15 active qubits. The lower depth/gate count comes from
compiling the executed circuit at optimization level 2 before the Checker's fixed
level-1 pass; the algorithm and measurements are unchanged.

## Tier 8: The Wrapped Key, N = 35 — Shor order finding

**What was hidden.** The factors of the public toy RSA modulus 35. **Why it works.** QPE on modular
multiplication samples information about the order `r` of public base 2; an even order
with a nontrivial half-order yields factors by GCD. **Circuit and extraction.**
`|0>^12 — H — [controlled modular powers] — inverse QFT body — measure`; the six-qubit work register
starts at integer 1. Reversed power-control wiring absorbs the inverse-QFT SWAPs for the
uniformly prepared counting state. Each controlled multiplier implements the complete
six-bit permutation, fixing padding outside the modulus; two retained dirty slots are
restored exactly. A batch is 64 shots, at most two batches. Continued fractions and
bounded subset LCMs propose orders from measured `y/2^12`; modular exponentiation
validates a candidate, then GCD and classical RSA unwrapping yield the key. **Classical
cost.** Trial factoring is trivial for 35; the table synthesis is exponential in the
work width and does not scale. **Scored resources.** 7,856 two-qubit gates, depth
18,804, 22,861 total gates, 18 active qubits. This is the final last-pivot native
synthesis, not the earlier 33,904-CX network.

## Tier 9: The Wrapped Key, N = 77 — Shor order finding

**What was hidden.** The factors of the public toy RSA modulus 77. **Why it works.** The same
measurement-driven order-finding method; 14 counting qubits and seven work qubits.
**Circuit and extraction.** `|0>^14 — H — [controlled modular powers] — full inverse
QFT — measure`; the seven-qubit work register starts at integer 1 and one clean synthesis wire starts at
zero. The public base is 2; multiplication acts modulo 77 below the modulus and fixes
padding. Up to two 64-shot batches yield `y/2^14`; continued fractions, bounded LCMs,
order validation and GCD recover factors for classical RSA decryption. **Classical
cost.** Trial division is trivial for 77; the global fixed-mask synthesis is specific to
this small instance. **Scored resources.** 34,186 two-qubit gates, depth 71,632,
102,830 total gates, 22 active qubits.

## Tier 10: The Handshake — quantum discrete logarithm

**What was hidden.** A Diffie–Hellman exponent from public `A = g^a mod p`. For
`p = 83`, `g = 3` and subgroup order 41, coherent evaluation of `g^x A^z` hides the
kernel `x + az = 0 mod 41`; Fourier sampling yields information about the dual relation
`v = au mod 41`. **Circuit and extraction.** Two six-qubit counting registers and a
seven-qubit work register implement `|x,z,1> → |x,z,g^x A^z mod 83>`, followed by
inverse-QFT bodies and measurements. Reversed control wiring absorbs physical SWAPs for
the prepared uniform registers. Each shot uses 12 controlled public-power blocks. For
measured grid integers, half-up rounding maps each to `u` and `v` modulo 41; the solver
forms measurement-derived equations, rejects uninformative or inconsistent samples and
tests at most eight new candidates per 128-shot batch, with at most two batches.
**Classical cost.** Brute force is feasible for this small subgroup; it grows with the
order and is not a scalable method. **Scored resources.** 38,823 two-qubit gates, depth
92,604, 111,337 total gates, 19 active qubits.

## Optimization and correctness

**Tier 5.** The accepted 19-qubit implementation resynthesizes consecutive CNOT windows
as exact GF(2) linear transformations after basis transpilation and before Aer
execution. Every replaced window was checked on all columns; the recorded maximum error
was zero. The final phase layer uses the actual adjoint, not a copy, so the relative
phase network and scratch qubits are restored. A 22-qubit candidate with 13,802 two-qubit gates
was rejected because all ten strict OSC solves exceeded the 120-second limit; fewer
gates did not mean a better solver.

**Tier 8.** The accepted six-bit modular multipliers use public mixed-polarity Boolean networks and native multi-controlled gates with last-pivot fanout. They preserve the entire permutation, including padding and control-off identity. At 18 active qubits, the final circuit uses 7,856 two-qubit gates, down from 33,904. The four nine-wire operators were compared on all 512 basis columns, including arbitrary borrowed bits; the maximum complex-entry error was below 2.8e-14.

**Tier 9.** The v6.2 integration retained in Candidate A uses affine-coordinate, mixed-polarity synthesis and exact shared-control grouping for five public multipliers. At 22 active qubits, it reduced the v6.1 circuit from 55,999 to 34,186 two-qubit gates. All controlled branches, padding, inverse maps and clean-workspace restoration were checked. In five paired v6.2 trials the median simulator solve time fell from 13.275 to 10.616 seconds.

**Tier 10.** The accepted implementation uses global mixed-polarity group-operation synthesis with a public cache, exact shared-control operations and SWAP-absorbed
QFT wiring: 38,823 two-qubit gates, retained from v6.1 and v6.2 (46,910 in v6; 82,804 in v5), at 19 active qubits. Tests cover
the actual controlled work-register branches, small complex operators and reduced
statevector comparisons; a separate 19-qubit statevector comparison reported error
about `6.5e-15`. These are scoped tests, not a dense full-unitary proof.

**Cross-tier evidence.** A reversible basis mapping alone is insufficient if phases
differ. Exact complex-operator tests, phase-preserving constructions, inverse checks
and restoration of clean or borrowed dirty wires support coherent composition on
superpositions. The modular work register intentionally retains its result and may
remain entangled; it need not return to zero. QFT SWAP absorption in Tiers 8 and 10
relies on uniform initial counting registers. Matching plaintext SHA-256 confirms an
output, not unitary equivalence.

## Analysis: classical versus quantum cost

The table compares the abstract query cost of each algorithm with the concrete work in
this submission. It deliberately separates oracle queries and shots from compiled
gates; the scored circuit is only one axis.

| Tier | Classical baseline | Quantum work in this solver | Scaling caveat |
|---:|---|---|---|
| 1 | up to 24 parity queries | 1 oracle call, 1 shot | oracle is supplied; advantage is query count |
| 2 | classical key distribution | 2,048 single-qubit measurements | security protocol, not a speed contest |
| 3 | up to `2^{n-1}+1` queries worst case | 24 oracle calls, 24 shots | promise-dependent |
| 4 | `O(2^{n/2})` collision queries | 32–128 shots, rank-9 rows | finite sampling can fail |
| 5 | `O(2^{10})` cipher checks | 25 iterations × 128 shots | reversible oracle dominates gates |
| 6 | `O(2^{14}/M)` checks | 2,048 pilot + ≤1,024 search shots | calibration is statistical |
| 7 | classical phase estimation | 64 + 32 shots; 14 controlled powers per shot | exact-grid assumption |
| 8 | trial division is trivial for 35 | 12 controlled blocks × ≤128 shots | 64-entry table synthesis |
| 9 | trial division is trivial for 77 | 14 controlled blocks × ≤128 shots | 128-entry table synthesis |
| 10 | `O(41)` brute force for this subgroup | 12 blocks × ≤256 shots | small subgroup, bounded sampling |

Grover gives a quadratic query reduction, `O(√(N/M))` versus `O(N/M)` under comparable
assumptions; Shor gives a polynomial-time order-finding framework against
sub-exponential classical factoring. Those asymptotic statements do not transfer
directly to this submission: the moduli are 35 and 77, the group order is 41, and the
solver uses explicit public permutation tables whose classical preparation is
exponential in the work width. At these sizes classical brute force or trial division
is immediate, so the exercise demonstrates the algorithms and their measurement paths,
not an end-to-end practical advantage.

A second distinction is query complexity versus circuit cost. Tier 5 uses only 25
oracle calls per shot but a reversible cipher with thousands of two-qubit gates; Tier 8
uses 12 controlled blocks but a table-synthesis preprocessing step that does not scale.
No claim is made that these compiled gate counts are competitive with classical
factoring at cryptographic sizes.

## Hardware, noise and the simulator boundary

Every result here comes from Qiskit Aer statevector simulation with an all-to-all
transpiler. That removes the dominant hardware costs: two-qubit gate error
(device- and calibration-dependent), readout error, limited qubit coherence,
and connectivity that forces SWAP routing and therefore more two-qubit gates. A real
run would also need calibration-aware transpilation, dynamical decoupling or error
mitigation, and repeated shots to build confidence; none of that is modeled here.

At cryptographic key sizes the gap is qualitative, not a constant factor. Shor's
modular exponentiation requires a fault-tolerant arithmetic design; physical qubit and timing estimates depend on the logical circuit, code, error rates and architecture. The toy circuits in this submission are scoring instruments and
teaching examples, not resource estimates for RSA-2048 or real Diffie–Hellman groups.
No physical-hardware run is claimed, and no hardware speedup is inferred from simulator
gate counts.

## Validation and limits

The v6.3 package was checked in a clean official checkout with only the v6.3 Candidate A ZIP
extracted: 10/10 FULL, ten matching hashes, Aer execution in all ten tiers, no flags, no
timeouts, and 103,166 / 217,625 / 294,982 aggregate metrics. Tier 5 was independently
checked on all 1,024 key inputs (maximum phase error `9.1e-16`, no detectable work/flag leakage);
Tier 8 was checked on the full 512-column controlled operators for multipliers 2, 4, 11
and 16 (maximum error `2.8e-14`). Five fresh simulator seeds passed for each of Tiers 5
and 8 during v6.3 integration; finite seeds do not prove a zero failure rate.

The table uses the approved Candidate A reference run. Junqi's three-run reconciliation found the same CX and active widths, with a depth sum of 217,602 and 294,857 total gates on his platform. Independent approval of the original archive does not transfer automatically to the v6.3.1 documentation ZIP.

Remaining limits: the hash checks the plaintext, not the unitary; complex-operator
evidence is scoped to selected blocks; the tables, compilation and shot budgets are
tuned to these small instances; and Simplicity depends on other teams' eligible
metrics, so no final simplicity score is asserted here.

## Conclusion

All ten measurement-driven workflows recovered their keys in the audited v6.3 run. The
selected circuits use 103,166 two-qubit gates in total, with every tier executing a
real Aer circuit and every hash matching. The main lesson is not a speedup claim: it is
that each algorithm's measurement semantics, reversible arithmetic and classical
post-processing can be made explicit and independently checked at toy scale, while the
scaling and hardware gaps to real cryptography remain large.
