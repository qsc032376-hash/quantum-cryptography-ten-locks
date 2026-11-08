# Tier 10 QFT and shared-control prototype

## Scope and reproduction

The isolated experiment is [`experiments/tier10_optimization_prototype.py`](../experiments/tier10_optimization_prototype.py). It reads the unmodified Tier 10 circuit builder, QFT and classical readout from Git object `integration/optimized-v2-candidate@0cd8adc025e89fa190836e9295f6b5ffa482e17a`, extracting only required source files into a temporary directory. It uses synthetic inputs and does not run the official Tier 10 `solve()` or Checker. It implements the earlier [handoff](TIER09_TIER10_OPTIMIZATION_HANDOFF.md); it does not change the submission.

From the repository root, with the reference commit available locally and Qiskit 2.6.1 installed:

```bash
python -B experiments/tier10_optimization_prototype.py
```

Observed: **5 tests passed** with Qiskit 2.6.1, Python 3.13, using statevectors and operators; the numerical tolerance is `atol=1e-12` and `rtol=0`. This is a small synthetic verification, not an Aer or official Checker run. The experiment uses no locked challenge data. NumPy and Qiskit are needed; Aer is not needed for these unitary simulations.

## Absorbing the inverse-QFT swaps

The verified builder's inverse QFT starts with a bit-reversal SWAP network, followed by the negative-angle controlled-phase/H body. Calling the network S and the body D, the inverse QFT is `D S` in right-to-left operator notation. For both X and Z registers, let U be the existing controlled modular-power map. Reverse each register's control wiring to implement `U' = S U S`, keep D unchanged, and measure physical `qj -> cj`. Because the actual count preparation is invariant under S, `D U' |+,+,1> = D S U |+,+,1>`. This is exact state equality including work and complex phase, hence equality of the full joint measurement distribution. It is preparation-scoped: for a generic input ψ the relationship is `D U' S ψ = D S U ψ`; do not call the two circuits identical on the same arbitrary input.

The experiment builds the real reference `build_exponent_mapping` using public synthetic parameters `p=5, g=2, A=4`, three work bits and counting widths 1, 2 and 3. It reverses the X and Z wire lists only for the mapping, then uses D with no swaps. Both versions initialize work to 1. The tests compare **all** `2^(2t)` count-register basis states for each width, with the optimized input first bit-reversed as the general identity requires; they compare every complex output amplitude and every count-register marginal probability. The standard all-plus preparation is compared on the same input for each width. An additional asymmetric complex superposition tests the general, relabeled-input identity. This exercises both register blocks and work entanglement; it is not a full six-bit instance or an exhaustive test of all work inputs. A deliberately incorrect version that simply removes swaps while leaving controls unchanged fails both complex-state and probability comparisons.

For widths 1–3, the full reference and experimental inverse-QFT matrices are independently checked against `exp(-2πi x y / 2^t)/sqrt(2^t)`. This verifies the negative sign and the gate order, not just a bitstring convention. In the prototype, D applies, chronologically, CP with angle `-π/2^(j-i)` for `i<j`, then H on j, exactly like the reference.

### Measurement and classical interface

A separate six-bit-per-register synthetic Fourier-phase circuit prepares asymmetric peaks X=13 and Z=26, relabels its inputs, applies D, and checks the exact probability-one result `011010001101`. Measurement instructions are explicitly checked as `qj -> cj`; hence the high six characters are Z and low six are X, without a post-readout reversal. This is an interface fixture, not a six-bit full modular-exponentiation distribution. It feeds the resulting key to the actual stable `measurement_from_counts()` and `decrypt_from_counts()` with an independently constructed synthetic order-5 DH ciphertext. Both decode the same witness `(3,1)`, and decryption returns the synthetic plaintext. The fixture uses the documented half-up rounding and `(-v mod r,u)` sign convention. A successful witness alone does not establish circuit equivalence: the complex-state and full-distribution checks above provide the separate evidence.

In the actual finite-grid algorithm, off-peak counts can imply incorrect or inconsistent equations. The stable `solve()` ranks measurement-derived candidates and verifies a public relation before passing a single verified witness to its classical path. This example does not justify feeding an arbitrary batch of raw counts directly into `decrypt_from_counts()`, which merges equations.

## Shared-control reversible example

The toy circuit has external control c, work controls a and b, three distinct targets and one clean auxiliary q. The original uses three exact `MCX(c,a,b; target)` gates. The candidate applies:

