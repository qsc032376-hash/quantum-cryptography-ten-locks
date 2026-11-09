# Tier 10 structural synthesis v3 research

**Decision: INCONCLUSIVE for integration.** A bounded exact guard-selection prototype improves the actual scored circuit and passes three local paired seeds plus the isolated official Tier 10 check. It adds substantial classical compilation work and the sample is too small to establish reliability comparable to the independently accepted v2. Preserve this as research, not a v6 change; the full integration and broader independent runtime checks remain future work.

## Provenance and architecture

- Accepted v2 reference: `optimization/tier10-v2@be78cc11d6e5e778c2ecfd2d0efa79fe740b3274`. Frozen v5 `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d` was not modified. Tier 8 hybrid reference `optimization/tier08-advanced-v2@b92a17fae7cf14c880e6457bce4f3c339626fc94`; its OSC validation `validation/tier08-osc-cardinal@3dac27e` is separate, not Tier 10 runtime evidence.
- The challenge's public group has modulus `p=83`, generator `g=3`, and supplied generator order 41. The circuit uses two 6-qubit counting registers and seven work qubits, initially work `|1⟩`; for public group element A it coherently computes `g^x A^z * y mod p`. Work encodings 83–127 are fixed. There are 12 independently controlled public multipliers, two inverse-QFT cores, and q[j]→c[j] measurements. The counter-register swap absorption relies on the prepared uniform counting state. Actual discrete log recovery remains measurement-derived; no classical exponent lookup is used.
- Each fixed permutation is synthesized into positive-controlled X gates with short guards and shared-target fanout. These networks encode the modular operation rather than a separate ripple-carry arithmetic circuit. Predicate computation and fanout uncomputation are part of the same gates. The current implementation uses no source-level ancilla; Qiskit may use available count wires during high-level synthesis and must restore them. No proposed candidate adds qubits or removes phase corrections.

## Cost decomposition

Local full double compilation, with solve-time Aer transpilation followed by official scoring, exactly reproduced **46,910 2Q / depth 109,763 / 132,023 total / 19 active**. Environment Python 3.13.9, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4; scoring basis `[rz,sx,x,cx]`, all-to-all, optimization level 1, seed 12345. The scored object is the circuit actually passed to Aer by `solve()`; final measurement is excluded from gate counts.

The 12 actual controlled permutation blocks contain respectively 4,062–5,502 isolated 2Q gates when compiled as eight-qubit blocks. Together they have 495 four-control, 445 five-control, 240 six-control and 70 seven-control logical MCX operations; single-, double- and triple-control gates and fanout CX also contribute. The first block is 4,994 isolated 2Q, depth 9,797. Each inverse-QFT core is 30 isolated 2Q / depth 41 / 93 gates on six active qubits. These are isolated benchmarks, **not additive attribution**: their 59,950-CX sum differs materially from the 46,910 whole-circuit result, because full-context synthesis can exploit other wires and compilation boundaries. [Machine-readable block results](../research/tier10_structural_v3/costs.json).

The official Tier 10 rules allow permutation-based modular unitaries but require a quantum circuit to recover an exponent; no classical enumeration or known-answer lookup is permitted. The public permutation compiler is exponential in work width and is not scalable large-integer arithmetic.

## Bounded techniques screened

1. **Explicit dirty MCX borrowing, rejected.** Tier 8's dirty-MCX technique was applied to each of 1,250 four-to-seven-control operations, borrowing three other count wires and restoring them. Individual MCX templates look cheaper, but the complete circuit measured **46,910 / 109,781 / 132,024 / 19**, with no 2Q improvement and slightly worse depth/total. The same full-context compiler already uses available wires; isolated 2Q counts overstate the benefit. No production file was changed.
2. **Tier 8 cycle anchors, rejected at local screen.** Adapted Gray-path cycle transpositions with three dirty counting wires to representative seven-work-bit multipliers. Their isolated costs were **16,720 2Q each**, versus **4,994 / 4,782 / 4,062** for the corresponding existing exact blocks. An isolated cycle block uses 11 wires including borrowed wires; reusing count wires would remain within the 19-qubit budget, but the much higher local cost did not justify full-circuit or Aer trials. Full encoded domain and external control semantics would remain mandatory for any future use.
3. **Cross-block cancellation, no new rewrite.** Existing v2 evidence checked all ordered boundaries, finding no directly adjacent or commutation-exposable cancellation in current order; different count controls cannot be collapsed just because multipliers repeat. QFT crossing and moving operations across controls were not attempted without a proof. Prior explicit no-ancilla MCX replacement also increased isolated cost. The 20-qubit clean candidate from v2 is outside this task's ≤19 active-qubit budget.
4. **Alternative minimum-cardinality row guards, promising.** Existing `_guard` chooses high bits until the mask protects earlier rows. Several different subsets can have the same minimum cardinality and protect the same row. The prototype tries 16 deterministic ranks among these alternatives for each existing forward/inverse and clear-method synthesis, then selects the lowest existing MCX/fanout cost estimate, including the accepted v2 network as fallback. It does not assume that this estimate equals the whole-circuit score. Four separate whole-circuit screens with 2 / 4 / 8 / 16 choices yielded **46,770 / 46,372 / 46,152 / 46,038** 2Q respectively; the measured 16-choice version is the candidate. `research/tier10_structural_v3/predicate_screen.py` retains the research selector, and `validate.py` appends a wrapper only to a disposable isolated candidate snapshot. No production or v6 file is modified. The wrapper temporarily patches the selector and is appropriate to these isolated single-process tests; a future production implementation should explicitly pass the guard strategy instead of relying on process-global patching and then repeat validation.

