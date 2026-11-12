# Bounded compilation and serialization probes

The companion `pass-manager-probe.json` was produced by
`pass_manager_probe.py` against the already extracted approved archive at
`/workspace/work/v63-fresh-official`. The probe performed no Aer execution,
key recovery, Oracle-definition inspection, or source modification. The
reported 19.482 s is aggregate wall time for this diagnostic, not simulator
time or a measured peak-memory figure.

## Tested configuration

- Python 3.12.14; Qiskit 2.6.1; Qiskit Aer 0.18.2.
- `PYTHONHASHSEED=0`; `seed_transpiler=12345`.
- Basis `rz, sx, x, cx`; no coupling map or initial layout.
- Approved precompilation: optimization level 2. Tier 5 supplies its Aer
  backend to the transpiler; Tier 6 uses the generic target, as its source
  specifies. Official scoring is optimization level 1.
- `QISKIT_PARALLEL=FALSE`, `OMP_NUM_THREADS=2`,
  `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`; `RAYON_NUM_THREADS` unset.

The JSON records recursive pass/controller classes, selected stable
configuration fields, and controller function qualified names. No layout,
routing, SABRE, or StochasticSwap pass was present in the generated flows.
This does **not** establish that all numerical synthesis paths are immune
to implementation/platform differences. The manifest omits opaque target
internals and Python object addresses; its hash is not a complete binary
environment fingerprint. The Tier 5 backend/basis warning is the existing
Qiskit configuration warning, not a Checker flag.

## Results

For each of Tier 5 and Tier 6, two fresh worker processes compared direct
construction against a QPY round trip *before* production precompilation.
Each compiled result then followed the official recorder's name/metadata
canonicalization and QPY transport before the scoring transpilation.

All four workers completed. Within each tier, ordered structural digests,
instruction histograms and metrics matched between the fresh processes.
Within each worker, the direct and round-tripped paths had exactly equal
native and scored primitive sequences, wire maps, numeric parameters and
global phase. Numeric values were compared transiently; only equality
Booleans were saved. This comparison covers the measured primitive circuit
types here, not arbitrary circuits containing control flow or classical
conditions.

| Tier/stage | CX | Depth | Total gates | Active qubits |
|---|---:|---:|---:|---:|
| 5 production precompile | 11,000 | 19,703 | 28,413 | 19 |
| 5 official scoring compile | 10,950 | 19,703 | 28,363 | 19 |
| 6 nominal production precompile | 3,000 | 5,691 | 8,680 | 22 |
| 6 nominal official scoring compile | 3,000 | 5,691 | 8,680 | 22 |

Tier 6 uses the public default **12-round builder only**, without its real
measurement/calibration path. It is a compilation hypothesis test, not
proof of which circuit a particular solver run executes or the Checker
selects. The separate actual-execution trace is needed for that conclusion.

## Fingerprint scope and interpretation

This diagnostic's versioned structural digest includes ordered public gate
class/name, qubit/classical-bit indices and parameter arity. It deliberately
excludes parameter/global-phase values, opaque definitions, labels,
metadata and register UUIDs. Generated `circuit-<number>` names are
canonicalized. Consequently it is a structural fingerprint, **not** a
unitary-equivalence certificate. The schema is independent of the shared
four-stage diagnostic helper and its digest values must not be compared
across schemas.

Top-level constructed-circuit metrics count composite gates as composite
instructions. Their apparent zero two-qubit-gate count is not a scoring
claim. Official scoring metrics in the table are computed only after
transpilation to the stated basis.

These experiments did not reproduce serialization-induced variation or
same-host process-order variation for the tested builders. They do not
reconstruct the unavailable historical ordered circuits, native-library
state or actual pass traces, and therefore do not establish the historical
root cause. In particular, the coincidence between Tier 5's current native
total of 28,413 and its historical scored total of 28,413 does not establish
an accounting error: their respective CX counts differ.
