# Ten Locks, One Message: presentation script

**Target:** approximately 6 minutes 30 seconds at a measured speaking pace, plus questions. The four speaker assignments and transitions below are provisional. Show only public parameters, circuit diagrams, aggregate statistics and pass/fail results; do not display recovered keys, private exponents, witnesses, plaintext or challenge data. The following demo describes a prepared, sanitized display of the recorded v5 evidence, not a live run promised by this documentation branch.

## 0:00–0:45 — The challenge and objective

**Sicheng Qian — mathematical modeling and optimization**

> Imagine ten locks, each built around a different kind of structure. Our goal was to understand which quantum method extracts useful information from each lock, then use classical cryptography to finish the recovery and verify the result.
>
> We studied hidden strings, quantum communication, reversible search, phases and periodicity. We also asked a practical question: can we simplify the circuits while keeping the mathematical behavior needed by the solution? Our verified reference is candidate v5. A local full-package run of the official Checker reported all ten tiers full, with matching hashes and valid resource metrics. That is a verification result, not a final competition ranking.

## 0:45–1:45 — Quantum–classical architecture

**Youyang Shang — classical cryptography and software**

> Our pipeline has five steps: challenge, quantum circuit, measurement, classical recovery, and cryptographic verification. The challenge gives public inputs or an allowed Oracle. A circuit prepares a state and uses interference to make useful outcomes more likely. Aer executes that circuit and produces classical samples.
>
> The classical stage interprets what those samples mean. Depending on the lock, it solves linear equations, checks a key candidate, reconstructs a period, computes greatest common divisors, or validates a modular relation. It then uses the recovered information in the specified cipher or keystream. Finally, the official Checker compares a hash of the returned plaintext with the expected hash.
>
> That final hash is important, but it does not explain how the answer was found. We keep the quantum measurement and the classical postprocessing connected: the circuit must contribute to the recovery, rather than merely run alongside a classical search.

## 1:45–3:00 — Main quantum algorithms

**Junqi Sheng — quantum circuits and Qiskit**

> The first group of locks turns hidden Boolean structure into interference. Bernstein–Vazirani maps a hidden parity string into phase and recovers the string with Hadamard gates. Deutsch–Jozsa distinguishes a promised constant function from a balanced function. Simon's algorithm samples equations orthogonal to a hidden XOR period; classical linear algebra then solves them. Our BB84 lock instead uses basis matching and observed errors to identify a disturbed channel.
>
> Grover's algorithm addresses the toy-cipher searches. A reversible oracle marks candidates by changing phase, and a diffuser rotates amplitude toward the marked set. The multiple-candidate lock still needs classical checks to select a valid result.
>
> Quantum phase estimation uses controlled powers and an inverse Fourier transform to read phase information. For the factoring locks, modular multiplication turns an order into phases; classical continued fractions and greatest common divisors can then produce factors. For the final lock, two-register Fourier sampling provides relations that can reveal a discrete logarithm after classical validation.

## 3:00–4:15 — Four optimization case studies

**Sicheng Qian**

> For Tier 5, the cipher's S-box and bit permutation are public and invertible. We move their inverses into two public comparison constants. The key-dependent mask is still computed reversibly. The same two-byte condition receives the same phase, and work bits are uncomputed. The proof applies to arbitrary key superpositions when the work and flag start at zero.
>
> For Tier 8, an exact M15 multi-controlled X uses two borrowed lines instead of four. It restores their values and phases, keeps the same readout, and lowers the measured two-qubit count from 49,920 to 42,810.
>
> For Tier 9, adjacent controlled flips sometimes share a predicate. We combine them with a pivot and a reversible fanout. When the predicate is false, the fanout cancels; when it is true, every intended target flips. This exact construction adds no ancilla and preserves relative phase.
>
> Tier 10 reuses that fanout idea. We also absorb the inverse Fourier transform's swaps by reversing the control-wire assignments in both count registers. Because those registers start uniformly, the complete output state is preserved. We keep the measured layout unchanged: the left six bits are Z and the right six are X.

## 4:15–5:15 — Verification and limitations

**Junrui Yu — integration, testing and benchmarking**

