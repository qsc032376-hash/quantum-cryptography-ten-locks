"""Deterministic hypothetical Simplicity analysis; standard library only."""
import argparse
import ast
import copy
from fractions import Fraction as F
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METRICS = ('two_qubit_gates', 'depth', 'total_gates', 'active_qubits')
WEIGHTS = dict(zip(METRICS, map(F, ('0.4', '0.3', '0.2', '0.1'))))
POINTS = dict(enumerate((1, 2, 2, 3, 4, 4, 5, 6, 6, 7), 1))
EXPECTED = [(151,44,298,25),(0,3,3,1),(7808,8771,19497,7),(183,195,455,20),
            (14552,28132,40938,19),(3000,5715,8752,22),(209,266,727,15),
            (33904,96055,102561,18),(55999,120242,168116,22),(46910,109763,132023,19)]
# Conservative architecture constraints, NOT universal quantum lower bounds.
# Only T9 has a documented narrower comparator in the reviewed evidence.
WIDTH_FLOOR = dict(enumerate((25,1,7,20,19,22,15,18,21,19),1))
RATES = (1,5,10,20,30)
CANDIDATES = {5:(13802,19480,38556,22),9:(55971,120223,168088,22),10:(46038,107877,129606,19)}

def pool(tier):
    return F(3,8)*POINTS[tier]

def ratio(best, value):
    if type(best) is not int or type(value) is not int or min(best,value)<0 or best>value:
        raise ValueError('eligible best must be an integer between zero and our value')
    return (F(1) if value==0 else F(1,1+value)) if best==0 else F(best,value)

def validate(rows):
    if set(rows)!=set(POINTS):
        raise ValueError('exactly tiers 1..10 required')
    for row in rows.values():
        if set(row)!=set(METRICS) or any(type(v) is not int or v<0 for v in row.values()):
            raise ValueError('four nonnegative integer metrics required')

def score(ours, best):
    """Best is the GLOBAL eligible minimum, including our eligible team."""
    validate(ours); validate(best)
    result = {}
    for i in POINTS:
        components = {m:pool(i)*WEIGHTS[m]*ratio(best[i][m],ours[i][m]) for m in METRICS}
        result[i] = {'score':sum(components.values()),'gap':pool(i)-sum(components.values()),
                     'components':components,'losses':{m:pool(i)*WEIGHTS[m]-components[m] for m in METRICS}}
    return {'label':'HYPOTHETICAL, not an official competition score',
            'total':sum(r['score'] for r in result.values()),'tiers':result}

def against(ours, competitors):
    """Independent competitor minima remain fixed when our values change."""
    validate(ours); validate(competitors)
    return score(ours,{i:{m:min(ours[i][m],competitors[i][m]) for m in METRICS} for i in POINTS})

def baseline():
    report=json.loads((ROOT/'docs/v6-rc/report.json').read_text())
    rows={i:report['tiers'][str(i)]['metrics'] for i in POINTS}
    assert [tuple(rows[i][m] for m in METRICS) for i in POINTS]==EXPECTED
    assert [sum(r[m] for r in rows.values()) for m in METRICS[:3]]==[162716,369186,473370]
    assert all(t['status']=='full' and t['hash_ok'] and not t['flags'] for t in report['tiers'].values())
    return rows

def ceil_fraction(n,d):
    return (n+d-1)//d

def lower(i,m,x,percent):
    floor=WIDTH_FLOOR[i] if m=='active_qubits' else (0 if m=='two_qubit_gates' else 1)
    return max(floor,ceil_fraction(x*(100-percent),100))

