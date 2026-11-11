"""Exact bounded ESOP/Reed--Muller and commuting-network simplification.

All gates are (mask, value, target_bit), with predicate (x & mask) == value.
No gate acts on a control bit. No auxiliary line or hidden datum is used.
The external positive control is added by the emitter, not represented here.
"""
from collections import Counter
from itertools import groupby, permutations
import hashlib
import json
from pathlib import Path
import time

CX_COST = {1: 1, 2: 6, 3: 14, 4: 20, 5: 28, 6: 36}


def grouped(ops):
    for (mask, value), run in groupby(ops, lambda op: tuple(op[:2])):
        targets = 0
        for _, _, target in run:
            targets ^= 1 << target
        if targets:
            yield mask, value, targets


def cost(ops):
    """Isolated exact-MCX plus shared-predicate fanout CX estimate only."""
    return sum(CX_COST[1 + mask.bit_count()] + 2 * (targets.bit_count() - 1)
               for mask, _, targets in grouped(ops))


def mapping(ops, width=6):
    out = list(range(1 << width))
    for mask, value, target in ops:
        assert mask >> target & 1 == 0 and value & mask == value
        assert 0 <= target < width and 0 <= mask < 1 << width
        out = [x ^ (1 << target) if x & mask == value else x for x in out]
    return out


def commute(a, b):
    """Sufficient exact criterion; intentionally not a complete oracle."""
    # Contradictory shared literals cannot be changed by either target, so
    # the two predicates can never both fire, even with crossed dependencies.
    incompatible = bool((a[1] ^ b[1]) & a[0] & b[0])
    return incompatible or a[2] == b[2] or not (a[0] >> b[2] & 1 or b[0] >> a[2] & 1)


def conjugate(a, b):
    """Return a single-cube representation of chronological A B A, if known.

    If A's predicate is implied by all B controls except A's target, A
    toggles that literal whenever B's other predicate holds. Therefore the
    conjugated B has just that control polarity reversed. No initial-target
    value is assumed. Unsupported conjugations return None, not a guess.
    """
    if commute(a,b):
        return b
    ma,va,ta=a; mb,vb,tb=b
    bit=1<<ta
    if mb & bit and not ma & (1<<tb):
        remaining=mb ^ bit
        if ma & remaining == ma and vb & ma == va:
            return mb,vb ^ bit,tb
    return None


def transported_merge(ops, window=48):
    """Cancel/merge separated cubes through certified exact conjugations."""
    current=list(map(tuple,ops))
    for _ in range(30):
        winner=None
        score=cost(current),len(current)
        for i,a in enumerate(current):
            crossed=[]
            for j in range(i+1,min(len(current),i+window+1)):
                b=current[j]
                merged=merge_pair(a,b)
                if merged is not False:
                    trial=current[:i]+crossed+([] if merged is None else [merged])+current[j+1:]
                    newscore=cost(trial),len(trial)
                    if newscore < score and (winner is None or newscore < winner[0]):
                        winner=newscore,trial
                transformed=conjugate(a,b)
                if transformed is None:
                    break
                crossed.append(transformed)
        if winner is None:
            break
        current=winner[1]
    return current


def merge_pair(a, b):
    """Return exact XOR merge, False if unavailable, None for cancellation.

    Cubes that differ in one ternary literal obey x XOR !x = 1,
    1 XOR x = !x and 1 XOR !x = x. All other literals are identical.
    """
    if a[2] != b[2]:
        return False
    if a == b:
        return None
    m, v, t = a
    n, w, _ = b
    diff = (m ^ n) | ((v ^ w) & m & n)
    if diff.bit_count() != 1:
        return False
    if m & diff and n & diff:
        return m & ~diff, v & ~diff, t
    # One cube lacks this literal; keep the other but complement it.
    present_m, present_v = (m, v) if m & diff else (n, w)
    return present_m, present_v ^ diff, t


