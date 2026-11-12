# Environment inventory and historical comparability

`collect_environment.py` generated `full-environment.json` using the same
Python executable as the tests. It imported installed public libraries and
read their metadata/files; it ran no Aer job and no transpiler. All 13
installed distributions and 16 actually imported native extension modules
are recorded. Only the explicit environment-variable allowlist is saved.

## Current runtime

- Python **3.12.14**, Qiskit **2.6.1**, Qiskit Aer **0.18.2**.
- NumPy 2.5.4; SciPy 1.18.1; rustworkx 0.18.1.
- Linux 6.18.57, x86_64, glibc 2.41.
- Intel Xeon Platinum 8370C; process affinity covers CPUs 0–4. The cgroup
  CPU quota is 400000/100000 (four CPU-equivalents), so the host CPU count
  alone is not the usable quota.
- Cgroup memory limit: 17,179,869,184 bytes (16 GiB). Memory-current and
  memory-peak values in this inventory are shared cgroup snapshots and must
  not be presented as per-Checker or per-tier peak memory.

The current **collector parent** has `PYTHONHASHSEED` and thread-count
variables unset. That is intentionally recorded rather than invented.
The unchanged official launcher explicitly sets `PYTHONHASHSEED=0` and
`QISKIT_PARALLEL=FALSE` for each child worker; actual test manifests also
record any outer runner thread settings. The standalone compilation probe
sets its own documented thread/hash environment. These are different
process scopes, not conflicting observations.

Actual imported binary SHA-256 values:

| Module | SHA-256 |
|---|---|
| `qiskit._accelerate` | `b0f6b3c2e7ac43efa4c5c46a52210d35df5f74c9cb500aec25a5930affb0e424` |
| `qiskit_aer.backends.controller_wrappers` | `1e2e873f0e5fe545b255b6083d2ca08a0d00b84797d7dde2cb5edc52f64750df` |

These hashes identify observed files. They do not establish that historical
Windows/Linux wheel builds or every linked shared library were identical.

## Historical evidence

The previous read-only comparison was retrieved directly from:

- Commit `e49ed058ed83b43866ffca4ca9b9785e3f9301ed`.
- `docs/v63-metrics-reconciliation/environmental-comparison.json`.
- Raw SHA-256 `9a5aa9c2e5c65333dbf979a3cb227054a6db430ea59504682c060324d4ee5eab`.

All seven historical cited files were reread from their pinned commits and
their raw SHA-256 values matched the previous comparison. All seven
protected-source records were checked against both approved Git bytes and
the fresh official extraction; all match. This includes the three affected
solutions, Tier 5 GF(2) pass, Checker, scoring configuration and requirements.

The recorded historical Python version is **3.12.10**, different from the
current patch version. Historical Qiskit/Aer version strings match
2.6.1/0.18.2. The historical actual NumPy version, full native wheel hashes,
CPU/BLAS configuration and thread environment were not independently
recorded for those v6.3 runs. A requirement pin or an earlier v6.1 package
freeze does not prove the later actual binary environment.

The immutable solver sources specify precompilation level 2 and
`seed_transpiler=12345`; the unchanged scoring configuration specifies level
1, the same seed, ordered basis `rz,sx,x,cx`, and no coupling map/initial
layout. Source/config identity is supported independently of the missing
historical binary inventory.

Thus, the environments are **not identical or fully documented**. The
Python patch difference and unavailable binary details are plausible
investigation leads, not demonstrated causes of the gate/depth variance.

## Fingerprint namespaces

The pass-manager probe's circuit digest uses its own ordered public
operation-class/name/wire-map/parameter-arity schema. The pass-manager tree
digest summarizes recursive classes and selected configuration fields.
The four-stage trace uses the separate shared fingerprint helper. Compare
SHA values only within the same schema; none of these deliberately
parameter-redacted structural digests alone proves unitary equivalence.
