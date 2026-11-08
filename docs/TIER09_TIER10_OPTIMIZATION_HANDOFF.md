# Tier 09 / Tier 10 mathematical optimization handoff

## Scope and reference

Implementation reference: `integration/optimized-v2-candidate@0cd8adc025e89fa190836e9295f6b5ffa482e17a`. The mathematical plan on this branch and the earlier `docs/CIRCUIT_OPTIMIZATION_AUDIT.md` at `optimization/circuit-audit@5390daf` have already developed the theory; this document turns their strongest candidates into an implementation and acceptance contract. The audit is not present in this branch or the stable reference. This is a design handoff, not an implementation or a new official benchmark. Do not modify circuit implementations, the official Oracle, Helper, Checker, challenge data or frozen releases as part of this handoff.

The stable reference's measured results, from its integration reports, are Tier 9: 117,739 two-qubit gates, depth 316,820, total gates 349,949, 21 active qubits; Tier 10: 107,168, 287,674, 317,957, 19 respectively. These are historical results under the recorded environment, not measurements of the proposed circuits. Both previously achieved `full`. Compare against a rerun of the same reference and environment before making a performance claim.

## Tier 9: share an exact control predicate in consecutive gates

**Bottleneck and choice.** `tier09/modular.py` forms the full 128-label permutation by positive-control row elimination and reverses the self-inverse X operations. The external phase bit is added to every gate. Fourteen controlled-power blocks act serially on seven work bits, with no ancillary qubit; cached gate construction and native Aer MCX already exist. Use a single dedicated clean bit for strictly consecutive gates with the same complete predicate and distinct targets. Do not reorder gates in the first implementation. A read-only scan of the exact stable compiler, public N=77, base 2 and its 14 powers found 964 such windows of length at least two, containing 2,448 of 4,564 native controlled-X operations. This is a structural opportunity, not a gate or runtime saving; windows of length two in particular may cost more. It does not calculate an order or use it to select a circuit.

**Implementation pseudocode** (chronological order; retain the existing operation list and controlled-power labels):

```text
allocate one b, initialized |0>, outside all controls and targets
for each controlled multiplier, in its existing order:
    i = 0
    while i < len(ops):
        mask, target = ops[i]
        f_controls = [external_control] + work_bits_in(mask)
        j = i + 1; targets = [target]
        while j < len(ops) and ops[j].mask == mask
              and ops[j].target not in targets:
            targets.append(ops[j].target); j += 1
        # every target must be outside f_controls; b is disjoint
        if len(targets) >= 2 and exact_candidate_is_selected:
            exact_MCX(f_controls, b)       # A: b ^= f
            for t in targets: CX(b, t)     # B
            exact_MCX(f_controls, b)       # A† = A; restore b
        else:
            emit original gates ops[i:j], each with external control
        i = j
```

Select windows only from the public gate sequence, by an explicitly recorded deterministic cost comparison under the pinned compiler. Start with all-original fallback and compare candidate selections using the complete actual execution circuit and official scoring configuration. The A gates may themselves use a proven exact synthesis appropriate to its controls and available resources; neither may silently require further unprovided ancillas. Handle zero work controls as a CX from the external control; identity permutations and empty lists are valid. Retain separate quantum applications for equal multipliers on distinct phase bits. Cache only immutable templates, with the ancilla wire included in their interface; caching saves construction, not quantum gates. If no selection improves the chosen score-relevant metrics without unacceptable regressions, retain the reference.

**Proof and contract.** Let `f` be the AND of the external bit and mask bits. Targets are distinct and outside the controls, so no target changes `f`; the original product maps each `y_t` to `y_t XOR f`. Starting with `b=0`, A, B, A maps `(b,y)` to `(0,y XOR f)` exactly. All gates must be exact permutation matrices with phase +1, so this equality holds linearly for arbitrary entangled controls/work, including external control in superposition, and b decouples and returns to zero at every window and block boundary. In particular f=0 gives identity and f=1 gives the original gates, without an uncontrolled relative phase. This is **clean-subspace equivalence**, not `U ⊗ I` on arbitrary b: when b starts at 1, the target result differs. Never borrow an unknown, entangled phase/work bit as this clean bit. A dirty-bit alternative requires the separate chronological sequence B, A, B, A; it restores arbitrary b and implements the same targets, but has twice the CX fanout and needs its own cost measurement. Do not replace MCX with a relative-phase variant unless the full composite, including both external-control branches, has separately been proved exactly equal; a truth table or equality up to a block global phase is insufficient.

