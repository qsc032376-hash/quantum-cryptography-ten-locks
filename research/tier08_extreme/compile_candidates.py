"""Stage B: at most 60 exact public multiplier circuits in official basis."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.tier08_extreme.emitter import build_from_operations, symbolic
from research.tier08_extreme.screen import score
from research.tier08_extreme.mixed import table, cost

HERE = Path(__file__).resolve().parent


def key(ops):
    return hashlib.sha256(json.dumps(ops, separators=(',', ':')).encode()).hexdigest()


def main():
    search = json.loads((HERE/'search.json').read_text())
    boolean = json.loads((HERE/'boolean_results.json').read_text())
    results = []
    selected = {}
    start = time.perf_counter()
    for d in (2, 4, 11, 16):
        candidates = []
        seen = set()

        def add(label, ops):
            digest = key(ops)
            if digest not in seen:
                seen.add(digest)
                candidates.append({'family': label, 'operations': ops, 'fingerprint': digest,
                                   'estimated_cx': cost(ops)})

        for row in search['top_candidates'][str(d)][:3]:
            add('affine', row['operations'])
        refined = sorted((r for r in boolean['refinements'] if r['multiplier'] == d), key=lambda r:r['after'])
        for row in refined[:10]:
            add('boolean_refined', row['operations'])
        if d in (11, 16):
            other = 16 if d == 11 else 11
            opposite = sorted((r for r in boolean['refinements'] if r['multiplier'] == other), key=lambda r:r['after'])
            for row in opposite[:2]:
                add('inverse_transfer', list(reversed(row['operations'])))
        for row in refined[10:]:
            if len(candidates) >= 15:
                break
            add('boolean_refined', row['operations'])
        for row in search['top_candidates'][str(d)][3:]:
            if len(candidates) >= 15:
                break
            add('affine', row['operations'])
        candidates = candidates[:15]
        assert len(candidates) <= 15
        for index, row in enumerate(candidates):
            ops = row['operations']
            assert symbolic(ops) == table(d)
            assert symbolic(list(reversed(ops))) == [table(d).index(x) for x in range(64)]
            record = {'multiplier': d, 'index': index, **row,
                      **score(build_from_operations(ops)), 'symbolic_and_inverse': True}
            results.append(record)
            print(d,index,record['family'],record['metrics'],flush=True)
        chosen = min((r for r in results if r['multiplier'] == d),
                     key=lambda r:(r['metrics']['two_qubit_gates'],r['metrics']['depth'],r['metrics']['total_gates']))
        selected[str(d)] = chosen['operations']
        payload = {'budget':60, 'compiled':len(results), 'emission':{'mode':'dirty','pivot':'first','allocation':'work_first'},
                   'elapsed_seconds':time.perf_counter()-start,'selected':selected,'results':results,
                   'source_inputs':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('search.json','boolean_results.json')}}
        (HERE/'compiled_candidates.json').write_text(json.dumps(payload,indent=2)+'\n')
    (HERE/'scored_selected.json').write_text(json.dumps(selected,indent=2)+'\n')


if __name__ == '__main__':
    main()