def exorlink(a, b, max_distance=3):
    """Exact ESOP telescoping identity, including distance-2/3 rewrites.

    prod(f_j) XOR prod(g_j) = XOR_i [prod(j<i,g_j) (f_i XOR g_i)
                                                   prod(j>i,f_j)].
    Each differing unary literal is one of 1,x,!x, whose XOR is the third.
    Trying each differing-variable order does not introduce work registers.
    """
    if a[2] != b[2]:
        return
    mask, value, target = a
    other_mask, other_value, _ = b
    differing = (mask ^ other_mask) | ((value ^ other_value) & mask & other_mask)
    if not 2 <= differing.bit_count() <= max_distance:
        return
    bits = [j for j in range(max(mask.bit_length(), other_mask.bit_length())) if differing >> j & 1]
    symbols_a = {j: (int(value >> j & 1) if mask >> j & 1 else -1) for j in bits}
    symbols_b = {j: (int(other_value >> j & 1) if other_mask >> j & 1 else -1) for j in bits}
    common_mask = mask & ~differing
    common_value = value & common_mask
    for ordering in permutations(bits):
        replacement = []
        for index, bit in enumerate(ordering):
            m, v = common_mask, common_value
            for at, j in enumerate(ordering):
                symbol = (symbols_b[j] if at < index else symbols_a[j])
                if at == index:
                    symbol = ({-1, 0, 1} - {symbols_a[j], symbols_b[j]}).pop()
                if symbol != -1:
                    m |= 1 << j
                    v |= symbol << j
            replacement.append((m, v, target))
        yield replacement


def cube_reduce(ops):
    """Canonical exact local ESOP reduction for one target only."""
    if not ops:
        return []
    assert len({op[2] for op in ops}) == 1
    current = sorted(op for op, n in Counter(map(tuple, ops)).items() if n % 2)
    for _ in range(50):
        best = None
        current_score = sum(CX_COST[1+op[0].bit_count()] for op in current),len(current)
        for i, a in enumerate(current):
            for j in range(i + 1, len(current)):
                b = current[j]
                merged = merge_pair(a, b)
                rewrites = [] if merged is False else [([] if merged is None else [merged])]
                rewrites.extend(exorlink(a,b))
                remaining = [op for k,op in enumerate(current) if k not in (i,j)]
                for rewrite in rewrites:
                    trial = sorted(op for op,n in Counter(remaining+rewrite).items() if n % 2)
                    score = sum(CX_COST[1+op[0].bit_count()] for op in trial), len(trial), trial
                    if score[:2] < current_score and (best is None or score < best[0]):
                        best = score, trial
        if best is None:
            return current
        current = best[1]
    return current


def commute_merge(ops, window=24):
    """Pull two equal-target cubes together through certified commuters."""
    current = list(map(tuple, ops))
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(current):
            for j in range(i + 1, min(len(current), i + window + 1)):
                b = current[j]
                merged = merge_pair(a, b)
                if merged is not False and all(commute(a, x) for x in current[i+1:j]):
                    trial = current[:i] + current[i+1:j] + ([] if merged is None else [merged]) + current[j+1:]
                    # Fanout grouping can make a syntactically shorter network dearer.
                    if (cost(trial), len(trial)) < (cost(current), len(current)):
                        current, changed = trial, True
                        break
                if not commute(a, b):
                    break
            if changed:
                break
    return current


def _truth_for_target(ops, width):
    t = ops[0][2]
    others = [j for j in range(width) if j != t]
    truth = []
    for z in range(1 << len(others)):
        x = sum(((z >> j) & 1) << wire for j, wire in enumerate(others))
        bit = 0
        for mask, value, _ in ops:
            bit ^= x & mask == value
        truth.append(int(bit))
    return t, others, truth


