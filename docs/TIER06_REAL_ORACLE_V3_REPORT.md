# Tier 6 V3 audit of the actual v6 oracle

**INCONCLUSIVE for a replacement solver.** The experiment checks the published search and calibration oracle circuits for the actual public ciphertext byte at baseline c4455782ea9388d5897fc27270f42dd3786ed35d. No optimized candidate was built.

## Baseline evidence

The archived official [Checker report](v6-rc/report.json) records full, matching hash, valid metrics, empty flags, two executed circuits, 3,000 two-qubit gates, depth 5,715, 8,752 total gates, 22 active qubits and solve time 11.766 s. These are historical v6 results. There was no same-environment candidate comparison. The report gives no new-candidate runtime, memory or score evidence.

## Coherent consistency test

Prepare all 14 data wires uniformly, eight work wires at zero, and the calibration flag in the minus state. Apply the baseline phase oracle followed by the baseline bit-valued predicate. A flag XOR on the minus state contributes a minus sign on its enabled branch. If both oracles implement the same Boolean predicate with clean workspace, the two signs cancel. Undo the preparation and check the complex amplitude of the all-zero register. Sample neither data-register outcomes nor candidate keys.

On Aer statevector with two threads, work leakage immediately after the phase oracle was 4.49e-31. Following the bit oracle it was 1.35e-30. The absolute difference of the final return amplitude from one was 5.52e-15 or less. The two-round search constructor produced exactly two phase-query blocks, no flag predicate and identity qubit-to-classical measurement mapping on all 14 wires. This query count is for the inspected constructor, not a measured count from an adaptive solve.

This tests one coherent input with support on all key basis states. It can detect a disagreement between phase and flag marking, but a shared predicate error could pass. It is not a full operator proof, independent truth-table specification check or decryption success test. The small leakage is numerical evidence for clean workspace on this input only.

Run from the research checkout root with the pinned dependencies:

~~~text
python -m research.tier06_real_oracle.audit
~~~

[Recorded scalar results](../research/tier06_real_oracle/results.json). This audit does not produce an optimized ciphertext-specific key-search implementation. No replacement Checker or paired recovery trials were run. No Pareto frontier or Simplicity improvement is supported. The synthetic V1/V2 evidence does not change this conclusion.
