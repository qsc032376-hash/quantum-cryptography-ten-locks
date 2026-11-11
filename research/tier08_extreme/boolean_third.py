"""Exact two-cube conjugation refinement of existing Tier8 search networks.

This explores no new coordinate configurations and adds no auxiliary qubits.
The first two refinement artifacts remain immutable inputs.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.tier08_extreme import boolean_second as b


def conjugate_pair(a,b_gate):
    """Exact chronological A B A as at most two same-target cubes.

    B's predicate is D * l(t), where A toggles t with predicate F. If B's
    target does not enter F, A is restored after B and l(t XOR F)=l(t) XOR F.
    Thus the conjugated target action is D*l(t) XOR D*F. Incompatible D,F
    makes the second term zero. The implied-F case merges to one cube.
    """
    if b.commute(a,b_gate):
        return [b_gate]
    ma,va,ta=a; mb,vb,tb=b_gate
    if not mb>>ta&1 or ma>>tb&1:
        return None
    remaining=mb ^ (1<<ta)
    if (va^vb)&ma&remaining:
        return [b_gate]
    if ma&remaining == ma:
        return [(mb,vb ^ (1<<ta),tb)]
    extra=(ma|remaining,va|(vb&remaining),tb)
    assert not extra[0]>>tb&1 and extra[1]&extra[0]==extra[1]
    return [b_gate,extra]


def transported_merge(ops,window=48):
    current=list(map(tuple,ops))
    for _ in range(30):
        winner=None
        score=b.cost(current),len(current)
        for i,a in enumerate(current):
            crossed=[]
            for j in range(i+1,min(len(current),i+window+1)):
                next_gate=current[j]
                merged=b.merge_pair(a,next_gate)
                if merged is not False:
                    trial=current[:i]+crossed+([] if merged is None else [merged])+current[j+1:]
                    newscore=b.cost(trial),len(trial)
                    if newscore < score and (winner is None or newscore < winner[0]):
                        winner=newscore,trial
                transformed=conjugate_pair(a,next_gate)
                if transformed is None:
                    break
                crossed.extend(transformed)
        if winner is None:
            break
        current=winner[1]
    return current


def main():
    started=time.perf_counter();out=Path(__file__).parent
    sources={name:hashlib.sha256((out/name).read_bytes()).hexdigest()
             for name in ['boolean.py','boolean_second.py','boolean_third.py','search.json']}
    base_test=b.self_test()
    cubes=[(m,v,t) for t in range(3) for m in range(8) if not m>>t&1
           for v in range(8) if v&m==v]
    checks=0
    for a in cubes:
        for bb in cubes:
            candidate=conjugate_pair(a,bb)
            if candidate is not None:
                assert b.mapping([a,bb,a],3)==b.mapping(candidate,3)
                checks+=1
    b.transported_merge=transported_merge
    search=json.loads((out/'search.json').read_text())
    result={'source_inputs':sources,'self_test':base_test,'two_cube_conjugate_tests':checks,
            'refinements':[],'variants':[]}
    for multiplier,networks in search['top_candidates'].items():
        choices=[]
        for rank,network in enumerate(networks[:15]):
            operations=b.optimize(network['operations'])
            row={'multiplier':int(multiplier),'source_rank':rank,'source_fingerprint':network['fingerprint'],
                 'before':b.cost(network['operations']),'after':b.cost(operations),'operations':operations,
                 'full_64_mapping_and_inverse':True}
            result['refinements'].append(row);choices.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ['operations','source_fingerprint']}),flush=True)
        result['variants'].append(min(choices,key=lambda x:(x['after'],len(x['operations']))))
    result['seconds']=time.perf_counter()-started
    (out/'boolean_third_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('best',[(r['multiplier'],r['after']) for r in result['variants']],result['seconds'],flush=True)


if __name__=='__main__':
    main()
