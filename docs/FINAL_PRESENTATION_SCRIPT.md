# Ten Locks — four-speaker presentation

**Delivery:** approximately 6½ minutes at 130–140 words per minute, allowing brief slide transitions. Eight slides; timings are targets, not separately spoken narration. The script contains about 866 spoken words. Present the experiment rows as **individually validated research candidates**, not as the unconfirmed final package. OSC Cardinal is a classical CPU cluster running a simulator. Detailed sources and limits are in [FINAL_QUANTUM_ANALYSIS.md](FINAL_QUANTUM_ANALYSIS.md).

## Slide 1 — The challenge and the plan (0:00–0:40)

**On slide:** Ten locks → quantum circuit → measurement → classical recovery → verified plaintext.

**Sicheng:**

> Our project asks a practical question: how do we turn quantum ideas into circuits that actually recover information, and how do we know the result is trustworthy? We studied ten cryptographic locks, from simple oracle problems to factoring and discrete logarithms. In every case, the quantum circuit produces measurements; classical processing turns those measurements into a candidate, and a hash checks the plaintext. That final hash alone does not prove the quantum circuit did useful work. We therefore track the complete path from the circuit to the answer.

## Slide 2 — Interference and the first four locks (0:40–1:32)

**On slide:** Actual Tier 1 logical circuit, with 24 input wires grouped. The oracle box is the supplied reversible oracle; the target is unmeasured.

```text
24 inputs |0> -- H⊗24 --[ U_f ]-- H⊗24 -- measure q[j] → c[j]
                           |
  target  |0> -- X -- H --[ U_f ]------------------------------
```

**Sicheng:**

> This is our actual Bernstein–Vazirani circuit at the logical level. The lower wire is prepared in the minus state. The oracle converts its hidden parity function into a phase, and the final Hadamards turn that phase into the hidden string. Deutsch–Jozsa uses the same interference idea to distinguish a constant function from a balanced one, assuming the stated promise. Simon's algorithm produces bit strings orthogonal to a hidden XOR period; we solve those measured equations over the binary field. BB84 is different: matching preparation and measurement bases provide correlated bits. In the simple random intercept–resend model, the expected error rate among sifted bits is twenty-five percent; a finite sample fluctuates.

## Slide 3 — Search, phase and order (1:32–2:43)

**Sicheng:**

> Tiers five and six use Grover search. The oracle marks keys that satisfy a public condition, and a diffusion step amplifies their probability. If there are M marked items among N, the ideal number of queries is proportional to the square root of N over M. Our sixth tier estimates the marked population with a measured pilot and verifies only measured candidates. Quantum phase estimation uses controlled powers of a unitary and an inverse quantum Fourier transform to estimate its phase. A phase that appears global before control becomes observable after control, so preserving it is essential.

**Junqi:**

> In Shor's factoring circuit, the unitary is modular multiplication. Measurements estimate fractions related to the order of the chosen base. Continued fractions and modular checks recover an order candidate, and a suitable even order gives factors through greatest common divisors. Some samples or bases are unhelpful, so validation and bounded retries are part of the algorithm.

## Slide 4 — Exact synthesis in Tiers 8 and 9 (2:43–3:33)

**On slide:** Separate candidate comparisons: Tier 8 **42,792 → 33,904** two-qubit gates; Tier 9 v2 **89,075 → 55,999**. Show 18 → 18 and 21 → 22 active qubits, respectively.

**Junqi:**

> Our main circuit cost is controlled modular multiplication. For Tier eight, we synthesize the same public permutation using fixed-mask elimination or a cycle-anchor construction. For Tier nine, we simplify fixed-mask synthesis and share control logic across target flips. In both cases the complete mapping must remain correct, including encoded states outside the modulus. Temporary workspace must be restored, and relative phases must be preserved. In independently measured candidates, Tier eight falls from forty-two thousand seven hundred ninety-two to thirty-three thousand nine hundred four two-qubit gates, at eighteen active qubits. Tier nine falls from eighty-nine thousand seventy-five to fifty-five thousand nine hundred ninety-nine, using twenty-two rather than twenty-one active qubits.

## Slide 5 — Validation and the cost of extra qubits (3:33–4:28)

**On slide:** Tier 8 and Tier 9: OSC 10/10 paired PASS. Tier 9 mean solve 28.23 → 36.10 s. Tier 5 clean candidate: 13,802 2Q, 22 qubits; 10/10 seeded solves over 120 s.

**Youyang:**

