# Tier 5 extreme synthesis research

This directory changes no production solution. It preserves 19 qubits, 25 Grover iterations, 128 shots, the exact public phase predicate and measurement-derived candidate recovery. No key lookup or classical search result is used by the solver.

Use Python 3.12 with the repository requirements, `psutil==7.2.2` for the existing benchmark harness and `z3-solver==5.4.1.0` for the small synthetic SMT probe. From the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier05_extreme/search.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier05_extreme/verify.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier05_extreme/alternatives.py
```

Run serially for comparable timing. The deterministic grid has 15 complete-circuit configurations; the separate phase-polynomial probe adds one whole-circuit measurement. The exact GF(2) pass is the baseline's existing implementation. Search caching fingerprints serialized circuits plus compilation parameters; equivalent requests reuse compiled results. The final tie-break minimizes CX, then depth, then total gates. Official scoring always uses level 1, seed 12345 and `rz,sx,x,cx`; the selected solver precompilation uses level 2. Results and the final configuration are in `search.json` and `candidate.json`.

`verify.py` checks all 1,024 key inputs of the fused Boolean mask map, a local complex RCCX operator, phase action on a nonzero-amplitude superposition of every key, workspace restoration, an arbitrary-workspace oracle state, and the full compiled 25-iteration circuit. The expected phase computation is test-only, never used in candidate construction or solving, and no marked-key value or raw statevector is saved. The phase-aware simulator explicitly restores the known compiled global-phase metadata after `set_statevector`; it does not fit a phase to force agreement.

`phase-diagnostic-before-fix.json` retains an initial test-wrapper error: Aer initialization overwrote global phase, creating an apparent full-state discrepancy despite identical probabilities. `diagnose_phase.py` reruns diagnostics with the corrected simulator helper and reports aggregate errors only. `validation-attempt1.json` retains a separate failed isolated import: the research wrapper eagerly imported its own partially initialized module. The corrected wrapper imports lazily inside the builder. Neither failure is discarded or counted as a passing trial.

## Official Checker and paired seeds

Place the existing benchmark-harness checkout beside this repository as `Quantum-Cryptography-Benchmark-Harness`, at `ab9676749e00da904d0b8076811a2407d3b7205f`, with the research source commit available in its Git object store. Commit source changes before running:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python -B research/tier05_extreme/validate.py
```

The script archives the baseline and committed candidate, appends only a temporary builder/compiler wrapper in the disposable candidate, and calls the unchanged official Tier 5 Checker. It then evaluates five paired seeds, 5100–5104, in fresh processes. Actual seed forwarding, hashes, circuit execution, finished Aer jobs, solve time and sampled process-tree RSS are recorded without plaintext or counts. The existing accepted baseline Checker result in `validation-attempt1.json` is reused when present and is clearly bound to the same baseline/environment. No candidate failure is reused as a pass.

Official solve and scoring-transpile limits remain 120 seconds; the official worker outer cap is 370 seconds. Seeded workers have a 120-second outer cap and 2 GiB monitored RSS. RSS is sampled every 20 ms and is not an exact allocator peak. Static native/GF(2) and scoring compilation times are separately recorded by `search.py`; they are not per-seed compilation timers.

`alternatives.json` records non-additive component costs, an exact small-window phase-polynomial screen and a bounded SMT proof on a synthetic three-wire linear block. It does not claim additional production savings from the SMT example. `pareto.json` distinguishes static resource/compilation results from baseline/finalist simulator measurements; unknown runtimes remain null.

See [the full report](../../docs/TIER05_EXTREME_SYNTHESIS_REPORT.md). Research acceptance does not authorize release integration or packaging.
