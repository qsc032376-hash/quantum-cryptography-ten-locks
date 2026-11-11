"""Bounded general-linear coordinate synthesis with explicit CX boundaries.

For L a short reversible CNOT network and B a bit-permutation/XOR encoding,
the eliminated table is B L P L^-1 B^-1. Decode only B gate-by-gate, leaving
L before and L^-1 after the controlled middle block. The boundaries are
unconditional; their cancellation establishes control-off identity.
"""
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.tier08_extreme import mixed
from research.tier08_extreme import boolean_third as boolean


def apply_linear(x,gates):
    for control,target in gates:
        assert control != target and 0<=control<6 and 0<=target<6
        if x>>control&1:
            x ^= 1<<target
    return x


def synthesize(multiplier,config):
    perm=config['permutation'];flip=config['xor_mask'];pre=config['pre_cx']
    original=mixed.table(multiplier)
    encoding=[mixed.encode(apply_linear(x,pre),perm,flip) for x in range(64)]
    assert len(set(encoding))==64
    mapped=[0]*64
    for x,y in enumerate(original):
        mapped[encoding[x]]=encoding[y]
    if config['inverse']:
        mapped=mixed.inverse_table(mapped)
    gates=mixed.eliminate(mapped,config['policy'],config['descending'])
    if config['inverse']:
        gates=gates[::-1]
    # Decode B; retain L as an explicit physical boundary network.
    operations=mixed.simplify([(
        sum(1<<perm[j] for j in range(6) if mask>>j&1),
        sum(1<<perm[j] for j in range(6) if mask>>j&1 and not flip>>j&1),
        perm[target]) for mask,target in gates])
    return {'pre_cx':pre,'operations':operations,'post_cx':list(reversed(pre))}


def verify(candidate,multiplier):
    expected=mixed.table(multiplier)
    pre=candidate['pre_cx'];post=candidate['post_cx'];ops=candidate['operations']
    for control in (0,1):
        for x in range(64):
            y=apply_linear(x,pre)
            if control:
                y=mixed.apply_operations(ops,y)
            y=apply_linear(y,post)
            assert y==(expected[x] if control else x)
            z=apply_linear(y,list(reversed(post)))
            if control:
                z=mixed.apply_operations(list(reversed(ops)),z)
            z=apply_linear(z,list(reversed(pre)))
            assert z==x
    return True


def cost(candidate):
    return mixed.cost(candidate['operations'])+len(candidate['pre_cx'])+len(candidate['post_cx'])


def main():
    out=Path(__file__).parent;started=time.perf_counter();rng=random.Random(2026111109)
    search=json.loads((out/'search.json').read_text())
    baseline=json.loads((out/'third_selected.json').read_text())
    result={'seed':2026111109,'configuration_cap':1000,'configurations':[],
            'selected':{d:{'pre_cx':[],'operations':ops,'post_cx':[]} for d,ops in baseline.items()},
            'baseline_proxy':{d:mixed.cost(ops) for d,ops in baseline.items()},
            'source_inputs':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in
                             ['affine_linear.py','mixed.py','boolean_second.py','boolean_third.py','search.json','third_selected.json']}}
    tops={str(d):[] for d in (2,4,11)}
    all_pairs=[(c,t) for c in range(6) for t in range(6) if c!=t]
    # The public inverse pair 11/16 shares the searched architecture.
    agenda=[11]*500+[2]*250+[4]*250
    for index,multiplier in enumerate(agenda):
        seed_config=search['top_candidates'][str(multiplier)][rng.randrange(8)]['configuration']
        depth=1+((index//30)%6)
        linear=[]
        for _ in range(depth):
            gate=rng.choice(all_pairs)
            if linear and linear[-1]==gate:
                linear.pop()
            else:
                linear.append(gate)
        config={'pre_cx':linear,'permutation':seed_config['permutation'],
                'xor_mask':seed_config['xor_mask'],'policy':rng.choice(['fixed','short_set','short_both']),
                'descending':bool(rng.randrange(2)),'inverse':bool(rng.randrange(2))}
        candidate=synthesize(multiplier,config);verify(candidate,multiplier)
        row={'index':index,'multiplier':multiplier,'configuration':config,
             'estimated_cx':cost(candidate),'candidate':candidate,'all_128_control_work_and_inverse':True}
        result['configurations'].append(row)
        tops[str(multiplier)].append(row)
        tops[str(multiplier)].sort(key=lambda r:(r['estimated_cx'],len(r['candidate']['operations'])))
        tops[str(multiplier)]=tops[str(multiplier)][:8]
        if cost(candidate)<cost(result['selected'][str(multiplier)]):
            result['selected'][str(multiplier)]=candidate
            print('gain',index,multiplier,cost(candidate),flush=True)
    # Exact local postprocessing of only the strongest previously searched networks.
    boolean.b.transported_merge=boolean.transported_merge
    result['refinements']=[]
    for multiplier,rows in tops.items():
        for row in rows:
            candidate=dict(row['candidate'])
            candidate['operations']=boolean.b.optimize(candidate['operations'])
            verify(candidate,int(multiplier))
            refined={'configuration_index':row['index'],'multiplier':int(multiplier),
                     'before':row['estimated_cx'],'after':cost(candidate),'candidate':candidate}
            result['refinements'].append(refined)
            if cost(candidate)<cost(result['selected'][multiplier]):
                result['selected'][multiplier]=candidate
    c=result['selected']['11']
    inverse={'pre_cx':c['pre_cx'],'operations':list(reversed(c['operations'])),'post_cx':c['post_cx']}
    verify(inverse,16)
    if cost(inverse)<cost(result['selected']['16']):
        result['selected']['16']=inverse
    result['best_proxy']={d:cost(c) for d,c in result['selected'].items()}
    result['seconds']=time.perf_counter()-started
    result['note']='Public permutation gate compilation only; estimates include both CX boundaries and require whole-circuit scoring.'
    (out/'affine_linear.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('finished',result['best_proxy'],result['seconds'],flush=True)


if __name__=='__main__':main()
