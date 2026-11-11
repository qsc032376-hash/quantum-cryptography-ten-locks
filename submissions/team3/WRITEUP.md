# Quantum Cryptography: Ten Locks, One Message — Team 3 Write-up

**Sicheng Qian, Junqi Sheng, Youyang Shang, Junrui Yu**

The Ohio State University · Qiskit Fall Fest 2026

## Abstract

We solve ten encrypted-file challenges with Bernstein–Vazirani, BB84, Deutsch–Jozsa, Simon, Grover search, phase estimation, Shor order finding and quantum discrete logarithms. Each `solve()` executes a Qiskit Aer circuit and uses measurements in key recovery. Classical post-processing decrypts the file and verifies its SHA-256. The independently audited v6 runtime candidate achieved FULL and matching hashes in all ten tiers. Its ten selected circuits use 32.54% fewer two-qubit gates in aggregate than v5. This is a circuit-resource comparison on a classical simulator, not evidence of a hardware speedup.

## Problem and methodology

Each file encodes a line using a key hidden behind a different oracle, channel or public cryptographic construction. We identify the structure, construct a circuit using the provided public interfaces, execute it on Aer and interpret its measurements. Classical routines perform operations such as linear algebra, candidate checking, continued fractions, GCD, reconciliation, key derivation and decryption. The official Checker hashes each returned plaintext; the hash checks the answer, while the circuit and measurement-to-key path explain how it was obtained.

The resource figures below are post-transpilation metrics for the one circuit selected by the official Checker in each tier, not the total work across shots or retries. It selects the executed circuit with the most two-qubit gates, then greatest depth. The independently reproduced v6 report recorded FULL, hash match, circuit execution, valid metrics and no flags for every tier. Raw private measurement strings and their frequencies were not retained in that report; we give the implemented recovery rules and shot budgets rather than inventing outcomes. Circuit sketches show logical blocks; `build_circuit()` in each solution provides the corresponding diagram interface, though it is not itself scored.

## Tier 1: The Parity Vault — Bernstein–Vazirani

**Objective and principle.** Recover a 24-bit XOR mask from a parity oracle. Phase kickback converts the oracle's inner product into a phase; Hadamards then map that phase to the hidden string.

**Circuit and extraction.** `|0>^24 — H — [parity oracle] — H — measure`; target `|1> — H — [oracle]` supplies |−⟩. One circuit, one shot and one oracle call produce the measured key bits, converted with the recorded classical-bit ordering. Classical XOR decrypts the file. The independent Checker confirmed the resulting hash; the actual string was not retained in the report. A classical black-box approach needs up to 24 independent bit queries. The exact one-shot outcome assumes the promised oracle and ideal simulation.

**Scored resources:** 151 two-qubit gates; depth 44; 298 total gates; 25 active qubits.

## Tier 2: Two Links — BB84

**Objective and principle.** Identify the intercepted link and reconstruct the clean link's key. Measuring in Alice's basis preserves an ideal BB84 bit; intercept-resend introduces errors among matching-basis check bits.

**Circuit and extraction.** For each received qubit Bob applies either identity (Z basis) or H (X basis), then measures. Bases are chosen before disclosure. After each of the two 1,024-qubit links is measured once, public bases and check bits permit sifting and a matching-basis error-rate comparison. The lower-error link supplies unrevealed matching-basis bits to the public reconciliation helper; classical XOR decrypts. The Checker recorded 2,048 measurement circuits and no repeat measurements. Each is one received-qubit measurement; the selected scored circuit includes the channel preparation. The independent hash matched. The fixed basis seed is for reproducibility, not production randomness; finite checks and the one-clean-link promise do not constitute a general security proof.

**Scored resources:** 0 two-qubit gates; depth 3; 3 total gates; 1 active qubit. Classical sifting and reconciliation scale with the transmitted data and reconciliation procedure.

## Tier 3: Twenty-Four Seals — Deutsch–Jozsa

**Objective and principle.** Classify 24 promised constant or balanced Boolean oracles. Interference makes the all-zero input result certain for a constant oracle and impossible for a balanced one in the ideal promise setting.

**Circuit and extraction.** For each oracle: `|0>^6 — H — [oracle] — H — measure`, with a |−⟩ target. The 24 circuits use one shot and one oracle call each. All-zero maps to constant; any other result maps to balanced. The classifications in oracle order form the key, which feeds the classical keystream decryptor. The independent hash matched; individual outcomes are not in the report. Classical deterministic classification can require exponentially many queries in the input width in the worst case; the advantage relies on the promise and ideal oracle.

**Scored resources:** 7,808 two-qubit gates; depth 8,771; 19,497 total gates; 7 active qubits.

## Tier 4: The Echo — Simon

