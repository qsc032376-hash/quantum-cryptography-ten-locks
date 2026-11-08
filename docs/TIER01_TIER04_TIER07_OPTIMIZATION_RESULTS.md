# Tier 1, 4, and 7 circuit optimization results

## Scope and decision

Baseline: frozen `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d`. This branch changes only the Tier 7 QPE builder and adds a synthetic test. Tier 1 and Tier 4 remain byte-for-byte identical to v5. No official Oracle, Helper, Checker, locked input, classical decoder, or other tier was changed. The experiment uses Qiskit 2.6.1, Aer 0.18.2, and the official `rz,sx,x,cx` basis, all-to-all connectivity, optimization level 1, and transpiler seed 12345. The Checker scores the largest actual Aer-executed circuit by two-qubit gates, then depth.

| Tier | Frozen v5 published 2Q / depth / total / active | Same-host v5 Checker | Candidate Checker | Decision |
|---|---|---|---|---|
| 1 | 151 / 44 / 298 / 25 | 151 / 44 / 298 / 25 | unchanged | REJECT: no legal external linear block to improve |
| 4 | 183 / 195 / 455 / 20 | 183 / 195 / 455 / 20 | unchanged | REJECT: no legal external linear block to improve |
| 7 | 230 / 271 / 763 / 15 | 230 / 268 / 758 / 15 | **209 / 265 / 724 / 15** | **ACCEPT** |

The published v5 figures are from the Windows v5 full Checker [record](OPTIMIZED_V5_READINESS.md). The paired Tier 7 baseline and candidate above were rerun on the same macOS Python 3.13 host with identical pinned Qiskit/Aer versions and scoring configuration. The platform-dependent 3-depth/5-total difference in the unchanged baseline prevents treating the published 271 → local 265 as a controlled six-layer reduction. The controlled Tier 7 saving is **21 two-qubit gates, 3 depth layers, 34 total gates, and 0 active qubits**. Across these three independent scored circuits, same-host sums change from 564 to 543 two-qubit gates, 507 to 504 summed depth, and 1,511 to 1,477 total gates. These sums are not one joint circuit. No competition simplicity points can be inferred without other teams' metrics.

## Tier 1: Bernstein–Vazirani

The visible circuit is $H^{\otimes24}$ on the input, applying X then H to prepare the target as $|-\rangle$, one opaque $U_f$, $H^{\otimes24}$ on the input, then $q_j\to c_j$. The eligible *external* linear CNOT block is the identity: its GF(2) matrix is $I_{24}$ and it contains zero CNOTs. No adjacent Hadamard pair exists outside the Oracle. The target preparation is necessary for the phase kickback $X^{s\cdot x}|-\rangle=(-1)^{s\cdot x}|-\rangle$; removing it would change the operation. The only visible CNOT work is within the supplied opaque Oracle. Its hidden implementation is neither inspected nor rewritten. One Oracle invocation and the 24-bit measurement mapping remain intact. An arbitrary input matrix $A\in GL(24,2)$ would require compensating readout $A^{-T}$, add gates, and supply no verified saving. Thus no Tier 1 candidate is retained.

The isolated, renamed-directory official Checker reports `full`, hash match, actual Aer execution, valid metrics, one Oracle call, and `flags=[]` for the unchanged v5 Tier 1. Its same-host solve time was 10.983 s; the two-tier Checker process peak resident memory was 615,661,568 bytes, so this is **not** a separately measured Tier 1 peak.

## Tier 4: Simon

The visible circuit is input $H^{\otimes10}$, one opaque $U_f:|x\rangle|0\rangle\mapsto|x\rangle|f(x)\rangle$, input $H^{\otimes10}$, then $q_j\to c_j$. As in Tier 1, the eligible external CNOT network has matrix $I_{10}$ and zero CNOTs. Output qubits must enter as $|0\rangle$; the unmeasured output register is already traced out by reading only the input. An arbitrary invertible relabeling of input or output would need matched Oracle-interface and equation transformations, with no existing external CNOT block to cancel. Oracle internal CNOTs cannot be treated as an editable known linear network. The measured rows still obey $y\cdot s=0\pmod2$, and the unchanged GF(2) solver derives the nonzero nullspace vector from measured rows. Thus no Tier 4 candidate is retained.

The isolated official Checker reports `full`, hash match, actual Aer execution, valid metrics, and `flags=[]` for the unchanged v5 Tier 4. Same-host solve time was 0.132 s. Simon sampling is finite (32-shot batches, 128-shot cap); one successful run does not guarantee every seed succeeds.

## Tier 7: exact inverse-QFT input reversal

Let $n=14$, $R|b_0,\ldots,b_{n-1}\rangle=|b_{n-1},\ldots,b_0\rangle$, and let $C$ be the negative-angle inverse-QFT core **without** its initial SWAPs. The original inverse QFT is $CR$. Let $P=\prod_{j=0}^{n-1}\Lambda_{q_j}(U^{2^j})$ denote the complete controlled-power block, including every complex scalar of $U$. The existing input preparation is $|+\rangle^{\otimes n}\otimes E|0\rangle$, invariant under $R$ on the first $n$ wires. Define $P'=RPR$; in code, the control for power $2^j$ is moved from $q_j$ to $q_{n-1-j}$. Therefore, for **any** one-qubit $U$ and target preparation $E$,

