# Tier 10 full-scale QFT and shared-control evaluation

## Decision and scope

**B — ACCEPT for this branch.** The default Tier 10 circuit now absorbs both inverse-QFT swap networks by reversing the controlled-power input wires. It keeps the exact output state for the actual preparation, the original readout, and 19 active qubits. **C — EXPERIMENTAL.** An independently selectable implementation in `tier10/shared_control.py` reduces the measured gate counts but increases active qubits to 20 and, on this machine, solve time. It is not enabled by the default `solve()`. Its full Checker run used a temporary renamed team copy with only that copy's builder import changed. **D was not tested:** B is a small independent improvement and C trades an extra qubit and runtime for fewer gates; combining them is a separate experiment, not evidence of a further saving. A remains the unchanged `integration/optimized-v2-candidate@0cd8adc025e89fa190836e9295f6b5ffa482e17a` fallback. This branch starts at that commit and does not merge the prototype branch.

## Transformations and correctness

For each count register, let S reverse its wires, D be the reference inverse-QFT body following the initial swaps, and U be the existing exact modular-power mapping. The reference applies `D S U`; the optimized circuit applies `D (S U S)` on the same physical wires. Since the count preparation is `|+>^(12)`, S fixes it, giving identical final complex states on count and work, including relative phases. This is preparation-scoped: for a general input the optimized input must also be reversed. Both X and Z power-control lists are reversed, while power labels, work wires, negative CP angles, D's gate order and `qj -> cj` measurements remain unchanged. The standalone `build_exponent_mapping` and shared full `build_inverse_qft` contracts are unchanged. Counts remain `z5…z0 x5…x0`; no output reversal is applied. The classical module, finite-grid rounding, candidate verification, `decrypt_from_counts()` convention and measurement-derived algorithm are unchanged.

Candidate C separately groups consecutive positive-control X gates with the same full predicate (including the external count control), at least three distinct targets, and no target in the control set. For a clean bit b it applies exact `MCX(predicate,b)`, one `CX(b,target)` per target, then the same exact MCX. On b=0 this restores b and exactly matches each original X, including phase and the external-control-zero branch; it is not equivalent on arbitrary dirty b. One extra bit is reused across blocks and both count registers only after uncomputation. Cached public multiplier circuits still run separately for distinct control bits. No hidden exponent, order or factors are derived from the synthesis.

## Evidence and limits

`tests/test_tier10_full_optimization.py` passed **5/5** with absolute complex tolerance `1e-12` and zero relative tolerance. It compares every column of synthetic controlled multipliers, including external control 0/1, padding and b=0 restoration; modulus 11 examples explicitly exercise the three-target shared rewrite. It compares full final complex states and full joint count distributions of A/B/C on several reduced circuits, including a modulus-11 case with an actual shared window; tests the negative-sign inverse QFT against its Fourier matrix; and checks direct measurement mapping and a synthetic asymmetric 12-bit classical decryption fixture. The existing `tests/test_tier10_integration.py` passed **2/2** on B, including real Aer synthetic recovery and hash handling. The earlier prototype at `feature/mathematical-modeling@08d8272d7408ae2d2f6f7d5a3bd0a6c459c26386` additionally tests all count-basis inputs with the required input relabeling and an asymmetric complex superposition; its results are not full-size resource measurements.

The full-size Checker runs below are bounded real Aer executions, and the official hash checks independently passed. They are single fixed-seed ideal-simulator trials with at most two batches in the unchanged solve policy; they do not establish a hardware success rate or a statistical failure bound. The tests and proof do not assume dirty ancillas or approximate QFT. They do not justify comparing only a successful plaintext, raw truth tables or distributions with unknown relative phases.

## Full-size results