def scenarios(ours):
    result={'A':copy.deepcopy(ours)}
    for label,p in [('B',10),('C',25),('D',50)]:
        result[label]={i:{m:lower(i,m,x,p) for m,x in row.items()} for i,row in ours.items()}
    # Different abstract rival specialists set each metric minimum, not one claimed team.
    gaps={1:(10,20,10),2:(0,0,0),3:(40,35,30),4:(20,10,15),5:(25,20,25),
          6:(25,30,20),7:(5,0,5),8:(40,35,30),9:(50,40,45),10:(40,50,35)}
    result['E']={i:{m:lower(i,m,row[m],gaps[i][j] if j<3 else (5 if i==9 else 0))
                    for j,m in enumerate(METRICS)} for i,row in ours.items()}
    return result

def gain(ours,comp,i,changes):
    candidate=copy.deepcopy(ours); candidate[i].update(changes)
    return against(candidate,comp)['tiers'][i]['score']-against(ours,comp)['tiers'][i]['score']

def upper_gain(i,old,new):
    # For decreases x->y, maximum over all integer competitor minima is 1-y/x,
    # attained at b=y. Increased metrics have supremum zero (rival >= new).
    return pool(i)*sum(WEIGHTS[m]*F(old[m]-new[m],old[m]) for m in METRICS if new[m]<old[m])