**Objective and principle.** Find the nonzero 10-bit XOR period of a promised two-to-one function. Each sample yields a row y satisfying y·s = 0 over GF(2).

**Circuit and extraction.** `|0>^10 — H — [oracle] — H — measure`; a 10-qubit zeroed output register enters the oracle and remains unmeasured. Each shot queries the oracle once. The solver takes 32-shot batches, up to 128 shots, and row-reduces the observed equations until rank 9 determines the unique nonzero null vector. The period feeds classical keystream decryption. The independent Checker passed; its report does not retain the rank history or bitstrings. Sampling may fail to reach sufficient rank within the finite budget. A classical collision search has exponential query cost in the input width under the usual black-box model.

**Scored resources:** 183 two-qubit gates; depth 195; 455 total gates; 20 active qubits.

## Tier 5: The Small Safe — Grover search

**Objective and principle.** Find a 10-bit toy-cipher key matching known text. With one marked item among 1,024, repeated phase marking and diffusion amplify its measurement probability.

**Circuit and extraction.** `|0>^10 — H — ([reversible cipher phase oracle] — [diffuser])^25 — measure`; eight scratch qubits and one flag support the oracle. It computes the public prefix predicate, applies a phase, and uncomputes temporary work. One 128-shot circuit uses 25 phase-oracle calls per shot, or 3,200 shot-weighted calls. Classical checks consider only measured keys, require a unique prefix-valid candidate with majority support, and decrypt. The independent hash matched; private counts are unavailable in the aggregate report. Sampling may fail, and the fixed iteration count assumes the stated one-solution promise. Classical exhaustive search is O(2^10) cipher checks; the quantum query advantage does not make the reversible cipher free.

**Scored resources:** 14,552 two-qubit gates; depth 28,132; 40,938 total gates; 19 active qubits.

## Tier 6: The Bigger Safe — multi-target Grover

**Objective and principle.** Recover a 14-bit key when roughly 64 keys satisfy the first-byte predicate. If M of N keys are marked, Grover's amplified probability after k rounds is sin²((2k+1)θ), where sin²θ = M/N.

**Circuit and extraction.** A calibration circuit prepares the key superposition, performs one phase-oracle/diffuser round, computes the predicate into a measured flag, and uses 2,048 shots. A statistical estimate selects the number of rounds for `H — ([Q phase] — [diffuser])^k — measure`. The solver uses at most two search batches and 1,024 search shots; each search shot uses k phase queries, and each pilot shot uses one phase and one bit-predicate query. It checks only observed candidates against the public first-byte predicate, then classically decrypts and filters by checksum, format and hash. The audited run executed two circuits and matched the hash, but does not disclose its pilot frequency, chosen k or search counts. Statistical calibration and candidate coverage are bounded, not guaranteed; a supplemental batch may be used if needed and time permits. Classical enumeration costs up to 2^14 candidate checks.

**Scored resources:** 3,000 two-qubit gates; depth 5,715; 8,752 total gates; 22 active qubits.

## Tier 7: The Hidden Angle — quantum phase estimation

**Objective and principle.** Recover a 14-bit eigenphase of the supplied one-qubit unitary. Controlled powers imprint the phase on a counting register; an inverse QFT converts the exact-grid phase into bits.

**Circuit and extraction.** `|0>^14 — H — [controlled U^(2^j)] — inverse QFT — measure`, with the supplied eigenstate as target. The 64-shot QPE batch must give one consistent 14-bit outcome. A second 32-shot quantum phase-cancellation circuit built from that measured value must yield all zeros. Each shot uses 14 controlled-power blocks, equivalent to 16,383 base-U applications if powers are counted as repeated queries; the two batches therefore represent 1,572,768 base-U applications under that convention. Matrix powers are classically constructed by repeated squaring, so actual compiled gate cost is a different accounting. The measured phase is converted to the keystream key and decrypted; the independent hash matched. Exact-grid behavior and ideal gates are assumptions, and the phase check is not a hardware-noise test.

**Scored resources:** 209 two-qubit gates; depth 266; 727 total gates; 15 active qubits.

## Tier 8: The Wrapped Key, N = 35 — Shor order finding

**Objective and principle.** Factor the toy RSA modulus to unwrap a key. QPE on modular multiplication samples information about the order r of public base 2; an even order with a nontrivial half-order gives factors via GCD.

**Circuit and extraction.** `|0>^12 — H — [controlled modular powers] — inverse QFT body — measure`; six work qubits start at |1⟩. Reversed power-control wiring absorbs the inverse-QFT SWAPs for the uniformly prepared counting state. Each controlled multiplier acts on all six-bit work states, fixing padding outside the modulus. A batch has 64 shots; at most two batches are allowed. Continued fractions and bounded subset LCMs propose orders from measured y/2^12; modular exponentiation validates and reduces a candidate, then GCD yields factors and classical RSA unwrapping yields the key. Trial factoring is applied to a measurement-derived candidate order, not to the modulus. The independent hash matched, but the measured frequencies were not retained. Finite samples can fail, and explicit small permutation tables do not scale to cryptographic moduli.