> We separate three types of evidence. Mathematical arguments identify the states and phases that must be preserved. Synthetic tests compare controlled operations, amplitudes, auxiliary-bit restoration and measurement mapping. The official Checker then tests the actual submitted recovery path, its hash and the recorded Aer circuit.
>
> Under the recorded scoring settings, the sum of the ten selected two-qubit counts changed from 307,349 in historical v1 to 241,211 in v5: about 21.52 percent fewer. The sum of per-tier depths fell by about 21.14 percent. These are ten separate circuits, and the v1 and v5 records came from different environments.
>
> Fewer scored gates do not guarantee faster simulation. On a same-machine Tier 10 comparison, the gate count fell while solve time rose. Aer is a classical simulator; these measurements do not show a quantum hardware advantage. Fixed-seed success also does not guarantee success for every sample or under noise.

## 5:15–6:30 — Sanitized demo walkthrough and conclusion

**Junrui Yu, then Youyang Shang**

> For a prepared demo, first show the pipeline and a public circuit diagram. Next, show one **synthetic** measurement example and how its bit layout becomes a classical equation. Then show a pass/fail hash result without showing the plaintext or recovered key. Finally, show the v5 resource table and the scoring configuration used to produce it.
>
> In the archived full-package run, the Checker recorded a circuit and matching hash for every tier. We do not need to expose secrets to demonstrate that workflow. The scoring system compares eligible teams on two-qubit gates, depth, total gates and active qubits; shots and classical computation remain separate costs.
>
> Our conclusion is that mathematical structure connects all ten locks, but correctness depends on the whole pipeline. The same proof that supports a circuit simplification must be paired with measurements, classical validation and an honest account of resources and noise. Thank you.

## Likely judge questions and concise answers

1. **Does a matching hash prove the quantum algorithm worked?** No. It verifies the returned plaintext. The circuit must actually execute and its measurement evidence must materially drive recovery; the method also needs review.
2. **What makes the Tier 5 constant folding valid?** The public S-box layer and permutation are invertible, so applying their inverses to the public target preserves each comparison. Exact uncomputation preserves the phase oracle on the clean-work/flag subspace.
3. **How did Tier 8 reduce its borrowed bits?** The complete M15 six-control X replaces the earlier complete template while preserving the exact unitary and returning both borrowed bits, including their coherent phases.
4. **How can Tier 9 share controls without an ancilla?** Consecutive flips have the same predicate. A pivot-to-target fanout, one controlled pivot flip and the inverse fanout reproduce every target flip, with no extra qubit and no relative phase.
5. **Why can't you simply delete the Tier 10 QFT swaps?** The swap is part of the inverse QFT. We also reverse the controlled-power wiring in each register; the proof uses the actual swap-invariant uniform preparation and retains the original output mapping.
6. **What happens to the Tier 10 bit order?** Measurement remains `X_j→c_j` and `Z_j→c_(6+j)`, so the displayed 12-bit key is Z on the left and X on the right. The classical adapter rounds each group without reversing it.
7. **Are Fourier samples always exact?** No. The binary grid need not contain the group frequencies. Off-peak samples can produce incorrect equations, so the recovery path verifies measurement-derived candidates using the public relation.
8. **Do fewer CX gates imply faster Aer runs?** No. Aer can execute native multi-controlled gates differently from the scoring decomposition, and simulation time depends on state width, gate structure, fusion and memory. We report timing separately.
9. **Is the sum of the ten depths one circuit's depth?** No. The Checker selects a circuit per tier. The sum compares ten separate scored depths and is not a single combined circuit or a hardware execution schedule.
10. **What does `full` establish, and is v5 a hardware or competition result?** In the local Checker run, the hash matched and a circuit executed during `solve()`. It is one fixed-seed simulator result, subject to method review. No hardware advantage is established, and the v5 draft has not been uploaded to the competition platform.

Evidence and full derivations: [final analysis](FINAL_QUANTUM_ANALYSIS.md), [official scoring](../SCORING.md), and [v5 integration report](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/41c7c6775b8fc499c2acdd878b4829bd17e1210d/docs/OPTIMIZED_V5_READINESS.md).
