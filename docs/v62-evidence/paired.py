"""Run the unchanged v6.1 fresh-process seed harness against both extracted trees."""
import argparse
import importlib.util
import json
from pathlib import Path
import hashlib

OUT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v61_trials", OUT.parent/"v61-evidence/reliability.py")
TRIALS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIALS)


def main(base, candidate):
    reports = {}
    for label, folder in (("baseline","baseline-checker"),("candidate","full-checker")):
        report = json.loads((OUT/folder/"report.json").read_text())
        assert set(report["tiers"]) == set(map(str,range(1,11)))
        assert all(row["status"]=="full" and row["hash_ok"] and row["circuit_executed"]
                   and row["metrics_status"]=="ok" and not row["flags"]
                   for row in report["tiers"].values())
        reports[label] = report["tiers"]["9"]["metrics"]
    audit = json.loads((OUT/"source-audit.json").read_text())
    for path,digest in audit["source_sha256"].items():
        assert hashlib.sha256((candidate/path).read_bytes()).hexdigest() == digest
    pairs = []
    for idx,seed in enumerate(range(9200,9250,10)):
        for label,root in (("baseline",base),("candidate",candidate))[::1 if idx%2==0 else -1]:
            row = TRIALS.trial(root,9,seed)
            calls = row.get("actual_forwarded_calls", [])
            if not 1 <= len(calls) <= 2 or any(call["shots"] != 64 for call in calls):
                row["status"] = "FAIL"
            pairs.append(dict(variant=label,seed=seed,batches=len(calls),**row))
            (OUT/"paired.json").write_text(json.dumps(dict(official_metrics=reports,runs=pairs),indent=2)+"\n")
            print(seed,label,row["status"],flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("base",type=Path)
    p.add_argument("candidate",type=Path)
    args=p.parse_args()
    main(args.base.resolve(),args.candidate.resolve())
