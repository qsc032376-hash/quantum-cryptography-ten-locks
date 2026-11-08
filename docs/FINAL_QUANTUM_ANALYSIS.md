# Ten Locks: final mathematical and experimental analysis

This document describes the verified v4 candidate [`73f4dbe330de3098acb368464d3f5606c30259f8`](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/tree/73f4dbe330de3098acb368464d3f5606c30259f8), not the contents of this documentation branch. It synthesizes the existing [ten tier models](../README.md#the-ten-quantum-locks), [optimization plan](MATHEMATICAL_OPTIMIZATION_PLAN.md), [Tier 9/10 handoff](TIER09_TIER10_OPTIMIZATION_HANDOFF.md), and [Tier 10 prototype](TIER10_OPTIMIZATION_PROTOTYPE.md). No circuits were rerun for this analysis. Detailed evidence and the scope of the full v4 Checker run are in the [v4 integration report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/73f4dbe330de3098acb368464d3f5606c30259f8/docs/OPTIMIZED_V4_CANDIDATE.md) and [recorded Checker JSON](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/73f4dbe330de3098acb368464d3f5606c30259f8/docs/evidence/v4/report.json).

## Quantum–classical architecture

**Challenge → circuit → measurement → classical recovery → cryptographic verification.** Public challenge parameters determine state preparation and a reversible computation or permitted Oracle. On Aer, interference and measurement produce classical samples: bit strings, phase estimates, candidate keys or group relations. Classical code uses those samples to solve linear equations, form continued fractions and greatest common divisors, check group relations, or select and decrypt a candidate. The recovered key material feeds the specified cipher or keystream; the returned plaintext is verified by the official SHA-256 hash.

Classical processing can validate or reject measurement-derived candidates, but an unrelated circuit followed by a classical search does not establish the required quantum recovery. A hash match confirms the plaintext, not the method or a hardware advantage. In Tier 2 the quantum communication model and basis reconciliation replace the search pattern; its sifted measurements still drive key reconstruction and verification. No secret values or challenge plaintext are reproduced here.

## Mathematical foundations across the ten locks

| Tier | Structure and why it fits |
| --- | --- |
| [1](TIER01_THEORY.md) | Bernstein–Vazirani: for the promised parity function `f_s(x)=s·x mod 2`, phase kickback produces `(-1)^(s·x)`. A final Hadamard transform maps the character to the hidden string s in the ideal model. |
| [2](TIER02_THEORY.md) | BB84: matching preparation and measurement bases give correlated bits; mismatched bases are random in the ideal model. Under the specified random intercept–resend attack, the sifted error rate is 25% in expectation. Sampled error rates identify the disturbed link, then basis reconciliation recovers bits. |
| [3](TIER03_THEORY.md) | Deutsch–Jozsa: the all-zero amplitude after phase kickback and Hadamards is `2^-n Σ_x (-1)^f(x)`. It has magnitude one for a constant function and zero for a balanced function, under the promise. Apply the test to each supplied Oracle. |
| [4](TIER04_THEORY.md) | Simon: for `f(x)=f(x⊕s)` under the two-to-one promise, interference yields samples y satisfying `y·s=0` over `F₂`. Collect sufficient independent rows and solve the resulting nullspace classically. |
| [5](TIER05_THEORY.md), [6](TIER06_THEORY.md) | Grover: a reversible phase oracle marks candidate keys and the diffuser reflects around the initial uniform state. With `sin²θ=M/N`, r iterations give marked-subspace probability `sin²((2r+1)θ)`. Tier 5 marks the two-byte condition; Tier 6 marks only its specified first-byte condition, then checks measured candidates and the checksum classically. |
| [7](TIER07_THEORY.md) | QPE: for `U|u⟩=e^(2πiφ)|u⟩`, controlled powers place phase information on the count register; inverse QFT and measurement estimate φ. Power phases, including any controlled global phase, must be preserved. |
| [8](TIER08_THEORY.md), [9](TIER09_THEORY.md) | Shor order finding: controlled modular powers of public coprime a make phase estimation sample information about `r=ord_N(a)`. Classical continued fractions and validation recover an order candidate. If r is even and `a^(r/2) ≠ ±1 (mod N)`, the gcds with `a^(r/2)±1` yield nontrivial factors for the challenge's two-prime moduli. RSA unwrapping is classical. |
| [10](TIER10_THEORY.md) | Shor discrete log: `f(x,z)=g^x A^z` with `A=g^a` hides `Δx+aΔz=0 mod r`. Two-register Fourier samples give approximate frequencies `(u,v)` satisfying `u a=v mod r` when correctly decoded. Classical processing rounds the finite-grid samples, verifies candidates with `g^a=A`, and derives the Diffie–Hellman shared integer. |

These are ideal algorithmic statements with their stated promises. Query counts do not automatically include the cost of implementing an Oracle, compiling modular arithmetic, classical preprocessing, repeated shots or running a physical device.

## Correctness of the validated optimizations

### Tier 5: fold public constants into the comparison

For ciphertext byte `c_i`, public round constant `d_i`, key rotation `R_i`, key-dependent mask M, public invertible S-box layer S and bit permutation P, the comparison against a public target byte `b_i` obeys

`P(S(c_i ⊕ d_i ⊕ M(R_i k))) = b_i` iff `M(R_i k) = c_i ⊕ d_i ⊕ S⁻¹(P⁻¹(b_i))`.

**Proof.** Apply the public inverses and XOR the known terms. Compute only the right-hand constants classically; the key-dependent mask is still computed reversibly on the quantum register. Both byte comparisons remain necessary. With `e_i(k)` the comparison predicates and work/flag initialized to zero, both implementations apply exactly `|k,0,0⟩ → (-1)^(e_0(k)e_1(k)) |k,0,0⟩`. The mask and flag are uncomputed; the exact dirty-MCX comparison restores its borrowed key wires and coherent phase. Linearity proves equality for arbitrary key superpositions on that clean-work/flag subspace, not for arbitrary nonzero work inputs. The unchanged diffuser can then be applied each round, preserving the complete ideal output distribution by induction.

**Synthetic evidence.** The [Tier 5 optimization report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/804b9dd349a40edd834fd06dfb2ceb09c6658bfc/docs/TIER05_OPTIMIZATION_RESULT.md) records synthetic phase-sensitive comparisons for both conditions true, each alone true and neither true, work restoration and one-round interference; it also documents test corrections and a stricter harness reliability result of `INCONCLUSIVE`. **Official evidence.** The optimization report records individual full/hash checks, while the [v4 integration report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/73f4dbe330de3098acb368464d3f5606c30259f8/docs/OPTIMIZED_V4_CANDIDATE.md) records the subsequent joint ten-tier run. These are complementary to the proof, not substitutes for it.

### Tier 9: exact shared-control fanout

**Proof.** For adjacent controlled X operations with the same predicate f, including the external phase bit, targets do not occur in f. Their X gates commute and repeated targets cancel in pairs. For remaining targets choose a pivot p; let F fan p out by CX to the other targets. Execute F, `X_p` controlled on f, then `F⁻¹`. If f=0 the fanouts cancel; if f=1, p and each other selected target flip once. The sequence equals the original gates as an exact full-domain unitary, including external control 0/1, arbitrary pivot state, padding and coherent phases. The actual v4 Tier 9 implementation uses no additional ancillary register: there is no clean-bit initialization assumption or extra ancilla to restore. It does not use the alternative single-clean-bit prototype as its default.

**Synthetic evidence.** The [Tier 9 optimization report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/17df36d1c31cd441cd3bd840157caadd3062cada/docs/TIER09_OPTIMIZATION_RESULT.md) records checks of all 256 control/work labels for each of 14 public blocks, gate-phase structure and padding; reduced synthetic circuits were compared by complex amplitudes and measurement probabilities. **Official evidence.** It records individual renamed-directory Checker and finite multi-seed tests; v4 subsequently passed the full joint Checker. The finite seed set is not exhaustive.

### Tier 10: QFT relabeling and ancilla-free fanout

**Proof.** Each inverse QFT is `D S`, where S is the initial bit reversal and D is the remaining negative-angle controlled-phase/H sequence. Let U be both controlled modular-power series and S reverse both count registers. Rewire each logical power to the reversed physical control, giving `U′=S U S`. On the actual uniform count preparation `|ψ₀⟩`, `S|ψ₀⟩=|ψ₀⟩`, hence `D U′|ψ₀⟩ = D S U|ψ₀⟩`. This preserves the complete state on the original physical wires and all joint probabilities, including finite-grid tails. It is a **preparation-scoped** equality: on an arbitrary input an additional input reversal is required. Measuring `X_j→c_j`, `Z_j→c_(6+j)` keeps the 12-bit string `z5…z0 x5…x0`; no undocumented reversal is needed.

The modular blocks independently use the same exact predicate fanout proof as Tier 9. Targets and controls are disjoint; no new ancilla is used or needs restoration. Cache reuse avoids rebuilding public circuits, but does not remove applications controlled by different bits. Each decoded `(u,v)` is rounded from a 64-point grid; a tail sample need not satisfy the true relation, so a measured candidate is checked against the public group relation before decryption.

**Synthetic evidence.** The [full-scale Tier 10 optimization report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/7c9d03238835a8b02fbf489440440059cad4ee13/docs/TIER10_FULL_OPTIMIZATION_RESULT.md) records reduced-instance complex-state and full joint-distribution comparisons, QFT sign/measurement-layout and synthetic classical-interface tests, plus all control/work labels of the 12 public multiplication blocks. **Official evidence.** The candidate passed Tier 10 Checker in a renamed directory; v4 then incorporated it and passed the full ten-tier Checker. Neither test set proves success under arbitrary hardware noise.

## Benchmark interpretation

The following are the requested recorded v1 and v4 results; v1 tier metrics come from the frozen [Tiers 1–7](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/868fb65e20c73a27bffc118f3617080df9cf2f8b/docs/SUBMISSION_STATUS.md), [Tiers 8–9](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/868fb65e20c73a27bffc118f3617080df9cf2f8b/docs/TIER08_TIER09_INTEGRATION.md), and [Tier 10](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/868fb65e20c73a27bffc118f3617080df9cf2f8b/docs/TIER10_INTEGRATION.md) reports, and v4 metrics come from its joint run. Percentages are `(v1−v4)/v1 × 100`.

| Metric | v1 | v4 | Reduction |
| --- | ---: | ---: | ---: |
| Sum of per-tier two-qubit gates | 307,349 | 248,321 | 59,028 (19.21%) |
| Sum of per-tier depths | 787,876 | 633,141 | 154,735 (19.64%) |
| Tier 5 two-qubit gates | 21,150 | 15,150 | 6,000 (28.37%) |
| Tier 9 two-qubit gates | 117,739 | 89,075 | 28,664 (24.35%) |
| Tier 10 two-qubit gates | 107,168 | 82,804 | 24,364 (22.73%) |

A sum of ten independently selected circuit depths is a comparative aggregate, not the depth of a single circuit or a simultaneous workload. The historical v1 figures and the v4 joint run were recorded in different environments; they share the reported scoring setup but are not a controlled cross-platform timing experiment. For a same-machine comparison, the [v4 report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/73f4dbe330de3098acb368464d3f5606c30259f8/docs/OPTIMIZED_V4_CANDIDATE.md) reports v3→v4 Tier 10 two-qubit gates 107,168→82,804 while solve time changed 1.368→2.072 seconds. This is one paired observation, not a universal slowdown. Aer can execute native multi-controlled gates differently from the fixed-basis scoring transpiler; gate types, statevector width, fusion, memory, scheduling and compilation all matter. Smaller scored circuits need not simulate faster.

The official configuration uses `rz,sx,x,cx`, all-to-all coupling, optimization level 1 and seed 12345; its other settings and limits are in [scoring_config.yaml](../tools/scoring_config.yaml). Decomposition, optimization level, seed, connectivity and layout can change cancellations, routing, depth and counts. The Checker scores the actual Aer-executed circuit with the most transpiled two-qubit gates, ties broken by depth; Tier 2 uses its channel log. Active qubits and total gates also contribute. Shots, calls, classical preparation and runtime are additional costs, not represented by one scored circuit. [Official scoring](../SCORING.md) makes simplicity relative to eligible teams with weights 40%, 30%, 20%, 10%; no final point total follows from our counts alone.

## Scientific and competition limits

- **Noise and sampling:** the reported v4 run is an ideal, bounded, fixed-seed simulator execution. Finite samples can miss a useful outcome, yield insufficient independent Simon equations, fail to recover an order, or produce off-peak discrete-log frequencies. Hash success in one run is not deterministic success or a noise-tolerance estimate. In Tier 2, 25% QBER is an expectation for the stated attack model, not a universal threshold or full security proof.
- **Depth and hardware:** deep two-qubit circuits are sensitive to physical gate errors, decoherence, connectivity, calibration, routing and measurement error. All-to-all transpilation is not a hardware mapping; an actual experiment needs a specified backend, noise model, timing, shot budget and measured error bars. No quantum hardware advantage is established.
- **Simulation and scaling:** statevector storage grows exponentially with active qubits; a public permutation truth table also grows exponentially in its width. Small permitted instances and Qiskit Aer execution do not demonstrate scalable Shor circuits or practical cryptanalytic advantage. Classical timing, memory, shots and query costs must be reported separately.
- **Validation scope:** v4's renamed-directory full-package run records `full`, matching hashes, valid metrics and no flags for all ten tiers, but is a local result, not an independent final competition award. A flag is a review request, not automatically a penalty. No full joint Checker for a v5/Tier 8 change is asserted here; Tier 8 results in this document are v4's unchanged results.

For an English delivery and suggested judge questions, see [the final presentation script](FINAL_PRESENTATION_SCRIPT.md).
