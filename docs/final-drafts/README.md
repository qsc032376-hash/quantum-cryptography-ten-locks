# Quantum Cryptography: Ten Locks, One Message

**Team 3:** Sicheng Qian, Junqi Sheng, Youyang Shang, Junrui Yu

**Institution:** The Ohio State University

**Event:** Qiskit Fall Fest 2026 — Quantum Cryptography Challenge

**Tiers attempted:** 1–10

**Write-up:** [WRITEUP.md](WRITEUP.md)

## Result

All ten tiers pass the unchanged official Checker: **10/10 FULL**, all ten plaintext
SHA-256 hashes match, every tier executed a circuit on Aer, and there were **no flags
and no timeouts**. The ten selected scoring circuits total:

| Metric | v6.3 result |
|---|---:|
| Two-qubit gates | **103,166** |
| Sum of per-tier depths | **217,625** |
| Total gates | **294,982** |

These figures were independently reproduced from the submitted ZIP in a clean checkout
of the official challenge repository (Python 3.12.10, Qiskit 2.6.1, Aer 0.18.2).
They are simulator results; they are not a hardware speedup claim.

## Contents

- `tier01/` through `tier10/`: each contains `solution.py` and the tier-specific
  modules that solution imports.
- Shared classical modules at the team root: keystream, toy cipher, RSA,
  Diffie–Hellman and Tier 7 decryption.
- `tier09/public_operations.json` and `tier10/public_operations.json`: public
  operation caches required at runtime.
- [WRITEUP.md](WRITEUP.md): algorithms, circuit construction, measurement-to-key
  recovery, resource tables, optimization evidence and limitations.

## Per-tier scoring resources

These are the official post-transpilation metrics for the one circuit the Checker
selects per tier (most two-qubit gates, then depth), not the total work over all shots.

| Tier | Algorithm | 2Q gates | Depth | Total gates | Active qubits | Status |
|---:|---|---:|---:|---:|---:|---|
| 1 | Bernstein–Vazirani | 151 | 44 | 298 | 25 | FULL |
| 2 | BB84 | 0 | 3 | 3 | 1 | FULL |
| 3 | Deutsch–Jozsa | 7,808 | 8,771 | 19,497 | 7 | FULL |
| 4 | Simon | 183 | 195 | 455 | 20 | FULL |
| 5 | Grover search | 10,950 | 19,703 | 28,413 | 19 | FULL |
| 6 | Multi-target Grover | 3,000 | 5,715 | 8,752 | 22 | FULL |
| 7 | Quantum phase estimation | 209 | 154 | 536 | 15 | FULL |
| 8 | Shor order finding, N = 35 | 7,856 | 18,804 | 22,861 | 18 | FULL |
| 9 | Shor order finding, N = 77 | 34,186 | 71,632 | 102,830 | 22 | FULL |
| 10 | Quantum discrete logarithm | 38,823 | 92,604 | 111,337 | 19 | FULL |
| **Sum** | **Ten separate circuits** | **103,166** | **217,625** | **294,982** | — | **10/10** |

The depth sum is not the depth of one combined circuit. Simplicity is relative to
other teams' eligible metrics and can only be final after the deadline.

## Reproduction

Use a fresh copy of the official challenge repository and Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python tools/check_setup.py
```

Place the complete `team3/` folder from the submission archive under `submissions/`,
then run the unchanged official Checker:

```bash
python tools/check_submission.py submissions/team3 --out reports/team3
```

Inspect `report.md` and `report.json` for hash status, circuit execution, flags and
metrics. `--metrics-only` skips the hash check and is not a correctness test.

## Evidence and scope

- Every `solve()` returns a plaintext that the official Checker hashes; matched hashes
  alone do not establish the recovery method, so the write-up identifies the measured
  outcomes and the classical post-processing used for each tier.
- Circuit diagrams in the write-up are logical block diagrams; the scored circuit is
  the exact circuit passed to Aer, not `build_circuit()`.
- The v6.3 changes are confined to Tier 5 and Tier 8; Tier 9 and Tier 10 retain their
  independently validated v6.2 implementations.
- No physical quantum hardware was used. All results are ideal-simulation results with
  all-to-all transpilation; noise, routing and fault-tolerance costs are discussed in
  the analysis.