def reed_muller(ops, width=6):
    """Explore all 2^(w-1) exact fixed-polarity RM representations.

    A same-target run is target ^= F(other wires), so no irreversible
    assignment or extra work register is introduced. Möbius transform gives
    ANF coefficients after each polarity change; mapping the literals back
    preserves the entire reversible operator, not just initialized targets.
    """
    if len(ops) < 2:
        return list(ops)
    target, others, truth = _truth_for_target(ops, width)
    best = cube_reduce(ops)
    expansions = []
    for flip in range(len(truth)):
        coefficients = [truth[x ^ flip] for x in range(len(truth))]
        for j in range(len(others)):
            for mask in range(len(truth)):
                if mask >> j & 1:
                    coefficients[mask] ^= coefficients[mask ^ (1 << j)]
        trial = []
        for mask, coefficient in enumerate(coefficients):
            if coefficient:
                physical = sum(1 << wire for j, wire in enumerate(others) if mask >> j & 1)
                value = sum(1 << wire for j, wire in enumerate(others)
                            if mask >> j & 1 and not flip >> j & 1)
                trial.append((physical, value, target))
        expansions.append(trial)
    # Screen all32 polarities, refine the eight strongest distinct expansions.
    # This preserves a bounded resource budget for distance-3 ESOP rewrites.
    unique = {tuple(trial) for trial in expansions}
    for expansion in sorted(unique,key=lambda x:(cost(x),len(x),x))[:8]:
        trial = cube_reduce(expansion)
        if (cost(trial), len(trial), trial) < (cost(best), len(best), best):
            best = trial
    assert _truth_for_target(ops, width)[2] == (_truth_for_target(best, width)[2] if best else [0]*len(truth))
    return best


def collect_target_runs(ops, reverse=False):
    """Expose larger same-target runs using only exact commuting swaps."""
    current = list(map(tuple, ops))
    if reverse:
        current.reverse()
    i = 0
    while i < len(current):
        target = current[i][2]
        end = i + 1
        while end < len(current) and current[end][2] == target:
            end += 1
        j = end
        while j < min(len(current), end + 32):
            if current[j][2] == target and all(commute(current[j], op) for op in current[end:j]):
                current.insert(end, current.pop(j))
                end += 1
            j += 1
        i = end
    return current[::-1] if reverse else current


def regroup_commuting(ops, policy=0, reverse=False):
    """Topologically reorder a certified commutation DAG for predicate fanout.

    Every originally ordered noncommuting pair remains ordered. Any changed
    order therefore decomposes into adjacent certified commuting exchanges.
    The heuristic only chooses among ready nodes; it cannot cross a dependency.
    """
    current = list(map(tuple, ops))
    if reverse:
        current.reverse()
    successors = [[] for _ in current]
    predecessors = [0] * len(current)
    for i, a in enumerate(current):
        for j in range(i+1, len(current)):
            if not commute(a, current[j]):
                successors[i].append(j)
                predecessors[j] += 1
    ready = {i for i, n in enumerate(predecessors) if n == 0}
    result = []
    last = None
    while ready:
        counts = Counter(current[i][:2] for i in ready)
        def priority(i):
            m, v, t = current[i]
            group = (m,v)
            if policy == 0:
                return (group == last, counts[group], m.bit_count(), -i)
            if policy == 1:
                return (group == last, counts[group] * CX_COST[1+m.bit_count()], -i)
            return (group == last, -m, -v, -i)
        i = max(ready, key=priority)
        ready.remove(i)
        result.append(current[i]); last = current[i][:2]
        for j in successors[i]:
            predecessors[j] -= 1
            if predecessors[j] == 0:
                ready.add(j)
    assert len(result) == len(current)
    return result[::-1] if reverse else result


def optimize(ops, width=6):
    """Return the lowest proxy-cost verified exact network among bounded rewrites."""
    original = list(map(tuple, ops)); expected = mapping(original, width)
    best = original
    for iteration in range(3):
        previous = (cost(best), len(best))
        for reverse in (False, True):
            current = transported_merge(commute_merge(best))
            gathered = collect_target_runs(current, reverse)
            trial = []
            for _, run in groupby(gathered, lambda op: op[2]):
                trial.extend(reed_muller(list(run), width))
            trial = transported_merge(commute_merge(trial))
            options = [current, trial]
            for policy in range(3):
                options.extend(transported_merge(commute_merge(regroup_commuting(c, policy, reverse)))
                               for c in (current, trial))
            for option in options:
                if (cost(option), len(option)) < (cost(best), len(best)):
                    best = option
        if (cost(best), len(best)) == previous:
            break
    assert mapping(best, width) == expected
    inverse = [0] * len(expected)
    for x, y in enumerate(expected):
        inverse[y] = x
    assert mapping(best[::-1], width) == inverse
    return best


