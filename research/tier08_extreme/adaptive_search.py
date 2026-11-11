"""Additional user-authorized bounded public-coordinate search, no Aer.

The original 500-configuration evidence is immutable. This second run explores
at most 4,000 previously unseen coordinate configurations using seeded local
neighborhoods and random perturbations. Full-domain verification remains exact.
"""
import argparse
from collections import deque
import hashlib
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mixed import network, table, verify, cost

SEED = 2026111109
MULTIPLIERS = (2, 4, 11, 16)


def canonical(config):
    return json.dumps(config, sort_keys=True, separators=(',', ':'))


def neighbors(config):
    """Single bit-coordinate swaps, XOR changes and exact policy variants."""
    p = config['permutation']
    for i in range(6):
        for j in range(i + 1, 6):
            q = p.copy(); q[i], q[j] = q[j], q[i]
            yield {**config, 'permutation': q}, 'bit_swap'
    for i in range(6):
        yield {**config, 'xor_mask': config['xor_mask'] ^ (1 << i)}, 'xor_single'
    for i in range(6):
        for j in range(i + 1, 6):
            yield {**config, 'xor_mask': config['xor_mask'] ^ (1 << i) ^ (1 << j)}, 'xor_double'
    yield {**config, 'inverse': not config['inverse']}, 'inverse_direction'
    yield {**config, 'descending': not config['descending']}, 'target_order'
    for policy in ('fixed', 'short_set', 'short_both'):
        if policy != config['policy']:
            yield {**config, 'policy': policy}, 'guard_policy'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--configs', type=int, default=4000)
    parser.add_argument('--seconds', type=float, default=240)
    args = parser.parse_args()
    if not 0 < args.configs <= 4000:
        raise ValueError('Additional user-authorized configuration cap is 4000')
    start = time.perf_counter()
    rng = random.Random(SEED)
    original_path = HERE/'search.json'
    original = json.loads(original_path.read_text())
    source_digest = hashlib.sha256(Path(__file__).read_bytes() + (HERE/'mixed.py').read_bytes()).hexdigest()
    output_path = HERE/'adaptive_search.json'
    prior = json.loads(output_path.read_text()) if output_path.exists() else {}
    cached = {row['cache_key']: row for row in prior.get('results', [])}
    original_keys = {canonical(c) for c in original['configurations']}
    queued = set(original_keys)
    queue = deque()
    results = []
    top = {str(d): list(original['top_candidates'][str(d)][:10]) for d in MULTIPLIERS}
    best = {str(d): original['best'][str(d)] for d in MULTIPLIERS}
    fingerprints = set()
    cache_hits = 0
    all_checks = 0
    checkpoints = []

    def enqueue(config, kind, parent=None, front=False):
        key = canonical(config)
        if key in queued:
            return
        queued.add(key)
        item = config, kind, parent
        queue.appendleft(item) if front else queue.append(item)

    # Initial beam is every retained top-15 source configuration, not only one
    # winner; neighborhoods overlap and are deduplicated before evaluation.
    for d in ('11', '16', '4', '2'):
        for row in original['top_candidates'][d]:
            for config, kind in neighbors(row['configuration']):
                enqueue(config, kind, {'multiplier':int(d), 'source_fingerprint':row['fingerprint']})

    def save():
        transfers = []
        for source, destination in ((11,16),(16,11)):
            row = best[str(source)]
            ops = tuple(tuple(op) for op in reversed(row['operations']))
            evidence = verify(ops, table(destination))
            transfers.append({'multiplier':destination,'source_multiplier':source,
                              'source_fingerprint':row['fingerprint'],
                              'source_configuration':row['configuration'],
                              'operations':ops,'estimated_cx':cost(ops),
                              'fingerprint':hashlib.sha256(repr(ops).encode()).hexdigest(),
                              **evidence})
        payload = {
            'authorization':'User requested additional attempts within the original one-hour session; original 500 cap expanded by at most 4000 new coordinate configurations.',
            'seed':SEED,'original_configuration_count':len(original_keys),
            'additional_configuration_budget':args.configs,
            'additional_configurations_evaluated':len(results),
            'total_distinct_configurations':len(original_keys)+len(results),
            'configuration_disjoint_from_original':True,
            'source_sha256':source_digest,
            'original_search_json_sha256':hashlib.sha256(original_path.read_bytes()).hexdigest(),
            'source_fingerprint_semantics':'sha256(adaptive_search.py bytes + mixed.py bytes)',
            'cache_key_semantics':'sha256(canonical JSON [source fingerprint, complete configuration]); multiplier subresults included',
            'cache_hits':cache_hits,'unique_networks':len(fingerprints),
            'symbolic_network_checks':all_checks,'all_symbolic_and_inverse_pass':True,
            'results':results,'best':best,'top_candidates':top,'inverse_transfer':transfers,
            'checkpoints':checkpoints,'elapsed_seconds':time.perf_counter()-start,
            'complete':len(results)==args.configs,
            'estimated_cost_note':'Isolated dirty-MCX/fanout proxy; not official whole-circuit metrics. No Aer or secret recovery executed.',
        }
        tmp = output_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(payload,separators=(',',':'))+'\n')
        tmp.replace(output_path)

    while len(results) < args.configs and time.perf_counter()-start < args.seconds:
        # Interleave fresh random multi-moves with beam descendants, preventing
        # all effort from being spent in one local coordinate neighborhood.
        if len(results) % 5 == 0 or not queue:
            d = rng.choice(('11','16','4','2'))
            parent_row = rng.choice(top[d][:5])
            config = dict(parent_row['configuration'])
            config['permutation'] = config['permutation'].copy()
            for _ in range(rng.randint(1,3)):
                i,j = rng.sample(range(6),2)
                config['permutation'][i],config['permutation'][j] = config['permutation'][j],config['permutation'][i]
            config['xor_mask'] ^= rng.randrange(64)
            config['inverse'] = bool(rng.randrange(2))
            config['descending'] = bool(rng.randrange(2))
            config['policy'] = rng.choice(('fixed','short_set','short_both'))
            enqueue(config,'seeded_multi_move',{'multiplier':int(d),'source_fingerprint':parent_row['fingerprint']},front=True)
        if not queue:
            continue
        config, method, parent = queue.popleft()
        index = len(results)
        cache_key = hashlib.sha256(json.dumps([source_digest,config],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        record = {'configuration_index':index,'configuration':config,'method':method,
                  'parent':parent,'cache_key':cache_key,'networks':{}}
        improvements = []
        previous = cached.get(cache_key)
        for d in MULTIPLIERS:
            ops = network(d,config)
            evidence = verify(ops,table(d))
            all_checks += 1
            fingerprint = hashlib.sha256(repr(ops).encode()).hexdigest()
            estimate = cost(ops)
            sub = {'estimated_cx':estimate,'operation_count':len(ops),
                   'fingerprint':fingerprint,**evidence}
            if previous:
                old = previous['networks'][str(d)]
                if old['fingerprint'] != fingerprint or old['estimated_cx'] != estimate:
                    raise AssertionError('Deterministic cache replay mismatch')
            fingerprints.add(fingerprint)
            record['networks'][str(d)] = sub
            candidate = {'multiplier':d,'configuration_index':index,'configuration':config,
                         'operations':ops,'cache_key':cache_key,**sub}
            if not any(r['fingerprint']==fingerprint for r in top[str(d)]):
                top[str(d)].append(candidate)
                top[str(d)].sort(key=lambda r:(r['estimated_cx'],r['operation_count'],r['fingerprint']))
                top[str(d)] = top[str(d)][:10]
            current = best[str(d)]
            if (estimate,len(ops)) < (current['estimated_cx'],current['operation_count']):
                best[str(d)] = candidate
                improvements.append((d,fingerprint))
        if previous:
            cache_hits += 1
        results.append(record)
        for d,fingerprint in improvements:
            children = list(neighbors(config))
            rng.shuffle(children)
            for child, kind in children:
                enqueue(child,kind,{'multiplier':d,'source_fingerprint':fingerprint},front=True)
        if improvements or len(results)%200 == 0:
            checkpoints.append({'configurations':len(results),
                                'best_estimated_cx':{d:r['estimated_cx'] for d,r in best.items()},
                                'elapsed_seconds':time.perf_counter()-start})
            save()
            print('additional',len(results),'best',{d:r['estimated_cx'] for d,r in best.items()},
                  'elapsed',round(time.perf_counter()-start,2),flush=True)
    save()


if __name__ == '__main__':
    main()
