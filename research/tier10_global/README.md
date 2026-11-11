# Tier 10 global synthesis research

This directory compiles only public modular permutations. It never searches for a discrete logarithm, changes recovery shot budgets, or records keys/plaintext/raw measurements. The accepted runtime and final archive are untouched.

## Reproduction

Use the repository's pinned requirements (Qiskit 2.6.1, Aer 0.18.2), NumPy and psutil 7.2.2. The recorded local environment is in `validation.json`. From the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_global/search.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_global/verify.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_global/alternatives.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_global/profile.py
```

Run these serially for comparable timing. `search.py` regenerates public gate networks and resource screens; it has 96 deterministic coordinate configurations, four forward/inverse and clear-mode choices per multiplier, and seven whole-circuit prefix checkpoints. The configurations and seed are saved, and duplicate operation fingerprints are rejected before ranking. A prefix reuses the best networks found previously. This is bounded search, not a global optimum proof. Gate-network caching is represented by `candidate.json`; the candidate's solve loads that compiled public circuit rather than repeating the offline search. Account for preprocessing separately.

For isolated official and ten-seed paired validation, place the benchmark-harness checkout beside this repository as `Quantum-Cryptography-Benchmark-Harness`, at commit `ab9676749e00da904d0b8076811a2407d3b7205f`. Its Git object store must contain this research commit (fetch the branch into that clone if needed). The script checks the harness revision, archives the pinned runtime and current committed research tree, and appends a builder wrapper only in a disposable candidate snapshot:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier10_global/validate.py
```

Commit the research sources before running validation because it evaluates Git snapshots, not uncommitted edits. The wrapper's source and candidate-network SHA-256 are recorded. It calls the unchanged official Tier 10 Checker, then ten pairs with seeds 1000–1009. Limits are 120 seconds per paired worker and 2 GiB sampled process-tree RSS; the official stage has a 370-second outer cap while retaining the official 120-second solve and transpile limits. Only safe aggregate JSON is retained. The shared benchmark worker verifies actual forwarded seeds, finished Aer jobs and hashes.

## Files and interpretation

- `search.py`, `search.json`: exact mixed-polarity synthesis, configuration cache, fingerprints and full-circuit metrics.
- `candidate.json`: public compiled networks, selected by CX at the level-1 native execution path.
- `verify.py`, `equivalence.json`: all-column complex controlled-block operators, inverses, and full 19-qubit prepared/random-input statevectors without phase fitting.
- `alternatives.py`, `alternatives.json`: ANF/ESOP considerations, cycle synthesis, dirty borrowing, native compiler levels, QFT/group-operation attribution.
- `profile.py`, `profile.json`: ranked full-circuit removal deltas for every public group-power block. Removal circuits are cost probes, not valid solvers; deltas are not additive.
- `validate.py`, `validation.json`: isolated official results and ten matched seeds.
- `pareto.json`: measured resource/compile frontier and fully measured baseline/finalist comparison. Missing simulation times are unknown, not zero.

Every scoring compilation uses `rz,sx,x,cx`, seed 12345, optimization level 1 and the unchanged official configuration. Native-level 0/2/3 alternatives are separately labeled and are not the validated candidate. Global cross-module cancellation is constrained by distinct external controls. Scratch registers are never assumed clean when they are merely idle or in superposition.

See [report](../../docs/TIER10_GLOBAL_SYNTHESIS_REPORT.md). Research acceptance is not release or submission approval.
