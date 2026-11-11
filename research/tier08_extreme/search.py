"""Bounded deterministic cheap search; no quantum solve or hidden data read."""
import argparse
import hashlib
import itertools
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mixed import network, table, verify, cost

SEED = 2026111108
MULTIPLIERS = (2, 4, 11, 16)
BASELINE_SHA = "c4455782ea9388d5897fc27270f42dd3786ed35d"


def configurations(limit=500):
    rng = random.Random(SEED)
    configs = []
    seen = set()

    def add(permutation, flip, inverse, policy, descending):
        config = {"permutation": list(permutation), "xor_mask": flip,
                  "inverse": inverse, "policy": policy, "descending": descending}
        key = json.dumps(config, sort_keys=True)
        if key not in seen:
            seen.add(key)
            configs.append(config)

    # Controlled ablations: 12 exact families in original coordinates.
    for policy, inverse, descending in itertools.product(
            ("fixed", "short_set", "short_both"), (False, True), (False, True)):
        add(range(6), 0, inverse, policy, descending)
    # Deliberate reversals/complements, followed by reproducible diverse search.
    for flip in (63, 21, 42, 0):
        for policy, inverse in itertools.product(("short_set", "short_both"), (False, True)):
            add(tuple(reversed(range(6))), flip, inverse, policy, False)
    while len(configs) < limit:
        permutation = list(range(6))
        rng.shuffle(permutation)
        flip = 0 if len(configs) % 4 == 0 else rng.randrange(64)
        add(permutation, flip, bool(rng.randrange(2)),
            rng.choice(("fixed", "short_set", "short_both")), bool(rng.randrange(2)))
    return configs[:limit]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", type=int, default=500)
    args = parser.parse_args()
    if not 1 <= args.configs <= 500:
        raise ValueError("Stage A budget is at most 500 configurations")
    started = time.perf_counter()
    source_digest = hashlib.sha256(Path(__file__).read_bytes() + (HERE/'mixed.py').read_bytes()).hexdigest()
    output_path = HERE/'search.json'
    prior = json.loads(output_path.read_text()) if output_path.exists() else {}
    initial_source_digest = prior.get('initial_search_source_sha256', prior.get('source_sha256', source_digest))
    cached = {r['cache_key']: r for r in prior.get('results', [])}
    configs = configurations(args.configs)
    results = []
    unique = set()
    best = {}
    checkpoints = []
    cache_hits = 0

    def save():
        tops = {}
        for multiplier in MULTIPLIERS:
            distinct = {}
            for row in results:
                if row['multiplier'] == multiplier:
                    distinct.setdefault(row['fingerprint'], row)
            tops[str(multiplier)] = sorted(distinct.values(), key=lambda r:(r['estimated_cx'],r['operation_count'],r['fingerprint']))[:15]
        # 11 and 16 are public inverse multipliers modulo 35. Reversing any
        # chronological self-inverse gate list implements the inverse mapping,
        # including fixed padding. This derives alternatives from existing
        # configurations; no new coordinates or hidden answer search are used.
        inverse_transfer = []
        for source, destination in ((11, 16), (16, 11)):
            if str(source) in best:
                source_row = best[str(source)]
                operations = tuple(tuple(op) for op in reversed(source_row['operations']))
                evidence = verify(operations, table(destination))
                inverse_transfer.append({
                    "multiplier": destination, "source_multiplier": source,
                    "source_fingerprint": source_row['fingerprint'],
                    "source_configuration": source_row['configuration'],
                    "fingerprint": hashlib.sha256(repr(operations).encode()).hexdigest(),
                    "estimated_cx": cost(operations), "operations": operations,
                    "derivation": "reverse existing self-inverse gate list; 11*16 mod 35 == 1",
                    **evidence,
                })
        output = {"baseline_commit": BASELINE_SHA, "seed": SEED,
                  "source_sha256": source_digest, "configuration_budget": 500,
                  "initial_search_source_sha256": initial_source_digest,
                  "configuration_semantics": "500 distinct configurations; each applies to four public multipliers",
                  "configurations": configs[:len(results)//4], "results": results,
                  "unique_networks": len(unique), "cache_hits": cache_hits,
                  "best": best, "top_candidates": tops, "checkpoints": checkpoints,
                  "inverse_transfer": inverse_transfer,
                  "elapsed_seconds": time.perf_counter()-started,
                  "estimate_note": "Isolated exact dirty-MCX CX plus fanout; not whole-circuit scoring",
                  "all_symbolic_and_inverse_pass": all(r['symbolic_pass'] for r in results)}
        temporary = output_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(output, separators=(',', ':'))+'\n')
        temporary.replace(output_path)

    for index, config in enumerate(configs):
        for multiplier in MULTIPLIERS:
            key = hashlib.sha256(json.dumps([source_digest,multiplier,config],sort_keys=True).encode()).hexdigest()
            row = cached.get(key)
            if row is None:
                ops = network(multiplier, config)
                evidence = verify(ops, table(multiplier))
                fingerprint = hashlib.sha256(repr(ops).encode()).hexdigest()
                row = {"configuration_index": index, "configuration": config,
                       "multiplier": multiplier, "cache_key": key,
                       "fingerprint": fingerprint, "estimated_cx": cost(ops),
                       "ungrouped_estimated_cx": cost(ops,False),
                       "operation_count": len(ops), "operations": ops, **evidence}
            else:
                cache_hits += 1
            unique.add(row['fingerprint'])
            results.append(row)
            old = best.get(str(multiplier))
            if old is None or (row['estimated_cx'],row['operation_count']) < (old['estimated_cx'],old['operation_count']):
                best[str(multiplier)] = row
        if index + 1 in (12,28,64,128,256,500,args.configs):
            checkpoints.append({"configurations":index+1,
                                "selected_fingerprints":{d:r['fingerprint'] for d,r in best.items()},
                                "estimated_weighted_cx":sum(best[str(d)]['estimated_cx']*(5 if d in (11,16) else 1) for d in MULTIPLIERS)})
            save()
            print('checked',index+1,'best estimated CX',{d:r['estimated_cx'] for d,r in best.items()},'elapsed',round(time.perf_counter()-started,2),flush=True)
    save()


if __name__ == '__main__':
    main()