```text
MCX(c,a,b; q)
CX(q, target_0); CX(q, target_1); CX(q, target_2)
MCX(c,a,b; q)
```

For `q=0`, the predicate `f=c∧a∧b` is unchanged by the targets, each target is toggled by f and q is restored to zero. Exact permutation matrices give phase +1 on both control branches. The test compares **every complex matrix column** for all 64 data inputs with q=0, plus a state in which a reference is entangled with a control and a target; it checks the auxiliary's reduced state is `|0><0|`. A negative test confirms that the construction is not equivalent for arbitrary q=1. The auxiliary must therefore be initialized clean and restored before reuse, and its control and target sets must remain disjoint. Relative-phase MCX replacements require a separate composite phase proof.

This is a local controlled-unitary window, not a complete modular multiplier. The actual Tier 10 builder invokes the Tier 9 positive-control compiler separately for each public power. This replacement can apply only where its chronological gate list has the same full predicate, including the relevant X or Z control, and distinct targets outside that predicate. Reuse one clean auxiliary only after restoration. Repeated public multipliers controlled by different register bits remain separate operations. No Tier 10 window count or full-scale saving has been measured here.

## Resource measurements

All four circuits were transpiled with the same Qiskit 2.6.1 settings: basis `rz,sx,x,cx`, all-to-all, optimization level 1, seed 12345, no initial layout. Counts and depth exclude measurement because these prototype circuits are unmeasured. Active means touched by a transpiled gate. The full QFT examples include the same actual synthetic modular mapping, work preparation and two count registers. The predicate-original example has six allocated qubits; the shared version adds the seventh clean qubit. This prevents the compiler from borrowing a spare clean wire in the original resource comparison.

| Prototype | CX / two-qubit | Total gates | Depth | Active qubits |
| --- | ---: | ---: | ---: | ---: |
| Two-register toy, full inverse QFT | 198 | 480 | 355 | 7 |
| Same toy, rewired and no QFT swaps | 192 | 468 | 350 | 7 |
| Three original MCX gates | 38 | 104 | 80 | 6 |
| Shared predicate with clean auxiliary | 29 | 77 | 56 | 7 |

These are measured small-circuit results, not Tier 10 scoring improvements. Basis decomposition, available ancillas, neighboring-gate cancellation, wire placement and scheduling affect the figures. In particular the extra active qubit has a scoring and statevector-memory cost, and a two-target window need not save anything. Actual inverse-QFT SWAP removal gives a logical opportunity, but the official compiler may already absorb or alter its cost. Do not extrapolate either difference numerically to the 19-qubit circuit.

## Full-scale handoff and risks

Recommend Junqi first implement SWAP absorption behind a separate experimental option in the complete six-bit X/Z circuit, preserving the standalone `build_exponent_mapping` and shared `build_inverse_qft` contracts. Reverse the control wire assigned to every `2**j` power in **each** register, retain the power labels, CP angles, one-register `z5…z0 x5…x0` measurement mapping and existing classical readout. Compare the complete joint distribution, including tails, against the reference on synthetic parameters and selected complex states before testing challenge data. Keep the reference as fallback.

Then Junqi may try the clean-predicate rewrite only on qualifying consecutive windows of the actual compiler, with a single explicit auxiliary wire in the full circuit and cached gate interface. Verify control-0 and control-1, complex phase, all work labels and fixed padding, clean restoration and reuse across both registers. Compare the unchanged, QFT-only, shared-only and combined versions. Check compilation time, memory and hardware/native MCX handling separately from basis-gate counts. Junrui should verify high/low register mapping, rounding and measurement-derived candidate validation on asymmetric synthetic examples and then conduct a separate official acceptance run when implementation is ready.

Full acceptance requires an actual circuit executed on Aer during `solve()` that materially produces the measured exponent, correct plaintext hash, and valid metrics. Official scoring measures the largest actually executed circuit by transpiled two-qubit gates (depth breaks ties), under the [fixed configuration](../tools/scoring_config.yaml), with solve and scoring-transpilation time limits; `build_circuit()` alone is not scored. The official [Tier 10 rules](../tier10/README.md) allow an explained public permutation construction but prohibit classical discrete-log search or lookup. `full` plus valid metrics is needed for simplicity eligibility; shots, batches and preprocessing are separate costs. No full Checker was run for this research.
