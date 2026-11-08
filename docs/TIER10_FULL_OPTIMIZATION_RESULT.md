# Tier 10 full-scale circuit optimization

## Recommendation and reference

**ACCEPT F on this working branch:** combine the exact no-ancilla shared-predicate fanout with QFT wire relabeling. The actual official Tier 10 Checker recorded 82,804 two-qubit gates, depth 218,263, 245,153 total gates and 19 active qubits, with `full`, matching SHA-256 and no flags. The default `build_qpe_circuit()` now uses F. The verified v3 branch is unchanged.

The existing working branch was continued from `fd35d76`, whose parent was v2 `0cd8adc`; it was not reset or merged. The specified `integration/optimized-v3-candidate@04feb70e52f5522aa2976ca9c7df2e48f27f3cce` changes Tier 9's `solution.py` and adds `tier09/shared_controls.py` relative to v2. Its Tier 10 circuit, readout and classical interfaces, Tier 9 `modular.py` used by Tier 10, shared QFT, Checker, scoring, challenge data, and Tier 10 integration tests are byte-identical to v2. Thus the same-machine Tier 10 A circuit is also the v3 Tier 10 baseline. **The existing working branch does not contain v3's separate Tier 9 optimization**; this work does not alter other-tier code and does not claim to integrate v3. A later integration onto v3 must retain its Tier 9 files and rerun relevant checks.

## Transformations

**QFT B.** For both count registers let S reverse the wires, D be the inverse-QFT body after its initial swaps, and U the exact controlled modular-power mapping. The reference applies `D S U`; reversing each register's controlled-power wiring gives `U' = S U S`, and applying D gives `D U'`. Because the actual input count state is `|+>^12`, S fixes it: `D U' |+,+,1> = D S U |+,+,1>`. This is exact equality of the complete final complex state, hence its joint output distribution. For an arbitrary count input the optimized input must also be reversed; it is not arbitrary-input equality with unchanged preparation. Negative CP angles and H order are preserved, as is measurement `qj -> cj`: the displayed key is `z5…z0 x5…x0`, with no output reversal. Standalone `build_exponent_mapping` and the shared full inverse-QFT contract are unchanged. The classical recovery module and `decrypt_from_counts()` are unchanged.

**Clean shared control C.** On consecutive operations with the same full predicate f, including the external count control, and at least three distinct targets outside the control set, compute f into an initialized-zero auxiliary, use it to flip the targets, then uncompute it. This yields the original exact controlled unitary on the clean-ancilla subspace and restores zero, including phase and control-zero behavior; it is not an arbitrary dirty-bit identity. D combines B and C, using the same single restored auxiliary across both count registers. C and D remain independently testable experiments; the extra active qubit and higher solve time are costs.

**Ancilla-free fanout E/F.** Independently adapted from the verified v3 Tier 9 technique, the Tier 10 compiler groups only *consecutive* X gates with an identical full predicate, XORs target occurrences to cancel equal pairs, then chooses a remaining target p as pivot. Apply CX from p to each other target, one exact MCX(f,p), and undo the CX fanout in reverse. When f=0 the fanouts cancel; when f=1 the pivot and every other selected target flip once. All selected targets are outside f, so the predicate is unchanged; each primitive is an exact phase-free permutation. The transformation therefore preserves all basis labels and relative phases, including external-control branches and padding, without allocating or borrowing any ancilla. Repeated multipliers controlled by distinct bits remain separate operations. E uses the full inverse QFT; F additionally performs B's consistent relabeling. The optimizations synthesize public modular permutations only; they do not derive a factor, order or discrete logarithm classically.

## Verification

Before the final Checker comparison, `tests/test_tier10_full_optimization.py` passed **6/6** at complex `atol=1e-12`, `rtol=0`. For both control values it checks every operator column on reduced controlled multipliers, including padding, phases and clean-ancilla restoration, with synthetic examples that really contain shared windows. It compares the complete complex final state and joint count distribution for A through F on reduced instances, including a case with an active clean-control window, and verifies `qj -> cj`. It checks the inverse-QFT matrix against the negative-exponent Fourier matrix. An asymmetric 12-bit synthetic fixture checks the actual `measurement_from_counts()` and `decrypt_from_counts()` interfaces. The earlier prototype `feature/mathematical-modeling@08d8272` also checks all count-register basis inputs with the required input relabeling and an asymmetric complex superposition. The existing Tier 10 integration tests passed **2/2**, including an Aer-based synthetic recovery and hash test for default F.

A separate efficient check propagates all 256 control/work basis labels through the actual phase-free fanout gate sequence for **each of the 12 public powers**, verifying the full controlled permutation and padding without constructing a full 19-qubit statevector. This public gate-specification test is not classical discrete-log recovery. Each primitive has phase +1, so equality of the basis permutation also fixes relative phase for these specific sequences. Actual `solve()` still obtains candidates from Aer measurements and checks the public group relation; the official plaintext is verified by the unchanged Checker.

## Full-size same-environment comparison

Qiskit 2.6.1, Aer 0.18.2, Python 3.13.9, NumPy 2.3.5, Apple M2; `OMP_NUM_THREADS=2`. Official scoring uses basis `rz,sx,x,cx`, all-to-all, optimization level 1 and seed 12345. Each row is an actual Tier 10 solve in a renamed team directory, one recorded unique Aer circuit and one 128-shot batch. The unchanged Checker returned **full / SHA-256 match / metrics ok / no flags** for every row. A uses the actual v3 Tier 10 `circuit.py`; B–E select their builder only in temporary solution copies. F uses the working branch's unmodified default solution and circuit.

| Candidate | Two-qubit | Depth | Total gates | Active qubits | Solve s | Checker wall s | Sampled tree peak RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A v3 Tier 10 | 107,168 | 287,674 | 317,957 | 19 | 1.769 | 3.794 | 288.4 |
| B QFT only | 107,150 | 287,656 | 317,938 | 19 | 1.625 | 3.370 | 310.1 |
| C clean shared control | 100,152 | 266,482 | 296,442 | 20 | 4.440 | 6.668 | 288.8 |
| D B + C | 100,134 | 266,464 | 296,423 | 20 | 4.401 | 6.615 | 289.4 |
| E no-ancilla fanout | 82,822 | 218,281 | 245,172 | 19 | 3.037 | 4.719 | 249.7 |
| F E + B, default | 82,804 | 218,263 | 245,153 | 19 | 2.996 | 4.586 | 284.3 |

F reduces A by 24,364 two-qubit gates, 69,411 depth and 72,804 total gates, without increasing active qubits. B, C and D are valid; **B ACCEPT**, **C/D INCONCLUSIVE for adoption** because they add an active qubit and take longer; **E ACCEPT**, **F ACCEPT**. Official simplicity ratios depend on other eligible teams, so these metrics alone do not establish a final competition score. E/F solve more slowly here even though their scoring gate counts are lower; hardware performance and larger-instance scaling are unproven.

Wall time and RSS were observed with `experiments/monitor_tier10_checker.py`, sampling the sum of process-tree RSS every 20 ms. The sum may double-count shared pages and miss short spikes. Values vary by run and are not intrinsic statevector memory; a 20-qubit statevector has twice the amplitudes of a 19-qubit statevector. The solver's existing memory limit and finite timeout remain in force. Each Checker result represents one ideal fixed-seed trial with bounded batches; it is not a failure-rate estimate or evidence for noisy hardware.

## Reproduction and boundaries

With the pinned Qiskit/Aer environment from the repository root:

```bash
OMP_NUM_THREADS=2 python -B tests/test_tier10_full_optimization.py
OMP_NUM_THREADS=2 python -B tests/test_tier10_integration.py -v
for variant in A B C D E F; do
  OMP_NUM_THREADS=2 python -B experiments/tier10_full_candidates.py "$variant"