def self_test():
    import random
    rng = random.Random(2026111108)
    checks = 0
    # Every admissible pair of cubes on three wires, same arbitrary target.
    for target in range(3):
        cubes = [(m, v, target) for m in range(8) if not m >> target & 1
                 for v in range(8) if v & m == v]
        for a in cubes:
            for b in cubes:
                merged = merge_pair(a, b)
                if merged is not False:
                    trial = [] if merged is None else [merged]
                    assert mapping([a, b], 3) == mapping(trial, 3)
                    checks += 1
                for replacement in exorlink(a,b):
                    assert mapping([a,b],3) == mapping(replacement,3)
                    checks += 1
    all_cubes = [(m,v,t) for t in range(3) for m in range(8) if not m>>t&1
                 for v in range(8) if v&m==v]
    for a in all_cubes:
        for b in all_cubes:
            if commute(a,b):
                assert mapping([a,b],3) == mapping([b,a],3)
                checks += 1
            conjugated=conjugate(a,b)
            if conjugated is not None:
                assert mapping([a,b,a],3) == mapping([conjugated],3)
                checks += 1
    for _ in range(12):
        ops = []
        for _ in range(25):
            target = rng.randrange(6)
            mask = rng.randrange(64) & ~(1 << target)
            value = rng.randrange(64) & mask
            ops.append((mask, value, target))
        assert mapping(optimize(ops)) == mapping(ops)
        checks += 1
    return {"seed": 2026111108, "exact_checks": checks, "status": "PASS"}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("boolean_results.json"))
    parser.add_argument("--top", type=int, default=1,
                        help="Refine this many existing networks per multiplier; no new coordinates")
    args = parser.parse_args()
    started = time.perf_counter()
    source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = {"self_test": self_test(), "variants": [], "method": "Exact commuting ESOP / fixed-polarity Reed--Muller"}
    if args.input:
        data = json.loads(args.input.read_text())
        selected = data.get("operations", data.get("candidate", data.get("selected", data.get("best", {}))))
        result["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
        result["refinements"] = []
        for multiplier, value in selected.items():
            sources = data.get("top_candidates", {}).get(str(multiplier), [value])[:args.top]
            candidates = []
            for index, source in enumerate(sources):
                ops = source.get("operations", source.get("ops")) if isinstance(source, dict) else source
                optimized = optimize(ops)
                candidates.append((cost(optimized), len(optimized), index, optimized, ops))
                result["refinements"].append({"multiplier":int(multiplier),"rank":index,
                    "source_fingerprint":source.get("fingerprint") if isinstance(source,dict) else None,
                    "before":cost(ops),"after":cost(optimized),"full_mapping_and_inverse":True,
                    "operations":optimized})
                print(json.dumps({"multiplier":int(multiplier),"rank":index,
                                  "before":cost(ops),"after":cost(optimized)}),flush=True)
            _, _, index, optimized, ops = min(candidates)
            result["variants"].append({"multiplier": int(multiplier), "original_cost": cost(ops),
                                       "candidate_cost": cost(optimized), "original_gates": len(ops),
                                       "candidate_gates": len(optimized), "operations": optimized,
                                       "selected_source_rank":index,
                                       "full_64_mapping_and_inverse": True})
    result["seconds"] = time.perf_counter() - started
    result["source_sha256"] = source_sha256
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"self_test": result["self_test"], "variants": [{k:v for k,v in x.items() if k != "operations"} for x in result["variants"]], "seconds": result["seconds"]}))


if __name__ == "__main__":
    main()