def tests():
    ours=baseline(); sc=scenarios(ours)
    assert score(ours,ours)['total']==15
    assert ratio(0,0)==1 and ratio(0,3)==F(1,4)
    for args in [(4,3),(-1,2),(1.2,3),(True,2)]:
        try: ratio(*args)
        except ValueError: pass
        else: raise AssertionError(args)
    # Official worked examples (unrounded points).
    best=dict(zip(METRICS,(30,50,100,12)))
    for row,expected in [((30,60,100,12),F(171,160)),((40,50,120,12),F(39,40)),((60,90,150,12),F(27,40))]:
        assert pool(4)*sum(WEIGHTS[m]*ratio(best[m],v) for m,v in zip(METRICS,row))==expected
    # Execute only the official pure ratio function: no Qiskit/YAML import needed.
    tree=ast.parse((ROOT/'tools/rank.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='metric_ratio')
    ns={}; exec(compile(ast.Module(body=[node],type_ignores=[]),'official ratio','exec'),ns)
    for x in range(51):
        for b in range(x+1): assert abs(float(ratio(b,x))-ns['metric_ratio'](b,x))<1e-14
    for comp in sc.values():
        assert 0<=against(ours,comp)['total']<=15
        for i in POINTS:
            for m in METRICS:
                changes=[lower(i,m,ours[i][m],p) for p in RATES]
                gains=[gain(ours,comp,i,{m:x}) for x in changes]
                assert gains==sorted(gains) and min(gains)>=0
    # Identity switch, zero rival, and candidate maximum checked exhaustively on small integers.
    for x in range(1,30):
        for y in range(x):
            gains=[ratio(min(b,y),y)-ratio(min(b,x),x) for b in range(x+2)]
            # y=0 follows special zero rule; max still 1 for x>0 is NOT attained.
            if y>0: assert max(gains)==F(x-y,x)
    assert gain(ours,sc['A'],10,dict(zip(METRICS,CANDIDATES[10])))==0
    print('PASS: baseline, examples, official ratio parity, invalid inputs, saturation, monotonicity, bounds')

def jsonable(obj):
    if isinstance(obj,F): return float(obj)
    if isinstance(obj,dict): return {str(k):jsonable(v) for k,v in obj.items()}
    if isinstance(obj,(tuple,list)): return [jsonable(v) for v in obj]
    return obj

def load_rows(path):
    data=json.loads(Path(path).read_text())
    if 'tiers' in data: data={i:r['metrics'] for i,r in data['tiers'].items()}
    return {int(i):r for i,r in data.items()}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test',action='store_true'); parser.add_argument('--ours')
    parser.add_argument('--best',help='global eligible minima; reject best > ours')
    parser.add_argument('--competitors',help='independent rival minima; recompute global best')
    parser.add_argument('--report',action='store_true',help='regenerate research Markdown report')
    args=parser.parse_args()
    if args.test: tests(); return
    if args.best and args.competitors: parser.error('choose --best or --competitors')
    ours=load_rows(args.ours) if args.ours else baseline()
    if args.report: write_report(ours); return
    if args.best: result=score(ours,load_rows(args.best))
    elif args.competitors: result=against(ours,load_rows(args.competitors))
    else:
        result={'assumptions':'integer ceiling; conservative documented width floors; no actual rival data',
                'scenarios':{s:{'competitors':c,'result':against(ours,c)} for s,c in scenarios(ours).items()},
                'sensitivity':[{ 'scenario':s,'tier':i,'metric':m,'percent':p,
                   'candidate':lower(i,m,ours[i][m],p),'gain':gain(ours,c,i,{m:lower(i,m,ours[i][m],p)})}
                   for s,c in scenarios(ours).items() for i in POINTS for m in METRICS for p in RATES]}
    print(json.dumps(jsonable(result),indent=2))

def write_report(ours):
    sc=scenarios(ours); scores={s:against(ours,c) for s,c in sc.items()}
    lines=['# Team 3 Simplicity sensitivity and optimization strategy',
    '', 'Research date: November 11, 2026 (America/New_York). Deadline: November 13, 2026, 12:00 PM EST.',
    '', '**Recommendation:** retain the verified final package. If further research is pursued, prioritize independent validation of Tier 10 v3, not immediate integration. All scores below are hypothetical; no opponent submissions were accessed.',
    '', '## Formula and provenance',
    '', 'For tier i, Pᵢ = 0.375 × tier points. The pools sum to 15. For each metric, the global best includes Team 3 when eligible: b = min(c, x), where c is an independently specified rival minimum. The ratio is b/x when b > 0; when b = 0 it is 1 if x = 0, otherwise 1/(1+x). Tier score is Pᵢ Σₘ wₘ ratioₘ. Weights are 0.40 two-qubit gates, 0.30 depth, 0.20 total gates and 0.10 active qubits.',
    '', 'Sources: [official rubric](../SCORING.md), [ranking implementation](../tools/rank.py), [RC JSON](v6-rc/report.json), and [RC table](v6-rc/report.md). Eligibility requires full tier credit and valid metrics; rank.py uses full-credit fraction and a present metrics mapping. The calculator assumes eligible validated input, not that hypothetical circuits have passed eligibility checks. It rejects a supplied global best greater than our value; the separate competitor interface allows larger rival values and recomputes the minimum.',
    '', 'Pinned runtime: `c4455782ea9388d5897fc27270f42dd3786ed35d`. Independent runtime audit: `58853c2`, docs/v6-rc/INDEPENDENT_AUDIT.md. Final package: `ca7290c7f6b35e37e4ef94f3d5f79110309f594f`. This research branch starts at the runtime RC and changes no submission file or archive. No quantum simulation was rerun.',
    '', 'Official Tier 4 examples reproduce exactly: Alpha 1.06875 (display 1.069), Beta 0.975, Gamma 0.675. Tests compare the official ratio implementation on 1,326 integer pairs, including zero. Aggregate gates alone cannot determine this score.',
    '', '## Verified baseline', '', '| Tier | Pool | 2Q | Depth | Gates | Qubits |', '|---:|---:|---:|---:|---:|---:|']
    for i in POINTS: lines.append(f'| {i} | {float(pool(i)):.3f} | '+ ' | '.join(str(ours[i][m]) for m in METRICS)+' |')
    lines += ['', 'All ten tiers are FULL, hash-matched and flag-free in the stored audited evidence. Totals are 162,716 two-qubit gates, 369,186 sum of per-tier depths, and 473,370 gates. The depth sum is not a combined-circuit depth. No discrepancy with the requested baseline was found.',
    '', '## Hypothetical competitor scenarios',
    '', 'A ties our baseline in every metric. B/C/D set positive gate and depth rival values to ceil(0.90x), ceil(0.75x), ceil(0.50x), respectively. Zero stays zero. These are approximate integer reductions, not exact uniform percentage scores. Depth and total gates remain at least one. Width uses a deliberately conservative architecture constraint: hold the documented register counts fixed except Tier 9, where the historical 21-qubit implementation provides a narrower reference. Thus percentage reductions in width are clipped at that evidence-supported floor. These are modeling constraints, not universal physical lower bounds; review thresholds are not physical bounds. No simultaneous realization of the hypothetical gate/width tuple is claimed.',
    '', 'E uses metric-specific percentage gaps (2Q/depth/gates): T1 10/20/10; T2 0/0/0; T3 40/35/30; T4 20/10/15; T5 25/20/25; T6 25/30/20; T7 5/0/5; T8 40/35/30; T9 50/40/45; T10 40/50/35. Width is unchanged except T9=21. Separate abstract specialists lead each metric, so no single competitor is assumed to attain every minimum. T2 is exactly tied in E and T7 close. Small-integer rounding keeps B/C T2 unchanged; D allows the hypothetical three-gate/depth circuit to become two, without asserting such an implementation exists.',
    '', '| Tier | A | B | C | D | E | E gap |', '|---:|---:|---:|---:|---:|---:|---:|']
    for i in POINTS: lines.append(f'| {i} | '+' | '.join(f"{float(scores[s]['tiers'][i]['score']):.6f}" for s in sc)+f" | {float(scores['E']['tiers'][i]['gap']):.6f} |")
    lines.append('| **Total / 15** | '+' | '.join(f"{float(scores[s]['total']):.6f}" for s in sc)+f" | {15-float(scores['E']['total']):.6f} |")
    lines += ['', 'All rival minima and every metric contribution/loss are exported by the default JSON command. No scenario is assigned a probability. Gaps from full in any scenario equal the pool minus the corresponding table entry.',
    '', '## Sensitivity and bounds',
    '', 'For positive fixed rival minimum c and x > c: Sₘ = Pᵢwₘc/x, dSₘ/dx = −Pᵢwₘc/x². A small fractional reduction ε has gain approximately Pᵢwₘ(c/x)ε; this compares fractional engineering progress, whereas the derivative compares removal of one unit. At x=c the function has a kink; below c it is flat at full credit. At c=0 use the official 1/(1+x) rule (derivative −Pᵢwₘ/(1+x)² for x>0), not c/x. At zero, ratio is 1. Integer rounding and saturation require finite differences, not derivative extrapolation.',
    '', 'For a positive reduction x→y, the greatest possible gain over fixed integer rival minima is Pᵢwₘ(1−y/x), attained at c=y. For c<y gain grows with c; for y≤c<x it decreases with c; for c≥x it is zero. Independent metric leaders make the sum of these bounds attainable in the abstract metric model, not evidence of a realizable opponent. No benefit remains when we already lead all affected metrics.',
    '', 'Each following cell is the isolated point gain for 1% / 5% / 10% / 20% / 30% requested reduction, using y=ceil((1−ε)x), clipped to the stated bounds. Other metrics and rival minima stay fixed. These are score sensitivities, not invented candidate measurements. Gate count, depth and width are coupled physically, so isolated improvements need circuit validation. A has zero gain for every row and is omitted here; all five scenarios and all four metrics are in JSON.',
    '', '| Tier | Metric | B gains | C gains | D gains | E gains |', '|---:|---|---|---|---|---|']
    for i in POINTS:
        for m in METRICS[:3]:
            cells=[' / '.join(f'{float(gain(ours,sc[s],i,{m:lower(i,m,ours[i][m],p)})):.5f}' for p in RATES) for s in 'BCDE']
            lines.append(f'| {i} | {m} | '+' | '.join(cells)+' |')
    lines += ['', '### Active-qubit sensitivity',
    '', 'No fractional qubits are used. For T1–8 and T10, none of the requested percentage reductions is supported within the preserved architecture: the calculator clips to the current width, giving zero modeled gain. This does not prove global width optimality. Tier 9 can be compared to the documented 21-qubit architecture; ceil rounding gives widths 22/21/21/21/21 at 1/5/10/20/30%. Holding v2 gates fixed while removing its synthesis wire is only a conditional tradeoff, not a tested candidate.',
    '', '| Tier | Current width | Supported lower comparison | E gain at lower width | E loss adding one qubit |', '|---:|---:|---:|---:|---:|']
    for i in POINTS:
        q=ours[i]['active_qubits']; floor=WIDTH_FLOOR[i]
        lines.append(f"| {i} | {q} | {floor} | {float(gain(ours,sc['E'],i,{'active_qubits':floor})):.6f} | {-float(gain(ours,sc['E'],i,{'active_qubits':q+1})):.6f} |")
    lines += ['', '### Ranked opportunities under E',
    '', 'Combined sensitivity means 10% improvement in each of 2Q, depth and total gates with width held fixed. It is a planning target, not a claim that an untested circuit exists. Marginal means a 1% 2Q reduction; 10% 2Q isolates the highest-weight metric. Ordering uses combined point gain, not gate counts.',
    '', '| Rank | Tier | Pool | E score | Gap | 1% 2Q gain | 10% 2Q gain | Combined 10% gain |', '|---:|---:|---:|---:|---:|---:|---:|---:|']
    combined={i:gain(ours,sc['E'],i,{m:lower(i,m,ours[i][m],10) for m in METRICS[:3]}) for i in POINTS}
    for rank,i in enumerate(sorted(POINTS,key=lambda i:combined[i],reverse=True),1):
        values=[pool(i),scores['E']['tiers'][i]['score'],scores['E']['tiers'][i]['gap'],gain(ours,sc['E'],i,{'two_qubit_gates':lower(i,'two_qubit_gates',ours[i]['two_qubit_gates'],1)}),gain(ours,sc['E'],i,{'two_qubit_gates':lower(i,'two_qubit_gates',ours[i]['two_qubit_gates'],10)}),combined[i]]
        lines.append(f'| {rank} | {i} | '+' | '.join(f'{float(v):.6f}' for v in values)+' |')
    lines += ['', 'Tier 10 has the largest pool (2.625) and largest combined 10% gain in E; two-qubit gates have its largest weight. Tier 8 and Tier 9 each have 2.25 points. Tier 7 has 1.875 points but is already near the assumed best in E and quickly saturates; in C/D it deserves much more attention. Tier 3 has a severe E gap despite only 0.75 points; inspect whether a low-effort exact rewrite is available before undertaking a risky large-tier redesign. Engineering effort has not been measured, so no points-per-hour ranking is asserted. A severe gap creates headroom but also lowers local sensitivity when the rival is far ahead.',
    '', '## Documented research candidates',
    '', '| Tier candidate | 2Q / depth / gates / qubits | A gain | B gain | C gain | D gain | E gain | Maximum positive gain bound |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for i,vals in CANDIDATES.items():
        new=dict(zip(METRICS,vals)); gains=[gain(ours,sc[s],i,new) for s in sc]
        lines.append(f'| T{i} '+('clean ancilla (rejected)' if i==5 else 'v3')+' | '+' / '.join(map(str,vals))+' | '+' | '.join(f'{float(v):.8f}' for v in gains)+f' | {float(upper_gain(i,ours[i],new)):.8f} |')
    lines += ['', 'T5 upper bound ignores the unavoidable width penalty for a fixed low-width rival and is not a practical score forecast. The exact gains in the five scenarios include that penalty. The documented total-gate count is 38,556, rather than an inferred value. All ten strict OSC candidate solves exceeded 120 seconds and were circuit_only, making them ineligible for Simplicity in those runs; one unseeded FULL result at 118.116 seconds does not erase the failures. Retain accepted GF(2), 14,552 / 28,132 / 40,938 / 19.',
    '', 'T9 v3 (55,971 / 120,223 / 168,088 / 22) passes an isolated Checker, but only two local paired seeds were tested and both were slower than v2. Its tiny upper bound is below the competition’s 0.01 tie tolerance by itself; do not confuse this with a guaranteed tie outcome when other scores differ. Do not integrate without independent reliability verification. The accepted v2 OSC benchmark retains its original INCONCLUSIVE label even though the later integration decision selected v2.',
    '', 'T10 v3 (46,038 / 107,877 / 129,606 / 19) and v2 both passed isolated Checker validation. v3 has three local paired seeds rather than v2’s accepted broader evidence; its mean local solve increased 4.005→5.651 seconds. The selector is a research wrapper requiring production integration and revalidation. The mathematical upper bound is a ceiling over unknown rivals, not an expected reward.',
    '', 'T8 trajectory: frozen v5 42,810 / 123,320; immediately preceding baseline 42,792 / 123,300 / 130,171 / 18; accepted hybrid 33,904 / 96,055 / 102,561 / 18. Hybrid fixed-mask/cycle-anchor synthesis passed independent full controlled-block operator checks and ten OSC pairs. These savings are already in v6; no new T8 candidate or extra reduction is claimed.',
    '', '## Scenario-based release decision',
    '', '| Option | Score opportunity | Correctness / runtime evidence | Effort and release risk | Decision |',
    '|---|---|---|---|---|',
    '| Keep accepted package | No incremental gain; preserves all scenario baseline scores | Independent 10/10 FULL runtime audit | No integration required | Recommended before deadline |',
    '| T5 clean ancilla | Conditional metric gains; width +3 | 10/10 strict OSC solve overruns | High timeout risk; loses eligibility | Reject |',
    '| T9 v3 | Very small absolute ceiling | Isolated FULL; two local pairs; independent reliability incomplete | New integration and package audit for negligible gain | Defer |',
    '| T10 v3 | Largest documented remaining ceiling; zero in A | Isolated FULL, scoped phase tests, three local pairs; slower | Broader independent validation, explicit selector integration, full artifact audit needed | First research target, not immediate release |',
    '| New T8/T10 changes | Hypothetical sensitivity only | No candidate evidence | Unknown engineering/validation effort | Do not promise a deliverable before deadline |',
    '', 'There are fewer than two calendar days from the analysis date to the deadline. Preserving ten FULL tiers is worth more than these small candidate ceilings: losing FULL can also lose tier-solution points and the entire tier Simplicity pool. We assign no fabricated failure probabilities or expected value. Any candidate must preserve genuine measurement-driven quantum execution, have supported mathematical correctness, pass the official Checker and timeout limits, receive independent verification, and be included in a rebuilt and audited final artifact before consideration. A later resubmission resets the official tie-break timestamp. This analysis does not authorize or perform integration, release creation or submission.',
    '', '## Evidence and reproduction',
    '', 'Evidence read from immutable Git snapshots: `0134d0d:docs/TIER05_FINAL_SELECTION.md`; `aed4e77:docs/TIER05_CLEAN_ANCILLA_OSC_VALIDATION.md`; `3dac27e:docs/TIER08_OSC_VALIDATION.md`; `2b5b2f3c565becd762b9dd3c1ec995b94f0fc13f:docs/TIER09_STRUCTURAL_V3_RESEARCH.md`; `8b741156e9d00c0c80a7d6890fa0ee2d1cada2d8:docs/TIER10_STRUCTURAL_V3_RESEARCH.md`. Historical reports are evidence, not files assumed to exist in the final ZIP. No private opponent data, secrets or plaintext were used.',
    '', 'See [calculator instructions and tests](../research/simplicity_analysis/README.md). The program exports all integer assumptions, per-metric gains/losses, all scenario scores and 200 sensitivity rows per scenario. Its deterministic report generator reproduces these tables. Bounds and conditional improvements do not certify physical feasibility, compiler equivalence or future seed reliability.']
    (ROOT/'docs/SIMPLICITY_SENSITIVITY_ANALYSIS.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
