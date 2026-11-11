# Quantum Cryptography: Ten Locks, One Message

> **v6.3 Candidate A.** The v6 metrics and independent acceptance below describe the earlier release. This draft integrates the selected Tier 5 and Tier 8 circuits with v6.2. Independent v6.3 source and package review is pending. Both tier09/public_operations.json and tier10/public_operations.json are runtime dependencies.

**Team 3:** Sicheng Qian, Junqi Sheng, Youyang Shang, and Junrui Yu

**Institution:** The Ohio State University

**Event:** Qiskit Fall Fest 2026 — Quantum Cryptography Challenge

**Tiers attempted:** 1–10

**Write-up:** [WRITEUP.md](WRITEUP.md)

## Overview

We solved all ten tiers using quantum circuits executed on Qiskit Aer, followed by classical key recovery and decryption. The official Checker reported FULL and matching plaintext SHA-256 hashes for all ten. Youyang Shang independently reproduced the v6 runtime release candidate's results, with no flags or timeouts. Relative to v5, the sum of the ten selected circuits' two-qubit gates fell from 241,211 to 162,716 (32.54%). These are simulator results, not a demonstration of hardware speedup.

## Contents

- `tier01/` through `tier10/`: each contains `solution.py` and the tier-specific helper modules needed by that solution.
- The team directory also contains shared classical helpers for the keystream, toy cipher, RSA, Diffie–Hellman and Tier 7 decryption. These files are required alongside the tier directories.
- [WRITEUP.md](WRITEUP.md): methods, per-tier analysis, circuit diagrams, validation and scaling limitations.

## Reproduction

Use a fresh copy of the official challenge repository and Python 3.12. From its root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python tools/check_setup.py
```

Place the complete `team3/` folder from the submission archive under `submissions/`, retaining all tier and shared helper files. Then run the official full Checker from the repository root:

```bash
python tools/check_submission.py submissions/team3 --out reports/team3
```

Inspect `reports/team3/report.md` and `report.json` for hash status, circuit execution, flags and scoring metrics. The Checker selects, per tier, the executed circuit with the most two-qubit gates after official transpilation, breaking ties by depth. `python tools/check_submission.py submissions/team3 --metrics-only` runs the metrics-only mode and does not verify hashes. Probabilistic sampling and machine load can affect individual runs.

## Verified v6 results

The independently reproduced rows below are for the selected scoring circuit in each tier; all ten were FULL with matching hashes and valid metrics.

| Tier | Algorithm | Two-qubit gates | Depth | Total gates | Active qubits | Checker |
|---:|---|---:|---:|---:|---:|---|
| 1 | Bernstein–Vazirani | 151 | 44 | 298 | 25 | FULL |
| 2 | BB84 | 0 | 3 | 3 | 1 | FULL |
| 3 | Deutsch–Jozsa | 7,808 | 8,771 | 19,497 | 7 | FULL |
| 4 | Simon | 183 | 195 | 455 | 20 | FULL |
| 5 | Grover search | 14,552 | 28,132 | 40,938 | 19 | FULL |
| 6 | Multi-target Grover | 3,000 | 5,715 | 8,752 | 22 | FULL |
| 7 | Quantum phase estimation | 209 | 266 | 727 | 15 | FULL |
| 8 | Shor order finding, N = 35 | 33,904 | 96,055 | 102,561 | 18 | FULL |
| 9 | Shor order finding, N = 77 | 55,999 | 120,242 | 168,116 | 22 | FULL |
| 10 | Quantum discrete logarithm | 46,910 | 109,763 | 132,023 | 19 | FULL |
| **Sum** | **Ten separate circuits** | **162,716** | **369,186** | **473,370** | — | **10/10** |

The depth sum is not the depth of one combined circuit. Simplicity points depend on eligible competitors' results and cannot yet be calculated from these numbers alone.