By induction, each replacement preserves the full modular permutation on all 128 labels, including fixed 77–127 padding, with a clean b. Consequently all controlled powers, the work/control entanglement, inverse QFT state and the complete phase-estimation distribution, including tails, remain exactly the same. Statevector equality is literal complex equality in the specified basis, not merely matching probabilities. Keep the base, phase-register size, bounded sampling, measured-order recovery, minimality checks, nontrivial GCD and RSA path unchanged.

**Costs and alternatives.** A window of k original MCXs becomes two exact predicate MCXs and k CXs, plus one allocated active qubit when used. Two-qubit count, total gates and depth can decrease or increase after synthesis and scheduling; fanout is serial on b, and the extra active qubit and simulation memory are costs. Native MCX counts, cached construction time and basis-gate score are different measures. Compare also the original circuit with exact one-clean-ancilla MCX decomposition on individual gates, but only if its documented input/output and full phases are verified; do not assume a library version's synthesis or savings. Neither path guarantees improvement.

The public permutation can instead be decomposed into cycles, then each cycle into transpositions, with each endpoint transposition synthesized by a Gray path of h one-bit edges forward and h-1 backward. The interior, including any padding visited, is restored; use exact externally controlled adjacent swaps, including negative-control normalization. This yields the full permutation if cycle orientation and gate order are correct. It is a valid comparator, not the first implementation: the audit already compared the older Gray compiler to the positive-control implementation, and path/cycle costs and actual basis synthesis need fresh measurement. Do not use cycle lengths to learn an order, factor, choose a base or generate an answer. A block and its exact inverse can cancel only when adjacent, on identical wires and with identical controls, or after a proved commutation; different phase controls do not generally cancel, and equal cached blocks are not inverse cancellations. Preserve the current query-accounting assertions unless an explicitly reviewed semantic change updates them truthfully.

## Tier 10: reuse exact synthesis and absorb inverse-QFT swaps

**Bottleneck.** `tier10/circuit.py` builds two six-bit controlled-power series for public g and A on the same seven-bit work register; the shared Tier 9 compiler and a cache across both series already exist. The two series serialize on work, and the QFT is a smaller part of the cost. Keep g and A as separate public inputs; never derive a hidden discrete logarithm to build the circuit. The measured result drives candidate generation and `pow(g,a,p)==A` verification.

**Controlled multiplication and ancilla.** Reuse the Tier 9 clean-window compiler unchanged, with the same dedicated b passed through every block of both series. Initial b=0 and restoration after each window make reuse valid even while X, Z and work are entangled. Include b in the enclosing circuit, cached-gate wire map and actual Aer input; do not allocate a fresh bit per multiplier. External controls remain the appropriate X or Z bit for each power. The same induction proves the whole controlled exponent mapping on the clean subspace, including every padding state, and therefore the joint output distribution. Measure Tier 10 independently; Tier 9's structural counts or score change do not transfer.

**SWAP absorption pseudocode** (apply as a separately switchable change, including when no ancilla optimization is selected):

```text
# t = 6; S reverses each register; D is the existing inverse-QFT body
prepare work=1 and H on every X[j], Z[j]
for (base, register) in [(g, X), (A, Z)]:
    for j in 0..t-1:
        d = pow(base, 2**j, p)
        append exact controlled_M_d on [register[t-1-j], work, optional_b]
        retain truthful public exponent 2**j in the outer block label
append existing inverse-QFT body D (CP and H sequence, no initial SWAPs) to X
append the same D to Z
measure X[j] -> c[j], Z[j] -> c[t+j], unchanged
```

`build_exponent_mapping` currently promises a standalone exact map on its input registers. Do not silently change that API: use a separate wiring option or wrapper in `build_qpe_circuit`, with an explicit interface and tests. Similarly leave the shared `build_inverse_qft` contract intact; factor or copy the exact body locally with its negative angles and order preserved.

**Proof and scope.** Let S reverse both count registers, U be the original controlled-multiplication sequence, and the existing full inverse QFT be `D S`, with operators written right-to-left. Rewiring every power gives `U' = S U S` on the entire register. The initialized count state is `|+>^(2t)`, so `S|ψ₀> = |ψ₀>` even with work initialized independently to |1> and b to |0>. Thus `D U'|ψ₀> = D S U S|ψ₀> = D S U|ψ₀>` as a complex final state on the same physical wires. This is a preparation-scoped equality, not an arbitrary-input identity for dropping S. The proof includes both controls, their joint distribution, work and clean ancilla. It does not justify dropping swaps alone, reversing the output strings, changing phase angles, or moving controls without reversing their power assignments. Measurement remains one register, displayed `z5…z0 x5…x0`; X is low six bits. Preserve `((82*y+64)//128)%41`, the `((-v)%41,u)` convention, candidate verification, bounded sampling and the classical interface.

