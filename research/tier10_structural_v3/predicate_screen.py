"""Test minimum-cardinality guard alternatives without changing production."""
import json,sys,time
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
from submissions.team3.tier10 import solution,shared_control,synthesis
from submissions.team3.tier08.modular import permutation_table
from screen import score


def guard_variant(available,row,variant):
    if available < row: raise ValueError('invalid mask')
    choices=[m for m in range(available+1) if m&available==m and m>=row]
    size=min(m.bit_count() for m in choices)
    choices=[m for m in choices if m.bit_count()==size]
    return choices[variant % len(choices)]


def make_selector(limit):
    @lru_cache(None)
    def select(d,p,w):
        table=permutation_table(d,p,w); inverse=[0]*len(table)
        for i,x in enumerate(table):inverse[x]=i
        original=synthesis.select_operations(d,p,w); best=original; cost=synthesis._cost(best)
        for variant in range(limit):
            def guard(available,row):return guard_variant(available,row,variant)
            with patch.object(synthesis,'_guard',guard):
                for mapping,back in ((table,False),(inverse,True)):
                    for shorten in (False,True):
                        ops=synthesis._short_predicates(mapping,shorten)
                        if back:ops=ops[::-1]
                        value=synthesis._cost(ops)
                        if value < cost:best,cost=ops,value
        return best
    return select

if __name__=='__main__':
    started=time.monotonic(); baseline=score(solution.build_circuit()); rows=[]
    for limit in (2,4,8,16):
        selector=make_selector(limit)
        with patch.object(shared_control,'select_operations',selector): metrics=score(solution.build_circuit())
        rows.append({'variants':limit,'metrics':metrics})
        print('variants',limit,metrics,flush=True)
    output={'baseline':baseline,'screens':rows,'seconds':round(time.monotonic()-started,3)}
    (ROOT/'research/tier10_structural_v3/predicate_screen.json').write_text(json.dumps(output,indent=2)+'\n')