> We checked more than the final plaintext. We compared controlled permutations on their complete small domains, checked phase and workspace behavior, and ran the unchanged official Checker. On OSC Cardinal, a classical CPU cluster, both Tier eight variants passed ten paired trials. Both Tier nine variants also passed ten, but the candidate's mean solve time increased from about twenty-eight to thirty-six seconds. Ten successes do not prove zero future failures. Tier five shows why this distinction matters: a twenty-two-qubit clean-ancilla candidate had only thirteen thousand eight hundred two two-qubit gates, but all ten seeded OSC solves exceeded the official two-minute limit. A separate unseeded check did pass near the limit. We rejected that candidate for integration under those conditions.

## Slide 6 — Discrete logarithm and final integration (4:28–5:22)

**On slide:** \(A=g^a\); \(f(x,z)=g^xA^z\); Fourier samples: \(v\equiv au\pmod r\). Tier 10 v2: **82,804 → 46,910** two-qubit gates; depth **218,263 → 109,763**; 19 qubits.

**Junrui:**

> Tier ten uses two Fourier registers to find a discrete logarithm. If the public value A equals g to the power a, the function g to the x times A to the z has a hidden linear relation. The measured Fourier frequencies give equations involving a. Finite register precision can produce partial or inconsistent equations, so we verify measurement-derived candidates against the public group relation before deriving the shared secret. Our independently accepted Tier ten candidate reduces two-qubit gates from eighty-two thousand eight hundred four to forty-six thousand nine hundred ten, with nineteen active qubits. Its full prepared state was independently compared with the baseline. These are candidate results; the exact final frozen package still needs confirmation.

## Slide 7 — Scaling and physical noise (5:22–6:07)

**On slide:** Queries ≠ compiled gates ≠ simulator runtime ≠ hardware performance.

**Youyang:**

> Gate count, depth and runtime answer different questions. Fewer gates do not automatically make classical simulation faster: a generic statevector doubles in size with each additional qubit, and the simulator may use a different native circuit from the scored circuit. Our public permutation-table synthesis also grows exponentially with the work-register width; it is a toy compiler, not scalable modular arithmetic. A real quantum computer adds connectivity constraints, imperfect gates, readout errors and decoherence. A smaller circuit may help, but only calibrated noise studies or hardware runs can establish a physical benefit. OSC is not a quantum computer.

## Slide 8 — Conclusion (6:07–6:40)

**Sicheng:**

> Our contribution is a chain of evidence: mathematical structure, exact reversible circuits, measurement-driven recovery and independent checks. We improved several scored circuits, but we also kept runtime and reliability visible when they moved in the wrong direction. The remaining release step is to match every claimed final metric to Junrui's exact frozen package and rerun the full Checker. That is how we turn a promising optimization into a defensible result.

---

## Five likely judge questions

1. **Why does a correct hash not prove quantum recovery?** A classical search could obtain the same plaintext while an unrelated circuit runs. Our evidence links measured outcomes to equations, order candidates or measured keys, then applies public validation and decryption. The hash verifies the end result, not the recovery pathway.
2. **Why can fewer two-qubit gates run more slowly?** The scored basis is not necessarily Aer’s native representation; wider statevectors, instruction mix, memory and compilation all matter. Tier 9 v2 reduced scored gates but was slower in the measured OSC sample.
3. **How do you know your optimizations preserve quantum phases?** The synthesis uses exact reversible controlled operations and restores workspaces. We combine full-domain complex block comparisons, inverse checks and compositional reasoning. Clean-ancilla claims require the ancilla to start in zero; we do not claim a full dense operator test for every large circuit.
4. **Does this break real RSA or Diffie–Hellman today?** No. Shor's algorithms have favorable asymptotic quantum complexity with efficient reversible arithmetic and sufficient fault-tolerant resources. These tiny instances use exponentially sized public lookup tables and noiseless classical simulation, not a scalable physical attack.
5. **Are these your final competition scores?** No. Simplicity is relative to eligible teams, and several numbers come from separate candidate branches. The frozen v5 report is verified, but the exact later final package has not been identified and checked. Finite OSC runs do not predict competitors, hardware performance or future success probability.

## 30-second backup conclusion — Sicheng

> We used interference, measurement and classical recovery to tackle ten cryptographic locks. Exact reversible synthesis reduced the scored cost of several candidate circuits, and independent checks tested the underlying mappings, phases and returned answers. But gate savings are not automatically simulation speed or hardware speed: one smaller Tier five candidate exceeded the time limit in all ten seeded trials. Our final requirement is to verify every reported number against the exact frozen submission, while keeping these toy demonstrations separate from scalable, fault-tolerant quantum computing.