Qiskit 2.6.1, Aer 0.18.2, Python 3.13, NumPy 2.3.5, Apple M2; `OMP_NUM_THREADS=2`, same default solver shots and seeds, official basis `rz,sx,x,cx`, all-to-all, optimization level 1, seed 12345. Official Checker used a renamed `team-renamed` directory, recorded the actual Aer-input circuit and selected the maximum two-qubit count, depth as tie breaker. All three used one 128-shot Aer batch and one recorded unique circuit and returned **full / SHA-256 match / metrics ok / no flags**. The following metrics are measured, not projected:

| Candidate | Two-qubit gates | Depth | Total gates | Active qubits | Solve seconds | Checker wall seconds | Sampled peak tree RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A v2 baseline | 107,168 | 287,674 | 317,957 | 19 | 1.650 | 3.638 | 298.3 |
| B QFT relabeling | 107,150 | 287,656 | 317,938 | 19 | 1.716 | 3.858 | 242.9 |
| C shared control | 100,152 | 266,482 | 296,442 | 20 | 4.890 | 7.320 | 236.6 |

Wall time and peak memory are from one repeat per candidate using `experiments/monitor_tier10_checker.py`; peak sums RSS across the Checker process tree sampled every 20 ms. It may miss short-lived peaks, double-count shared pages, and varies with scheduling; it should not be interpreted as intrinsic statevector memory. Solve time is the Checker's own per-tier value. In particular a lower sampled tree peak does **not** imply that the 20-qubit state requires less memory: its statevector has twice as many amplitudes as the 19-qubit one. Earlier separate scoring-process measurements were A/B/C 251,559,936 / 256,163,840 / 221,839,360 bytes peak RSS; native build times 0.250 / 0.175 / 0.153 s and score transpilation 0.826 / 0.806 / 1.217 s. These timings are observations, not performance guarantees.

C reduces the first three scoring metrics but increases the active-qubit metric. Official simplicity is relative to other eligible teams and weighs the four metrics 40/30/20/10%; no unconditional score gain follows from this table. The present 512 MiB Aer memory limit, statevector growth, additional runtime and full-scale reproducibility need reassessment before making C the default. Neither this result nor the earlier toy result demonstrates scalability to larger moduli.

## Reproduction and acceptance

Run from the repository root with the pinned Qiskit/Aer environment:

```bash
OMP_NUM_THREADS=2 python -B tests/test_tier10_full_optimization.py
OMP_NUM_THREADS=2 python -B tests/test_tier10_integration.py -v
for variant in A B C; do
  OMP_NUM_THREADS=2 python -B experiments/tier10_full_candidates.py "$variant"
done
```

The second command tests default B. The last script constructs the full public-parameter A/B/C circuits, applies the same native Aer transpilation as the solver and then the official-equivalent scoring transformation; it does not replace Checker acceptance. To reproduce the Checker comparisons, create three **temporary** `team-renamed` folders, each with `classical_keystream.py`, `rsa_classical.py`, `dh_classical.py`, `tier07/qpe.py`, `tier08/{modular,order}.py`, `tier09/modular.py`, and `tier10/{circuit,readout,solution,shared_control}.py` copied from this worktree. For A replace the copied `tier10/circuit.py` with its `git show 0cd8adc:submissions/team3/tier10/circuit.py` version. B is unmodified. For C, in the temporary copy's `tier10/solution.py` only, remove `build_qpe_circuit` from the `.circuit` import and import `shared_circuit as build_qpe_circuit` from `.shared_control`. Run each using:

```bash
OMP_NUM_THREADS=2 python -B experiments/monitor_tier10_checker.py /path/to/team-renamed /path/to/report
```

The monitor calls the unchanged `tools/check_submission.py`, which checks only tiers present in the temporary folder; it does not alter Checker, challenge data or the actual solver. Inspect `report.json` for `status`, `hash_ok`, metrics, flags, and circuit count. Official solve and scoring transpilation each have a 120-second tier budget. Other tiers must not be inferred to have been rechecked here. `git diff 0cd8adc` confirms no Tier 1–9 source or official Oracle, Helper, Checker, challenge data or frozen-release changes; the verified v2 branch remains untouched. No PR or merge is implied by acceptance on this branch.