$$
CRP\bigl(|+\rangle^{\otimes n}\otimes E|0\rangle\bigr)
=CP'\bigl(|+\rangle^{\otimes n}\otimes E|0\rangle\bigr).
$$

This is exact final-state equality, not just agreement of one measured key, and retains relative phases and the controlled global phase of $U$. The identity uses $R^2=I$ and $R|+\rangle^{\otimes n}=|+\rangle^{\otimes n}$; it does **not** claim equality of the two circuits as unrestricted operators on arbitrary input states. The target is not an ancilla, and no new ancilla is introduced. The additional phase-cancellation verification circuit remains executed and unchanged. Measurement remains $q_j\to c_j$, so `c13...c0` is the ordinary integer phase with no bitstring reversal; `measurement_to_phase()` and the classical decryptor remain unchanged. Negative controlled-phase angles in $C$ are unchanged.

Implementation pseudocode:

```text
prepare target E|0>; H on q[0:n]
for j in 0..n-1:
    apply controlled U^(2^j) using q[n-1-j] as control
apply inverse-QFT core C without input SWAPs
measure q[j] into c[j] for every j
```

The original QFT has seven disjoint SWAPs, which decompose to 21 CX gates in the official basis. The measured 21-CX saving matches this structure. The 34-total-gate saving also includes transpiler-dependent one-qubit simplification and is not a standalone mathematical gate identity. Powers of $U$ are still made by repeated squaring of the full complex matrix, without eigenvalue or angle extraction. All 14 controlled powers, the required eigenstate preparation, the 64-shot QPE Aer run, and the 32-shot independent phase-cancellation Aer run remain in `solve()`.

## Equivalence and official evidence

- `tests/test_tier07_qft_relabeling.py`: all computational basis states for inverse QFT widths 1–4; exact operator identity $CR=\mathrm{IQFT}$; full-state amplitude equality for widths 2–4 and synthetic exact-grid phases including a nonzero global phase; non-diagonal $U$ with a superposed target; exact synthetic 4-bit Aer readout `0011` for phase $3/16$ in both forms; identical $q_j\to c_j$ map. All four tests pass. The full-state tests include the target and thus check relative phases. There is no new ancilla to restore.
- Ten paired real-Aer simulator seeds 700–709 on the public Tier 7 instance, 64 shots each, produced identical recovered phases and valid plaintext hashes for v5 and the relabeled QPE (10/10). Secret phases, counts, matrices, and plaintext were not logged. This is finite-seed evidence, not an exhaustive probability test; the algebraic identity supplies the general correctness argument.
- Isolated, renamed-team official Checker: Tier 1 `full`, Tier 4 `full`, and Tier 7 baseline/candidate both `full`; all three hash matches, valid metrics, actual circuits, and empty flags. The accepted Tier 7 keeps two unique Aer-executed circuits; the Checker records the QPE one as the scored circuit. The same-host Tier 7 Checker solve times were 0.101 s baseline and 0.106 s candidate. Separate Checker process wall times were 1.64 s and 1.83 s, with macOS maximum resident set sizes 101,728,256 and 101,253,120 bytes. Such short runs do not establish a runtime or memory improvement. A separate ten-seed 64-shot QPE-only Aer timing gave medians 12.658 ms and 12.392 ms, with ranges 12.361–18.595 and 12.123–13.264 ms; it excludes the additional phase check and is likewise not a speed claim.
- Existing Tier 1 and Tier 7 adapter tests pass (13 cases). No full ten-tier Checker was run because the other seven tiers are unchanged.

## Rejected or unproven approaches

Tier 1/4 external CNOT cancellation, GF(2) resynthesis, and compute/uncompute removal have no nontrivial visible block to act on. Any Oracle-internal rewrite would violate the opaque-interface constraint. Tier 7 omitting SWAPs *without* reversing power controls changes phase order and readout. Inferring a controlled-$U^{2^j}$ phase from eigenvalues or stripping its scalar would risk a wrong relative phase and violate the tier rule. Removing the second phase-check execution was tested as an isolated experiment but rejected: QFT relabeling alone already produces the same scored improvement, while the check provides independent confirmation.

## Integration and limits

Cherry-pick only `submissions/team3/tier07/qpe.py` from this branch into any future candidate; the test is optional for a submission package. Keep `tier07/solution.py`, classical recovery, and every other tier as in verified v5. Re-run the official Checker on an isolated, renamed team directory and confirm `full`, SHA-256 match, valid metrics, and no flags before release. The present branch is an independently checked development candidate, not a new verified ten-tier release. The exact 21-CX improvement is supported on the pinned scoring configuration; other transpilers, connectivity, hardware noise, and random seeds may change resource counts or reliability. Aer simulation is not hardware quantum advantage.
