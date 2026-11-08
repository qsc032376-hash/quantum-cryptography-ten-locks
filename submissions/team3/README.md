# Team 3 — Ten Locks, One Message

**Members:** Sicheng Qian, Junqi Sheng, Youyang Shang, Junrui Yu
**Tiers attempted:** 1–10
**Write-up:** [WRITEUP.md](WRITEUP.md)

Our verified v5 solution uses Qiskit Aer to measure each challenge's quantum structure, then applies classical recovery and cryptographic verification. In a local full-package run of the official Checker, all ten tiers were `full`, all plaintext SHA-256 hashes matched, all scoring metrics were valid, and no flags were recorded. This is a local verification result, not a competition score or a hardware demonstration.

The ten selected scoring circuits sum to 241,211 two-qubit gates, 621,301 per-tier depth, and 711,705 total gates. These are sums across separate tiers. The README in the repository root explains setup and reproducibility; this team README and the linked write-up are intended for the competition's `submissions/team3/` folder alongside the verified v5 solution modules. This documentation branch contains these two handoff documents only; the verified code resides at `release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d`.

To reproduce the official check after placing these documents beside the verified team modules in a fresh challenge checkout, install the pinned `requirements.txt` from the repository root and run `python tools/check_submission.py submissions/team3`. The check runs real Aer circuits and may take time. We do not expose hidden keys, measurement witnesses, or decrypted messages in this shareable README.
