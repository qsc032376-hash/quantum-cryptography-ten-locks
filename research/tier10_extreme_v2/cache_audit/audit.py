"""Tier 10 cache provenance audit: raw-byte hashes and circuit equivalence."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

from submissions.team3.tier08.modular import permutation_table  # noqa: E402
from submissions.team3.tier10 import global_synthesis  # noqa: E402

TARGETS = [
    ("v6.1", "0c043a4", "submissions/team3/tier10/public_operations.json"),
    ("v6.2", "aee41fb", "submissions/team3/tier10/public_operations.json"),
    ("research_7edfe87", "7edfe87", "research/tier10_global/candidate.json"),
    ("ultra_heavy_9ca45f3", "9ca45f3", "research/tier10_ultra_heavy/affine_candidate.json"),
]
CACHE_SOURCES = [
    ("v6.1", "0c043a4", "submissions/team3/tier10/public_operations.json"),
    ("v6.2", "aee41fb", "submissions/team3/tier10/public_operations.json"),
    ("research_7edfe87", "7edfe87", "research/tier10_global/candidate.json"),
    ("ultra_heavy_9ca45f3", "9ca45f3", "submissions/team3/tier10/public_operations.json"),
]


def blob(commit, path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def main():
    audit = {"targets": [], "operations_equal": None, "operator_checks": []}
    parsed = {}
    for name, commit, path in TARGETS + CACHE_SOURCES:
        data = blob(commit, path)
        record = {
            "name": name,
            "commit": commit,
            "path": path,
            "bytes": len(data),
            "sha256_blob_bytes": hashlib.sha256(data).hexdigest(),
            "sha1_git_blob": subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", f"{commit}:{path}"]
            ).decode().strip(),
        }
        try:
            payload = json.loads(data)
            record["json_keys"] = sorted(payload.keys())
        except Exception:
            record["json_keys"] = None
        audit["targets"].append(record)
        if "operations" in (record["json_keys"] or []):
            parsed[name] = json.loads(data)["operations"]

    names = [name for name, _, _ in CACHE_SOURCES if name in parsed]
    reference = parsed[names[0]]
    audit["operations_equal"] = all(parsed[name] == reference for name in names)
    audit["operation_fingerprints"] = {
        name: hashlib.sha256(
            json.dumps(parsed[name], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        for name in names
    }

    # Circuit-level equivalence of the canonical cache over every multiplier.
    for key, ops in sorted(reference.items(), key=lambda kv: int(kv[0])):
        d = int(key)
        table = permutation_table(d, 83, 7)
        circuit = global_synthesis.emit([tuple(op) for op in ops], 7)
        matrix = Operator(circuit).data
        ideal = np.zeros_like(matrix)
        for control in (0, 1):
            for x in range(128):
                y = table[x] if control else x
                ideal[control + (y << 1), control + (x << 1)] = 1
        audit["operator_checks"].append(
            {
                "multiplier": d,
                "padding_fixed": all(table[x] == x for x in range(83, 128)),
                "max_error": float(np.max(np.abs(matrix - ideal))),
                "inverse_max_error": float(
                    np.max(np.abs(Operator(circuit.inverse()).data - ideal.conj().T))
                ),
            }
        )

    output = Path(__file__).with_name("audit.json")
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2)[:4000])


if __name__ == "__main__":
    main()