## Exactness

For row `r` with current output `y≥r`, select any `m` contained in `y` with `m≥r`. Every value satisfying positive controls `m` is at least `m`, so flips cannot disturb rows below `r`; selected target bits are outside the mask. Each row is fixed by reversible controlled-X operations, so reversing the elimination implements the original full public permutation. Inverse-table synthesis is reversed once more to implement the same forward mapping. Grouped fanout `F·MCX·F⁻¹` is exact, with identical control-off action and no relative phase. The prototype checks all available seven-bit masks and rows for all 16 selection ranks, including the minimum-cardinality property.

`research/tier10_structural_v3/verify.py` independently checked all **256 control/work branches per block for all 12 actual blocks**, including both control states and all padding encodings. It explicitly verifies that every emitted source gate is an exact positive CX/CCX/MCX, then checks a random complex superposition against the analytic permutation and applies the inverse. Maximum observed forward error is **3.23e−14**; inverse reconstruction error **6.40e−14**. The arithmetic comparison and operation semantics give a compositional phase argument beyond the sampled superpositions. The count/work register wiring, 12 named powers, inverse QFT and q[j]→c[j] ordering remain unchanged. No prohibitively large full-system dense operator was constructed. Evidence: `equivalence.json`.

## Actual executed circuit and local validation

The isolated Checker recorded the real circuit used by the candidate `solve()`, not just the diagram builder:

| Metric | Accepted v2 | Candidate | Change |
|---|---:|---:|---:|
| Two-qubit gates | 46,910 | 46,038 | −872 (−1.86%) |
| Depth | 109,763 | 107,877 | −1,886 (−1.72%) |
| Total gates | 132,023 | 129,606 | −2,417 (−1.83%) |
| Active qubits | 19 | 19 | 0 |

All four official Simplicity weights favor or tie the candidate (2Q 0.4, depth 0.3, total 0.2, active 0.1). Other teams' best values are unknown, so no competition score is inferred.

Three paired local seeds, injected and observed at Aer (`1000`, `1001`, `1002`), used 128 shots and one quantum circuit each. Baseline and candidate both passed **3/3** hash and timing checks; no timeout. Each solve used a fresh process. Baseline / candidate solve times were **4.158 / 5.473**, **4.045 / 5.909**, **3.811 / 5.570** s. Mean solve **4.005 → 5.651 s (+41.1%)**; mean sampled process-tree peak RSS **119.35 → 116.67 MiB**, with ranges **118.78–119.64 / 112.81–123.58 MiB**. RSS is 20-ms sampled summed process-tree RSS and may double-count pages or miss peaks; these short runs do not establish a general memory improvement.

The unchanged official `check_tier` was invoked only for Tier 10 against an isolated candidate snapshot: **full**, SHA-256 match, valid metrics, **flags=[]**, one circuit, no timeout; solve **5.985 s**, full worker wall **7.2736 s**, sampled process-tree peak **161.28 MiB**, and candidate metrics match the table. The official solve and scoring-transpile thresholds remain 120 seconds each; the 240-second harness limit covers the wider worker process and does not relax them. Local results and host configuration are in `validation.json`. The baseline's accepted ten-seed reference is documented in `docs/TIER10_ADVANCED_OPTIMIZATION.md`; it is not presented as a ten-seed test of this new candidate. No OSC job or full ten-tier Checker was run.

## Reproduction and limitations

With the stated v2 commit and pinned dependencies available, from this branch run:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_structural_v3/costs.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_structural_v3/screen.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_structural_v3/cycle_screen.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_structural_v3/predicate_screen.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_structural_v3/verify.py
```

`validate.py` requires the sibling benchmark harness checkout at `ab9676749e00da904d0b8076811a2407d3b7205f` and the accepted v2 Git object; it uses isolated Git snapshots and writes safe aggregate JSON. Run it with the same environment variables. The research candidate is defined by the 16-choice selector in `predicate_screen.py` and the disposable wrapper in `validate.py`, not an integrated Tier 10 production source change. Recheck the actual scored circuit after any integration, and run a larger matched-seed reliability and resource study before considering v6; hardware, compiler version, memory sampling and stochastic samples can change conclusions. No frozen release, official Checker/Oracle/Helper, other tier, final submission ZIP, or production v6 was changed.