**Scored resources:** 33,904 two-qubit gates; depth 96,055; 102,561 total gates; 18 active qubits. The circuit contains 12 controlled public-power blocks per shot; their table synthesis and gate costs are separate from abstract oracle queries.

## Tier 9: The Wrapped Key, N = 77 — Shor order finding

**Objective and principle.** Apply the same measurement-driven order-finding method to a larger toy RSA modulus.

**Circuit and extraction.** `|0>^14 — H — [controlled modular powers] — full inverse QFT — measure`; seven work qubits start at |1⟩ and one clean synthesis wire starts at zero. The public base is 2; multiplication acts modulo 77 below the modulus and fixes padding. The clean wire can be used by exact decomposition and must return to zero. Up to two 64-shot batches yield y/2^14; continued fractions, bounded LCMs, order validation and GCD recover factors for classical RSA decryption. There are 14 controlled-power blocks per shot. The independent hash matched; raw frequencies are not in the report. Bounded sampling can fail, and the table-based implementation is specific to this small instance.

**Scored resources:** 55,999 two-qubit gates; depth 120,242; 168,116 total gates; 22 active qubits.

## Tier 10: The Handshake — quantum discrete logarithm

**Objective and principle.** Recover a Diffie–Hellman exponent from public A = g^a mod p. For p = 83, g = 3 and supplied subgroup order 41, coherent evaluation of g^x A^z hides the kernel x + az = 0 mod 41; Fourier sampling produces information about the dual relation v = au mod 41.

**Circuit and extraction.** Two six-qubit counting registers and a seven-qubit work register implement `|x,z,1> → |x,z,g^x A^z mod 83>`, followed by inverse-QFT bodies and measurements. Reversed control wiring absorbs the physical SWAPs for the prepared uniform registers. Each shot uses 12 controlled public-power blocks. For measured grid integers bX and bZ, classical half-up rounding maps each from the 64-point grid to u and v modulo 41. The solver forms measurement-derived equations, rejects uninformative or inconsistent samples, and tests at most eight new candidates per 128-shot batch against the public relation, with at most two batches. A verified exponent derives the shared secret and keystream. The independent hash matched; raw outcomes are not published in the aggregate report. Rounding can produce false equations and the bounded sampling may fail; this is not a general exponent-search fallback.

**Scored resources:** 46,910 two-qubit gates; depth 109,763; 132,023 total gates; 19 active qubits. Classical brute force is feasible for this small subgroup but grows with its order.

## Circuit optimization and correctness

**Tier 5.** The accepted 19-qubit implementation resynthesizes consecutive CNOT windows as GF(2) linear transformations after normal basis transpilation and before Aer execution. Full complex operators of every replaced window were compared on all columns; the recorded maximum error was zero. The positive-CNOT maps preserve phase and their composition preserves the original reversible transformation and restoration behavior. The final circuit has 14,552 two-qubit gates. A 22-qubit candidate with 13,802 gates was excluded after all ten strict OSC solves exceeded the 120-second solve timeout. Ten paired OSC trials of the accepted rewrite passed, but its measured simulation solve time increased.

**Tier 8.** Controlled modular multipliers use a hybrid choice between fixed-mask row elimination and cycle-anchor synthesis. Both implement the complete public permutation, including padding and control-off identity; anchor choice reduces a construction cost without proving global optimality. Relative to the immediately preceding baseline, two-qubit gates fell 42,792 → 33,904 and depth 123,300 → 96,055, with 18 active qubits unchanged. Ten paired OSC trials passed. Independent complex-operator checks covered each actual nine-wire controlled block, including dirty-wire values and inverse, with maximum element error approximately 2.94×10⁻¹³; this was not a full 18-qubit dense-operator test.

**Tier 9.** Global fixed-original-mask elimination synthesizes the complete seven-bit permutation; already fixed rows remain untouched. Exact shared-control grouping preserves the controlled mapping and phase. The approved v2 changed two-qubit gates 89,075 → 55,999, depth 235,048 → 120,242, and active qubits 21 → 22. Ten paired OSC trials passed correctness, but mean solve time rose from 28.2307 to 36.0989 seconds. The original overall benchmark label remains **INCONCLUSIVE**; the subsequent integration decision selected v2. Earlier timeout evidence remains relevant.

