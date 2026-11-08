# Tier 5 joint comparisons and MCX synthesis

Research base: `research/tier05-mask-fusion@ab74c49`; construction `optimization/tier05-tier08-v2@0988ac44d88d08cc12258f2010afaf792dd53e7b`; GF(2) reference `research/real-circuit-optimization@4d79b7fa66d0acd4786d71be3c3ac2d291618c69`. All edits are research-only. The 22-qubit candidate uses an existing exact clean-ancilla MCX template independently for each comparison; it is **not** a successful shared-predicate synthesis. The 19-qubit joint-synthesis question remains open.

## Controls and legality

Each MCX8 has physical controls `work[0:8]` (q10–q17) and target flag q18. In the accepted version the exact dirty M15 template borrows key q0–q2, which may be arbitrary and entangled, and restores them. The first comparison tests a public-constant-adjusted first mask, the middle comparison is conjugated by H on the flag and tests the second mask, and the third reverses the first comparison. In execution order, write this as `A C_A A^-1 B D_B B^-1 A C_A^-1 A^-1`, where A and B XOR the two rotated public masks into work; X wrappers around each comparator implement the appropriate public constant. Identical physical control wires do not mean identical Boolean predicates: uncomputation, the other mask and constant adjustments change their values. Comparing across those transitions or reusing a computed conjunction without updating it is invalid. The third operation returns to the first predicate only after all intervening steps; simply carrying a control predicate through the intervening target/work-changing operations would require a new exact proof and proper uncomputation.

## Bounded prototypes and phase evidence

1. **Shared predicate, hypothetical adjacent pair.** For two adjacent operations `X^p` then `Z^p` on one target, compute p into one clean ancilla, apply controlled X and Z, then uncompute. The 8-control microbenchmark produced 104 → 62 CX, depth 307 → 183, but uses a 13th active wire and does not implement the actual separated oracle comparisons. This is not a full-circuit result and no saving is attributed to the real oracle. All columns on the clean-zero subspace for 3 controls were compared as full complex operators (max error below 7e-16); an 8-control full-support random superposition test gives error below 6e-17. For clean=0, the identity follows directly from computing the same p, applying X and Z in order, and uncomputing p. No arbitrary clean=1 contract is claimed.
2. **Relative-phase compute/uncompute.** A bounded fragment computes a two-control conjunction with RCCX, applies CZ, then uses the exact inverse RCCX. Its full complex operator matches the corresponding exact-CCX sandwich on every input (error zero), with 13 → 7 CX and depth 27 → 23. The cancellation works because the relative diagonal phase commutes with the intermediate diagonal CZ. This does **not** prove cancellation across the actual intervening mask transforms; no relative-phase replacement was installed in the full oracle.
3. **Dirty-ancilla choices.** M15 (3 borrowed), I15 (6 borrowed), and KG24 (1 or 2 borrowed) exact templates were placed into all three actual comparison sites and complete 25-iteration circuits were compiled. The 3-control full complex operator for each template, including all dirty states, matched the exact gate within 1.6e-15. No dirty template improved the 19-qubit CX objective. Tests do not constitute a dense verification of every column of the 8-control dirty templates; those exact constructions rely on the Qiskit synthesis contract.
4. **Three new clean ancillas.** Each comparison uses an exact 8-control M15 clean template with q19–q21 initialized zero. It restores all three before the next operation. No existing key wire is assumed clean; the original 19 wires and 25 iterations retain their roles. We exhaustively checked all 512 control/target inputs, exact complex amplitudes and clean restoration for the actual 8-control clean template (maximum error 5.11e-15). Linear extension gives equality on superpositions and entangled original registers for clean-zero ancillas. Unchanged comparators, X/H wrappers, mask transformations and inverse operations then prove the original phase predicate and cleanup compositionally. This guarantees equivalence on the three-clean-zero subspace, not arbitrary values of the new ancillas. A four-control full complex clean-subspace operator test also passed. Final measurement mapping and the 25 oracle calls were checked.

## Full-circuit measurements

Local Python 3.13.9, Qiskit 2.6.1/Aer 0.18.2. Same Aer-target native compilation, `rz,sx,x,cx`, level 1, seed 12345, no coupling restriction, followed by the existing GF(2) consecutive-CX pass and official scoring compilation. One full circuit per row; measured directly, not extrapolated from the MCX block. Total gates and depth exclude measurements.

| Candidate | 2Q CX | Depth | Total | Active qubits |
|---|---:|---:|---:|---:|
| Existing 3-dirty M15 + GF(2) | 14,552 | 28,132 | 40,938 | 19 |
| 6-dirty I15 | 15,002 | 29,157 | 42,063 | 19 |
| 1-dirty KG24 | 16,502 | 29,982 | 48,813 | 19 |
| 2-dirty KG24 | 16,502 | 26,582 | 48,363 | 19 |
| **3 additional clean qubits** | **13,802** | **19,480** | **38,556** | **22** |
| Previous mask-fusion depth reference | 14,652 | 23,757 | 39,238 | 19 |

The clean construction reduces CX by 750 and depth by 8,652 but adds three active qubits. Each isolated clean MCX8 is 42 CX versus 52 for the dirty baseline; the full result nevertheless comes from actual whole-circuit compilation. An active-qubit scoring penalty applies, so the gate reductions alone do not determine net competition points. Single execution timing and metadata are in `results.json`; compile durations are not evidence of simulator speed. The clean work allocation is a real additional resource, and the GF(2) pass runs after native compilation.

## Validation and recommendation


Two preselected paired seeds were run in separate clean processes with 128 shots, actual Aer seed injection recorded, two simulator threads and a 120-second process timeout. Both baseline and clean candidate returned the expected SHA-256 for each seed. Seed 1000 solve time was 13.6293 / 90.0753 seconds; seed 2000 was 14.8872 / 88.5873 seconds (baseline / clean). These are limited, sequential local observations, not a controlled distribution or noise-hardware result. They show a material runtime cost in this environment despite the circuit savings. The increased active qubit count can also reduce the official qubit component; final competition score depends on other teams. Exact seed metadata and safe results are in `paired_results.json`.

The unmodified official Checker was run only for Tier 5 in an isolated correctly named submission copy, using the prototype and its GF(2) rewrite. It returned **full**, hash match, metrics status **ok**, flags empty and one circuit executed; its 13,802 / 19,480 / 38,556 / 22 metrics match the direct measurement. Its `solve` took 92.391 seconds, near the unchanged official 120-second timeout; `checker_result.json` contains the safe summary. No full ten-tier Checker was run.

**Recommendation: INCONCLUSIVE for integration.** The exact clean-ancilla prototype achieves the requested two-qubit and depth reduction and has finite correctness evidence, but uses three more active qubits, is near the timeout in the one official check, and was roughly six times slower in the two local pairs. These limited samples do not establish robust success across seeds or machines. The original 19-qubit joint optimization did not succeed; do not replace the accepted implementation based on this experiment. Further work could seek an exact reusable partial predicate that accounts for the changing work register, or a rigorously phase-cancelled synthesis without adding clean wires. Any future integration should measure the actual scoring tradeoff and more seeds without relaxing limits.

Reproduce in the pinned environment:

```sh
PYTHONPATH=. python -B -m research.tier05_joint_mcx.experiment
PYTHONPATH=. python -B -m research.tier05_joint_mcx.validate
```

The second command runs four isolated bounded solves and one Tier 5 official Checker, not the ten-tier Checker. It writes aggregate safe result JSON under `research/tier05_joint_mcx`; it does not change production submissions, official tools, or any other tier. Experimental private temporary snapshots are automatically removed.
