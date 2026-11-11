"""Run five fresh Aer seeds per changed tier on the ZIP payload."""
import argparse
from hashlib import sha256
from pathlib import Path
import importlib.util
import json

OUT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("trials", OUT.parent/"v61-evidence/reliability.py")
trials = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trials)


def run(root):
    manifest = json.loads((OUT/"zip-manifest.json").read_text())
    for name,digest in manifest["contents"].items():
        assert sha256((root/"submissions"/name).read_bytes()).hexdigest() == digest
    records=[]
    for tier,first in ((5,5301),(8,8301)):
        for seed in range(first,first+5):
            row=trials.trial(root,tier,seed)
            records.append(dict(tier=tier,seed=seed,**row))
            (OUT/"seeds.json").write_text(json.dumps(records,indent=2)+"\n")
            print(tier,seed,row["status"],flush=True)
    assert all(r["status"]=="PASS" and r["hash_ok"] for r in records)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("official_root",type=Path)
    run(p.parse_args().official_root.resolve())
