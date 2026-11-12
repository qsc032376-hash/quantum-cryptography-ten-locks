# Four-stage circuit provenance diagnostic

This diagnostic is additional to the three unmodified official Checker CLI
runs. It performs at most one additional real solve for each of Tiers 5, 6 and
7; it is not a fourth complete ten-tier acceptance run or an independent
performance benchmark. The three CLI runs remain the primary acceptance
evidence.

## Observation boundaries

`four_stage_probe.py` invokes the unchanged official `worker_solve` and
`worker_transpile` functions in separate fresh Python processes. A selective
`sys.setprofile` callback observes the actual functions' inputs and returns.
The diagnostic does not replace any production, Qiskit, Aer or Checker
function. The official solve worker still installs its own ordinary recorder,
as it does during an unmodified Checker run.

1. **Constructed circuit:** the exact circuit supplied by the approved
   `solution.py` to its preprocessing `transpile()` call. This includes actual
   measurement-dependent choices, such as Tier 6's chosen iteration count and
   Tier 7's phase-check circuit. It is not a call to an unrelated default
   `build_circuit()`.
2. **Aer input:** the exact circuit argument entering the underlying
   `AerBackend.run`. The intermediate source-transpiler return is also recorded
   separately. In Tier 5 this distinction is necessary because `gf2_runs`
   transforms that intermediate circuit before Aer receives it.
3. **Scoring input:** every circuit loaded by the unchanged official scoring
   worker from its normalized, deduplicated QPY recording. The selected index
   uses the official maximum `(two_qubit_gates, depth)`, with the first tie
   retained. Normalization removes simulator save/set instructions and resets
   circuit metadata/name; it does not rebuild the submitted circuit.
4. **Scoring output:** the actual `transpile()` return inside the unchanged
   official worker, using its real configuration. Its computed selected
   metrics are compared with the worker's own output.

Private native-circuit recordings provide an exact bridge between stages 2
and 3 and the separately captured primary Checker run. Comparisons check
widths, ordered operation names and public base classes, operation arities,
quantum/classical wire mappings, numeric scalar parameters and global phase.
Conditional or opaque instructions are refused by this native comparison.
Only equality booleans are published, never numeric gate parameters or the
private QPY payloads. `Instruction.__eq__` is not used.

## Fingerprint scope and privacy

`circuit_fingerprint.py` defines schema
`v63-parameter-free-ordered-structure-v1`. Its digest includes circuit widths,
ordered public instruction identities, arities, wire mappings and parameter
types. It excludes numeric parameter values, global phase, labels, circuit
metadata and composite-gate names. Opaque gates are normalized by public class
and width without opening their definitions.

Consequently, a matching structural digest alone is **not** a proof of equal
unitaries, identical phases or equivalent secret-dependent parameters. The
separate transient native comparisons establish the more limited exact
primitive-sequence equality where those comparisons are reported true.

Each summary includes a literal named-CX count and the unchanged official
`compute_metrics` results for the stored representation. A constructed circuit
containing opaque composite instructions has **top-level** metrics; these are
not the eventual decomposed gate cost. All scoring-output metrics are measured
after the real official transpilation. Histograms and measurement mappings are
included, but measurement counts, recovered keys and plaintext are not.

## Resource and execution limits

The runner applies a 120-second wall limit and a 2 GiB aggregate process-tree
RSS limit to each diagnostic solve/scoring process, sampled every 50 ms. A
limit violation terminates the process group, records the failure and is not
retried. Scoring is skipped after a failed diagnostic solve. These external
bounds do not edit the official scoring configuration.

All diagnostic child processes explicitly use `PYTHONHASHSEED=0` and
`QISKIT_PARALLEL=FALSE`. The exact compilation arguments and Aer run options,
including the distinction between an unspecified simulator seed and an
explicit seed, are captured from real calls. Profiling and copying can add
runtime and memory overhead, so these timings should not be described as
unmodified production performance.

## Synthetic metadata-test correction

The initial synthetic native-comparison test attempted to change a rotation
parameter by assigning through `circuit.data[index].operation.params`. In this
Qiskit version that accessor manipulation did not establish the intended
different stored circuit, so the fixture's assertion that the two circuits
must compare unequal failed. No Aer execution occurred in that test.

The test was corrected to construct two independent synthetic circuits with
different explicit rotation parameters. The reproducible
`fingerprint_selftest.py` then passed all checks: syntax, exclusion of numeric
parameters/global phase/metadata from structural digests, sensitivity to wire
ordering, normalization of opaque names, literal-CX/official metric accounting
and strict native-equality guards. Its final result is
`fingerprint-schema-selftest.json`. This was an audit-test fixture correction,
not a production-circuit change or an Aer failure.