**Tier 10.** The independently accepted v2 uses shorter safe control predicates for reversible permutation synthesis, exact shared-control operations and SWAP-absorbed QFT wiring. Two-qubit gates fell 82,804 → 46,910 and depth 218,263 → 109,763, with 19 active qubits. Tests cover actual controlled work-register branches, small complex operators and reduced-state comparisons; a separate 19-qubit statevector comparison reported error about 6.5×10⁻¹⁵. These are scoped tests, not a dense full-unitary proof. The v2 simulation was slower in its cited benchmark.

A reversible basis mapping alone is insufficient if phases differ. Exact complex-operator tests, phase-preserving gate constructions, inverse checks and restoration of temporary clean or borrowed dirty wires support coherent composition on superpositions. The modular work register intentionally retains its result and may remain entangled; it need not return to zero. QFT SWAP absorption in Tiers 8 and 10 relies on uniform initial counting registers, rather than equality of the bare operators on arbitrary inputs. Matching plaintext SHA-256 confirms an output, not equivalence of quantum unitaries; finite tests and compiler assumptions limit the evidence.

## Scaling and classical comparison

Grover needs O(√(N/M)) oracle queries for M marked items, versus O(N/M) expected classical search under comparable assumptions; constructing and uncomputing a reversible oracle can dominate its gates. Shor's framework uses QPE and efficient reversible modular arithmetic to extract an order, followed by classical continued fractions and GCD. These toy solutions also use classical preprocessing, explicit public permutation tables, synthesis heuristics, bounded candidate validation and post-processing. A table of 2^w work states requires exponential storage in w; fixed small permutations do not establish scalable arithmetic. Classical brute force or factoring is practical at these sizes. Neither query complexity nor a lower scored gate count establishes an end-to-end advantage for this implementation, and no practical RSA-2048 break is claimed.

## Hardware and noise

Aer and OSC Cardinal are classical simulation platforms, not quantum processors. On hardware, two-qubit errors accumulate, limited coherence constrains circuit duration, and readout errors corrupt measured equations. Restricted connectivity requires routing and additional gates. Reliable large instances would require fault-tolerant logical gates, error correction, physical-qubit overhead and far longer resource estimates; the ideal, all-to-all scoring circuit does not include those costs. No physical-hardware run is claimed.

## Experimental methodology and results

The audited runtime RC is commit `c4455782ea9388d5897fc27270f42dd3786ed35d`; its tested team tree is `5d825abd0f0c82546c83574bf4148c3a92238d83`. Frozen v5 is `41c7c6775b8fc499c2acdd878b4829bd17e1210d`. The independent audit used Python 3.12.10, Qiskit 2.6.1 and Aer 0.18.2 with pinned requirements. Official scoring uses basis `rz`, `sx`, `x`, `cx`, all-to-all connectivity, optimization level 1 and transpiler seed 12345; solve and scoring transpilation each have a 120-second limit. Youyang independently rebuilt the runtime ZIP byte-for-byte, checked its manifest, and ran the unchanged official Checker on an extracted copy: ten FULL, ten matching hashes, no flags or timeouts. That archive contained runtime files only; the final archive containing this write-up must be rebuilt and receive a new digest.

| Metric, summed over ten selected circuits | v5 | v6 | Reduction |
|---|---:|---:|---:|
| Two-qubit gates | 241,211 | 162,716 | 32.54% |
| Sum of per-tier depths | 621,301 | 369,186 | 40.58% |
| Total gates | 711,705 | 473,370 | 33.49% |

These are ten independent circuits, not a monolithic circuit or the total cost of all shots. The per-tier metrics appear in the [README](README.md). Simplicity uses relative best/team ratios weighted 40% two-qubit gates, 30% depth, 20% total gates and 10% active qubits. Without other teams' eligible metrics, a final Simplicity score cannot be determined.

A single full Checker run establishes observed correctness in that environment. Paired-seed OSC trials provide additional finite reliability and performance evidence; they do not prove zero failure probability. They record solve or wall time and sampled process-tree peak RSS, which can miss brief peaks or double-count shared pages. Nodes, load and simulation representations affect comparisons. Mathematical operator tests address a different question from hashes and sampled runs. In particular, reduced gates need not imply faster simulation: Tier 9 used an additional active qubit and was slower in the paired sample. The rejected Tier 5 clean-ancilla candidate illustrates the gate-versus-time tradeoff.

## Conclusion

All ten measured quantum workflows recovered their keys in the independently audited run. The v6 selected circuits reduced aggregate two-qubit gates by 32.54% from v5, supported by reproducible Checker results and scoped mathematical and multi-seed evidence. Future work includes scalable reversible arithmetic, broader reliability studies and realistic noise and fault-tolerance analysis. Neither arbitrary-seed success nor real-hardware performance is guaranteed by these simulator results.