The explicit six SWAPs disappear, but any basis-gate, depth or total-gate savings depend on the compiler's existing layout, cancellations and scheduling. Active qubits should remain unchanged for this change alone, subject to measurement; the clean-bit candidate can add one. No numerical improvement is asserted. Consider clean-window synthesis and QFT rewiring independently and together so regressions are attributable. An identity public multiplier can be skipped mathematically, but the existing named-block accounting expects every power; retain it in this first change rather than inadvertently invalidating the execution checks.

## Minimal synthetic validation and acceptance

Run against a clean copy of the stable reference with pinned Qiskit/Aer and fixed seeds; record version, commit, commands and results. Use only synthetic public parameters for the following tests. These are proposed tests, not results of this documentation work.

1. **Predicate window:** exhaustively test a small example with external control, two predicate bits, two targets and b. Compare complex output amplitudes for all control/work basis states with b=0; include f=0, f=1, both target values, an external-control superposition and an entangled reference. Assert b returns to zero. Test b=1 as a negative test for the clean construction; if testing the optional dirty sequence, compare all b=0/1 inputs and a b-reference entangled state. Check exact amplitude phase, not only basis labels or equality up to independent branch phases.
2. **Full multiplier:** with synthetic modulus 5, width 3 and a coprime multiplier 2, compare original and candidate controlled operators on every work label and both control values with b=0; explicitly include padding 5–7, identity multiplier, empty/no-window paths and inverse round trip. Check all complex columns at a common phase of +1 and a superposition across control branches. Check b after every block and when reused. Include a synthetic cycle crossing Gray-path padding if evaluating the alternative; verify full permutation and phase. Reject non-coprime multipliers.
3. **Tier 9 circuit:** use a small synthetic coprime modulus and phase register; compare the exact unmeasured final state including work and b=0, then the entire count probability vector, not just peaks or a successful factor. Verify unchanged power labels and `qj -> cj` mapping. Compare original, shared-window and fallback cases.
4. **Tier 10 circuit:** use a small synthetic group with asymmetric X/Z outcomes and nontrivial A, plus identity A and widths 1 and odd/even widths to exercise reversal. Compare original and rewired complete complex final states before measurement (including work and b); compare every joint count probability after measurement, not just marginals. Explicitly test unequal X/Z bitstrings, leading zeros, `qj -> cj`, finite-grid rounding and both control series. Repeat with the clean-window candidate enabled and disabled. Add a negative test showing that removing swaps alone fails on an asymmetric input. Exercise repeated multipliers under distinct controls and reuse b across both series.
5. **Performance:** execute the same `solve()` paths and shots/batch limits on baseline and candidate; capture all Aer-submitted circuits, score the one with largest transpiled two-qubit count, breaking ties by depth. Use `rz,sx,x,cx`, all-to-all, optimization level 1, seed 12345, no initial layout; report the four metrics, shots, batches, logical powers, preprocessing and transpilation time, simulation time and peak RSS separately. The 120-second solve timeout and separate 120-second scoring-transpilation budget apply to each tier; the latter covers all unique circuits for that tier. Recheck native Aer support and memory with the pinned versions. A lower standalone gate count or a faster builder is not an official score improvement.
6. **Official Checker:** in a renamed temporary team directory with all required dependencies, run `python -B tools/check_submission.py <team-copy> --out <report-dir>` using the unmodified official Checker and data, following the stable Tier 9 and Tier 10 integration reports' copy commands. Require `full`, matching plaintext SHA-256, recorded actual Aer execution that materially supplies the factor/order or exponent, valid four metrics and no timeout; inspect any review flag and explain construction, measured evidence and classical postprocessing. A flag alone is not automatic failure. `--metrics-only` still invokes `solve()` and cannot establish hash acceptance. Keep actual secrets, measured witnesses and plaintext out of shared reports. Retain quantum measurement-derived order with minimality and GCD checks for Tier 9, and measurement-derived exponent plus public relation verification for Tier 10. No classical factoring shortcut, exponent brute force, lookup table, hard-coded hidden value or unrelated Aer circuit is acceptable.

The official scoring pool requires full credit and valid metrics; its ratios are relative to eligible teams, with weights 40% two-qubit gates, 30% depth, 20% total gates and 10% active qubits. A tradeoff across metrics has no predetermined score without competitors' results. Tier 9 and Tier 10 supply no dedicated Oracle or Helper: public small-modulus permutation construction is allowed if explained, but it must remain part of a genuine Aer computation during `solve()`. See [Tier 9 rules](../tier09/README.md), [Tier 10 rules](../tier10/README.md), [challenge rules](../CHALLENGE.md), [scoring](../SCORING.md), and [official settings](../tools/scoring_config.yaml).