done
```

The last script separately builds the full public-parameter circuit, applies native Aer transpilation and the official-equivalent score transpilation. It does not replace Checker validation. For the Checker experiment, copy the unchanged team dependencies and candidate `tier10/{circuit,shared_control,readout,solution}.py` into six separate temporary `team-renamed` directories. A uses `git show 04feb70:submissions/team3/tier10/circuit.py` in its temporary copy. For B/C/D/E, change only the temporary solution's `build_qpe_circuit` import to respectively `circuit.build_qpe_qft_only`, `shared_control.shared_circuit`, `shared_control.combined_circuit`, or `shared_control.fanout_circuit`. F uses the unmodified working-branch solution. Each temporary directory includes `classical_keystream.py`, `rsa_classical.py`, `dh_classical.py`, `tier07/qpe.py`, `tier08/{modular,order}.py`, and `tier09/modular.py`. Then run:

```bash
OMP_NUM_THREADS=2 python -B experiments/monitor_tier10_checker.py /path/to/team-renamed /path/to/report
```

The monitor invokes the unmodified official `tools/check_submission.py`. Inspect `report.json` for `full`, hash, metrics, flags and recorded circuits. The Checker tests only the tier present in these temporary copies; it does not validate the entire v3 package. Scoring selects the executed circuit with the most two-qubit gates, breaking ties by depth; solve and scoring-transpilation each have a 120-second tier budget. Shots, batches, runtime and classical compilation cost are distinct from the four scoring metrics. `git diff fd35d76` confirms no other-tier code was changed in this work. The divergence from v3's Tier 9 noted above must be resolved in a separate integration step, not silently attributed to this branch.
