# Team 3 bounded hyperoptimizer

A research framework with a deliberately small first experiment. It reuses prior Tier 5/9/10 acceptance evidence and promotes one new Tier 8 candidate. It is not a production integration or a claim that all proposed superoptimization algorithms are implemented.

## Layout and semantics

- `ir/model.py`: typed exact/relative-phase/Boolean semantics, control polarities, phase sensitivity, affine maps, public permutations, and clean/dirty restoration contracts. Declaring a contract is not proof; `certify` rejects Boolean-only phase claims and context-free relative-phase substitutions.
- `synthesis/permutations.py`: complete-domain row elimination, forward/inverse synthesis, bit/polarity conjugation, explicit sparse linear conjugation, complementary-cube cancellation and shared-target fanout. General affine CNOT overhead is actually emitted on both sides; it is not free.
- `synthesis/windows.py`: strictly bounded <=3-wire monomial SAT/SMT windows with phase exponents modulo eight. The supplied exact gate library can represent X/CX/Toffoli, mixed-control/multi-target maps and diagonal phase gates. Solver results are independently replayed; an unknown/timeout is not an optimality proof. It does not support arbitrary continuous phases or optimize a global circuit.
- `search/run.py`: deterministic Tier 8 grid, proposal hashes, circuit fingerprint deduplication, checkpointing and verified completed-cache reuse. No unbounded worker remains running.
- `verification/`: complete controlled complex operators/inverses, prepared full-state comparison, and explicit evidence stages. No per-control-branch phase fitting is allowed.
- `cost/official.py`: actual execution-precompilation followed by unchanged official scoring. Tier 8 defaults to its basis-first execution path; Aer-native mode is an explicit separate option for compatible adapters.
- `experiments/`: Tier 8 execution adapter, isolated official/seeded validation and immutable prior-evidence registry.
- `results/`: configuration/cache hashes, measurements, phase evidence, Pareto data and status registry.
- `tests/`: affine/control/padding, semantics gatekeeping, and bounded phase-aware SMT regression cases.

This first version does not implement global beam/A*/meet-in-the-middle search, arbitrary row orders, dense affine exploration, a general Grover optimizer or automated complete-tier replacement from SMT windows. Small solver demonstrations are utilities, not claimed measured tier improvements. These extensions are deferred because the requested usage-saving policy favored a cheap, large Tier 8 opportunity.

## Reproduction

Use Python 3.12 and repository requirements plus `psutil==7.2.2` and `z3-solver==5.4.1.0`. From the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/hyperoptimizer/tests/test_framework.py
python -B research/hyperoptimizer/experiments/registry.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/hyperoptimizer/search/run.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/hyperoptimizer/search/run.py --fresh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/hyperoptimizer/verification/tier08.py
```

The ordinary search command reuses a completed checkpoint only when its candidate SHA-256 matches. `--fresh` regenerates all 36 coordinate configurations with seed 20261112. There are 24 bit/polarity proposals and 12 one/two-CNOT affine proposals, four forward/inverse-clear alternatives per public multiplier. Only three prefixes are whole-circuit scored. Selected configuration and gate arrays are public modular arithmetic, not recovered orders or factors. Replaying changes timing metadata; compare gate networks and metrics separately from elapsed time.

For official and five-pair execution, the existing sibling `Quantum-Cryptography-Benchmark-Harness` checkout must be at `ab9676749e00da904d0b8076811a2407d3b7205f`, with the committed research branch available in its Git object store. Commit sources before running:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/hyperoptimizer/experiments/validate.py
```

The validator archives the exact v6 baseline and current committed research tree, installs a disposable Tier 8 multiplier wrapper and calls the unchanged official Tier 8 Checker. It then uses five fresh-process paired seeds 8100–8104. Actual forwarded seeds, completed Aer jobs, hashes, solve time and 20-ms sampled process-tree RSS are retained. Official limits stay 120 seconds each; the official outer cap is 370 seconds, seeded-worker cap 120 seconds, monitored RSS cap 2 GiB. No plaintext, factors or raw counts are saved.

Static compilation times, measured solve/Aer times, cache sizes and missing measurements are distinguished. Reproducibility risk is qualitative, not assigned a fabricated probability. See [report](../../docs/TEAM3_HYPEROPTIMIZATION_REPORT.md). Never copy a research cache into a final package without separate integration, dependency and artifact auditing.
