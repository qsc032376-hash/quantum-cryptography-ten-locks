# Tier 6 reflection synthesis experiment

**INCONCLUSIVE** for the complete tier. The strongest isolated reflection by CX then depth uses two clean scratch qubits (KG24). All changes are research files. The full-solver comparison, official candidate validation and paired solve reliability remain outstanding.

## Reference and reproducibility

The baseline is c4455782ea9388d5897fc27270f42dd3786ed35d. Its official results in docs/v6-rc/report.json are FULL, 3,000 two-qubit gates, depth 5,715, 8,752 gates and 22 active wires. Frozen package ca7290c7f6b35e37e4ef94f3d5f79110309f594f was read only. From the repository root on Windows, using the pinned Python 3.12 environment with psutil, run:

~~~text
python -m research.tier06_extreme.profile
~~~

[Recorded samples and metrics](../research/tier06_extreme/results.json). Qiskit 2.6.1, all-to-all rz/sx/x/cx, precompile level 2 followed by scoring level 1, transpiler seed 12345. Each full-width numerical trial uses a fresh process, Aer CPU statevector and two threads maximum. Costs below are for isolated, unmeasured components.

| Component | CX | Depth | Gates | Active |
|---|---:|---:|---:|---:|
| Original reversible mask |64|120|160|22|
| Original phase oracle, synthetic byte 0 |178|312|431|22|
| Original bit oracle, synthetic byte 0 |186|345|462|23|
| Original diffuser, M15 |72|164|310|20|
| KG24 one clean |72|167|306|15|
| KG24 two clean |72|104|307|16|
| KG24 one dirty |138|316|522|15|
| V24 no workspace |1084|2384|2942|14|

Two-clean KG24 reduces isolated depth by 36.59%, gates by 0.97% and active wires by four; CX stays at 72. On the four minimized metrics the non-dominated choices are one clean, two clean and no workspace. The dirty option's distinct workspace contract can matter even when its numeric costs are dominated. The synthetic oracle figures include computation and uncomputation together. Isolated costs are not additive across a compiled round. The calibration bit oracle has a separate flag, and its width need not equal the active width in the scored circuit.

## Reflection proof and checks

On data wires numbered 0 through 13, H on the highest-index target conjugates exact MCX to a sign flip on the all-ones state. Conjugation by X on all data wires moves this sign flip to zero. Conjugation by H on all data wires and the outer phase pi give the reflection 2|+><+|-I, where |+> denotes the uniform state on all data wires. The selected synthesis uses two zero-initialized scratch wires and restores them. It needs no dirty-wire assumption. This argument concerns the diffuser alone.

For each method, the complete complex operator on five data wires was compared on every applicable input column, including amplitudes into every workspace sector. The dirty case checked the entire operator including arbitrary workspace, which extends by linearity to entangled inputs. Maximum entry error across methods was below 7e-15. At 14 data wires, five independent complex input vectors (seeds 100 through 104) were paired across baseline and selected circuit. The analytic output on the clean subspace is twice the mean input amplitude minus each input amplitude, with zero amplitude in the other scratch sectors. All ten samples matched up to a single global phase, maximum entry error below 6e-17. The same seed initializes each paired input and is passed to Aer. These deterministic statevector tests do not sample key recovery.

| Five synthetic trials, median | M15 | Two-clean KG24 |
|---|---:|---:|
| Aer run including state save, seconds |0.1024|0.0142|
| Whole worker peak working set, MiB |170.56|95.42|

Memory includes imports, compilation, input preparation and simulation. The workers simulate 20 and 16 wires respectively. A production solver may still allocate 22 wires for other operations. Neither timing nor memory improvement can be transferred directly to the whole tier.

## Score and outstanding evidence

In a hypothetical field with the candidate best on each metric, if *whole-tier* depth decreased by 10% while the three other metrics stayed fixed, the largest gain under those assumptions would be 1.5 x 0.30 x 0.10 = 0.045 points. This is a sensitivity example. A candidate score, a measured whole-tier reduction and a positive lower bound on competition points cannot be derived from this experiment.

The bounded search compiled five generic diffuser families. It did not synthesize a ciphertext-specific predicate, accelerate key recovery, or run a modified solver. Candidate oracle calls, calibration statistics, solve time, full-solver peak memory, actual solve seed success rate, official metrics and hash verification are unmeasured. The checker evidence applies only to frozen v6. No production recommendation follows from the component ranking.
