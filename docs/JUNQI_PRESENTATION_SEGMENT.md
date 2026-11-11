# Junqi Sheng — 90-second quantum technical segment

Prepared 2026-11-11 for `release/ten-locks-v6-rc@c4455782ea9388d5897fc27270f42dd3786ed35d`. This is Junqi's technical segment, not a replacement for Sicheng's full Team 3 presentation. Numerical and mathematical sources are indexed in [the final technical review](JUNQI_FINAL_TECHNICAL_REVIEW.md).

## Speaking script

Read the following four paragraphs only: **202 words, about 90 seconds at 135 words per minute**. Timing is a delivery estimate, not a recorded rehearsal. Keep the exact metric table below visible; avoid reading every depth and total-gate entry aloud.

<!-- SCRIPT_START -->
In Tiers eight and nine, we use Shor's quantum order finding for moduli thirty-five and seventy-seven. We prepare the work register as one, apply controlled modular powers, then Fourier measurement. Measured frequencies supply candidate periods; classical validation and greatest common divisors recover factors.

We optimize the reversible permutations, not the answers. Tier eight combines fixed-mask elimination with better cycle anchors. Its two-qubit count falls from forty-two thousand seven hundred ninety-two to thirty-three thousand nine hundred four. Tier nine uses global fixed-mask synthesis, reducing eighty-nine thousand seventy-five to fifty-five thousand nine hundred ninety-nine. Depth falls about twenty-two and forty-nine percent, respectively. Tier eight keeps eighteen qubits; Tier nine uses twenty-two instead of twenty-one, including a clean synthesis ancilla.

Our argument covers control-off branches, padding states, relative phases and restored auxiliary state. Exhaustive small-block tests and complex-operator comparisons support it. Paired simulator trials and plaintext hashes check recovery, but hashes alone do not prove unitary equivalence.

Fewer gates do not guarantee faster simulation. Tier nine passed ten paired OSC trials but took longer on average; its original benchmark label remains INCONCLUSIVE. These are Aer simulations, not hardware results. Public permutation-table synthesis also grows exponentially, so this toy implementation does not demonstrate practical cryptographic speedup.
<!-- SCRIPT_END -->

## Slide / speaker reference — do not read every number

| Accepted comparison | Two-qubit gates | Depth | Total gates | Active qubits |
|---|---:|---:|---:|---:|
| Tier 8, preceding baseline → hybrid | 42,792 → 33,904 | 123,300 → 96,055 | 130,171 → 102,561 | 18 → 18 |
| Tier 9, v5 → approved v2 | 89,075 → 55,999 | 235,048 → 120,242 | 263,601 → 168,116 | 21 → 22 |

Suggested pacing: algorithm 0–20 seconds; transformations and metrics 20–54; correctness 54–72; limitations 72–90. Rehearse aloud and adjust pauses, without removing the runtime or scaling qualification. T8 comparisons use source `0988ac4` → `b92a17f`; T9 uses `41c7c67` → `00fee41`.

If asked about Tier 10: accepted v2 uses two six-bit Fourier registers and seven work qubits to sample the subgroup relation for `g^x A^z`. It shortens exact positive-control predicates. Its RC metrics are **46,910 2Q / 109,763 depth / 132,023 gates / 19 qubits**, compared with **82,804 / 218,263 / 245,153 / 19**. The 64-point grid must be rounded to the public order 41 before forming candidate equations. Production validates only measurement-derived candidates against `g^a=A`; it does not enumerate exponents. Do not cite unaccepted Tier 10 v3's 46,038 gates or claim that v2 accelerated Aer.

## Five likely technical judge questions

### 1. How do you know the optimized permutation is equivalent?

The row-elimination invariant fixes each output row while preserving every earlier row. Reversing the self-inverse gates therefore implements the complete original permutation, including padding. Changing the cycle anchor gives a different transposition sequence implementing the same cycle. Adding the external control preserves both control branches. We also check complex amplitudes and auxiliary restoration, not just bit outputs: Tier 8 has independent full 512-by-512 controlled-block comparisons, with error below 3e−13. Tier 9 has independent exhaustive basis checks, small complex operators and clean-subspace tests. These support a compositional argument; we do not claim an exhaustive dense operator for the whole 22-qubit circuit. SHA-256 only checks the recovered plaintext.

### 2. Why did Tier 9 need an extra qubit?

We chose an extra zero-initialized workspace so exact MCX synthesis could trade one qubit for substantially fewer gates. The actual circuit passed to Aer includes it. Native MCX simulation leaves it idle; official basis synthesis can use and restore it, making 22 qubits active in the scored circuit. The contract is `V(|ψ⟩|0⟩)=U|ψ⟩|0⟩`; we do not claim correctness for an arbitrary dirty initial state on that clean wire. This was an engineering tradeoff, not a mathematical lower bound or a free resource.

### 3. Why did fewer gates not always produce faster simulation?

The score counts gates after official decomposition, while Aer can execute native MCX operations. Width, gate representation, compilation, threading and machine load all affect CPU time. In the paired Tier 9 OSC record, mean solve time rose from 28.2307 to 36.0989 seconds, about 27.87%, despite fewer scored gates. All ten pairs passed, but the original overall benchmark label remains INCONCLUSIVE. We claim a circuit-resource improvement, not a runtime improvement. Tier 8's observed timing improvement is also specific to its measured configuration.

### 4. Does this approach scale to realistic cryptographic keys?

Not this compiler. It explicitly constructs a public table with `2^w` entries and performs table-wide elimination and synthesis choices. That classical preparation grows exponentially with work-register width; toy postprocessing also has bounded, small-instance choices. Shor's scalable algorithm instead needs efficient reversible arithmetic plus a suitable fault-tolerant implementation. Our Aer experiments demonstrate the algorithmic mechanism and exact local optimizations at challenge sizes, not practical RSA or Diffie–Hellman cryptanalysis, hardware advantage or an unconditional speedup.

### 5. How do you distinguish genuine quantum computation from classical answer extraction?

Trace the data dependence. Factoring candidates come from measured Fourier frequencies, continued fractions and bounded combinations; only then do modular-order checks and GCD produce factors. Tier 10 candidates come from actual two-register counts, rounded frequency equations and bounded public-relation checks. The classical compiler receives public parameters only and emits reversible gates; it does not send factors, periods or exponents to recovery. There is no hidden-answer lookup or brute-force fallback. This is genuine quantum-circuit computation **simulated on a classical CPU**, not an assertion that the computer itself is quantum. End-to-end hashes alone would not establish this causal path.

## Final accuracy reminders

- The combined RC's reported 10/10 FULL, matching hashes, valid metrics and zero flags/timeouts remain pending Youyang's independent RC/ZIP audit.
- 369,186 is the **sum of ten per-tier selected circuit depths**, not a combined circuit's depth or execution time.
- Tier 8/Tier 10 have SWAP-absorbed wiring; Tier 9 retains its full inverse QFT. Output conventions are unchanged.
- Restore temporary workspace, not the intentionally entangled modular work result. Never substitute an uncorrected relative-phase gate just because basis outputs match.
- Do not disclose actual factors, hidden orders, exponent, key, counts or plaintext during this segment. Use clearly labeled artificial examples if a diagram needs numbers.
- Retain frozen v5 as the fallback. This review does not create a release or sign off the final submission archive.
