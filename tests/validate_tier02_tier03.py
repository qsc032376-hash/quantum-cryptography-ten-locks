"""Verify one real solve in a fresh process; emit only aggregate diagnostics."""

import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from common import is_correct
from tools.check_submission import load_solution


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def record_runs():
    original_run = AerSimulator.run
    counts = Counter()

    def run(simulator, circuits, *args, **kwargs):
        # Count only; Channel composes the hidden input preparation internally.
        experiments = 1 if isinstance(circuits, QuantumCircuit) else len(circuits)
        counts["aer_batches"] += 1
        counts["circuits"] += experiments
        counts["shots"] += experiments * kwargs.get("shots", simulator.options.shots)
        return original_run(simulator, circuits, *args, **kwargs)

    return counts, patch.object(AerSimulator, "run", new=run)


def validate_tier02(solution):
    helper = solution.helper
    channel = helper.Channel
    require(not channel.log, "Use a fresh process for Tier 2")
    original_init = channel.__init__
    original_receive = channel.receive_all
    original_finish = channel.finish
    original_reconcile = helper.reconcile
    names, events, measured, reports, candidates = {}, [], {}, {}, {}
    reconciliations = []

    def init(instance, name):
        names[id(instance)] = name
        events.append((name, "construct"))
        original_init(instance, name)

    def receive(instance, circuits):
        name = names[id(instance)]
        require(events.count((name, "construct")) == 1 and name not in measured,
                "Duplicate Channel construction or receive")
        events.append((name, "receive_all"))
        patterns = [tuple(item.operation.name for item in c.data) for c in circuits]
        require(all(p in (("measure",), ("h", "measure")) for p in patterns),
                "Invalid public Bob measurement circuit")
        outcomes = original_receive(instance, circuits)
        measured[name] = ([int("h" in pattern) for pattern in patterns], outcomes)
        return outcomes

    def finish(instance):
        name = names[id(instance)]
        require(name in measured and name not in reports, "Incorrect Channel.finish order")
        events.append((name, "finish"))
        data = original_finish(instance)
        bob, outcomes = measured[name]
        checked = {int(index): bit for index, bit in data["check_bits"].items()}
        matched = {i for i, basis in enumerate(bob) if basis == data["alice_bases"][i]}
        sample = matched & checked.keys()
        require(bool(sample), "No matched public checks")
        errors = sum(outcomes[i] != checked[i] for i in sample)
        retained = matched - checked.keys()
        reports[name] = {
            "check_errors": errors, "check_samples": len(sample),
            "qber": float(Fraction(errors, len(sample))), "retained": len(retained),
        }
        candidates[name] = ({i: outcomes[i] for i in retained}, data["reconcile"])
        return data

    def reconcile(bits, public_data):
        require(set(reports) == set(helper.LINKS), "Reconciled before both links finished")
        rates = {name: Fraction(stats["check_errors"], stats["check_samples"])
                 for name, stats in reports.items()}
        require(len(set(rates.values())) == 2, "QBER tie")
        selected = min(rates, key=rates.get)
        require((bits, public_data) == candidates[selected], "Incorrect reconciliation inputs")
        reconciliations.append(selected)
        return original_reconcile(bits, public_data)

    runs, aer = record_runs()
    with (patch.object(channel, "__init__", new=init),
          patch.object(channel, "receive_all", new=receive),
          patch.object(channel, "finish", new=finish),
          patch.object(helper, "reconcile", new=reconcile),
          aer):
        hash_ok = is_correct(2, solution.solve())

    require(hash_ok, "Tier 2 SHA-256 mismatch")
    for name in helper.LINKS:
        require([event for link, event in events if link == name]
                == ["construct", "receive_all", "finish"], "Channel order or count mismatch")
    expected = {(name, i) for name in helper.LINKS for i in range(len(measured[name][0]))}
    actual = [(name, i) for name, i, _ in channel.log]
    require(len(actual) == len(expected) and set(actual) == expected, "Missing or repeated qubits")
    require(runs == {"aer_batches": 2, "circuits": 2048, "shots": 2048},
            "Tier 2 Aer execution count mismatch")
    require(len(reconciliations) == 1, "Expected one reconciliation")
    return {**runs, "hash_ok": hash_ok, "channel_calls": events, "links": reports,
            "repeat_measurements": len(actual) - len(set(actual)),
            "reconcile_calls": len(reconciliations), "selected_link": reconciliations[0]}


def validate_tier03(solution):
    original_build = solution.build_circuit
    original_classify = solution.measurement_to_bit
    original_decrypt = solution._load_decrypt()
    indices, calls, measured_flags = [], [], []
    decrypt_calls = 0

    def build(index=0):
        circuit = original_build(index)
        indices.append(index)
        calls.append(solution.helper.count_oracle_calls(circuit))
        return circuit

    def classify(bits):
        flag = original_classify(bits)
        measured_flags.append(flag)
        return flag

    def decrypt(tier, key_bits, ciphertext_hex):
        nonlocal decrypt_calls
        decrypt_calls += 1
        require(tier == 3 and len(measured_flags) == 24
                and key_bits == "".join(measured_flags), "Incorrect measured key transfer")
        return original_decrypt(tier, key_bits, ciphertext_hex)

    runs, aer = record_runs()
    with (patch.object(solution, "build_circuit", new=build),
          patch.object(solution, "measurement_to_bit", new=classify),
          patch.object(solution, "_load_decrypt", return_value=decrypt),
          aer):
        hash_ok = is_correct(3, solution.solve())

    require(hash_ok, "Tier 3 SHA-256 mismatch")
    require(indices == list(range(24)) and calls == [1] * 24, "Oracle order or count mismatch")
    require(runs == {"aer_batches": 1, "circuits": 24, "shots": 24},
            "Tier 3 Aer execution count mismatch")
    require(decrypt_calls == 1, "Expected one classical decryption")
    return {**runs, "hash_ok": hash_ok, "oracle_order_ok": True,
            "oracle_calls_total": sum(calls), "oracle_calls_per_circuit": 1,
            "classical_decrypt_calls": decrypt_calls}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tier", type=int, choices=(2, 3))
    parser.add_argument("--team-dir", type=Path, default=ROOT / "submissions/team3")
    args = parser.parse_args()
    path = args.team_dir.resolve() / f"tier{args.tier:02d}" / "solution.py"
    sys.path.insert(0, str(path.parent))  # Match the Checker worker import path.
    solution = load_solution(path)
    started = time.perf_counter()
    validate = {2: validate_tier02, 3: validate_tier03}[args.tier]
    result = validate(solution)
    print(json.dumps({"tier": args.tier, "seconds": round(time.perf_counter() - started, 3),
                      **result}, sort_keys=True))


if __name__ == "__main__":
    main()
