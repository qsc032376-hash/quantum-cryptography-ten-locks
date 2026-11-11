"""Bounded probes of alternate constructions; no production mutation."""
import json,time
from collections import Counter
from qiskit import transpile
from search import *
from submissions.team3.tier08.modular import build_controlled_multiplier
from qiskit.synthesis import synth_mcx_n_dirty_m15

def main():
    par=solution._public_parameters();selected=json.loads((OUT/'candidate.json').read_text())['operations']
    d=int(next(iter(selected)));table=permutation_table(d,par['p'],7)
    # PPRM/ANF of output XOR input. An out-of-place XOR evaluator needs seven targets.
    terms=[];dependent=0
    for bit in range(7):
        coeff=[((table[x]^x)>>bit)&1 for x in range(128)]
        for j in range(7):
            for x in range(128):
                if x>>j&1:coeff[x]^=coeff[x^(1<<j)]
        terms.append(sum(coeff));dependent+=sum(v for m,v in enumerate(coeff) if m>>bit&1)
        for x in range(128):
            assert sum(coeff[m] for m in range(128) if x&m==m)%2==((table[x]^x)>>bit&1)
    cycle=build_controlled_multiplier(d,par['p'],7)
    opts={'basis_gates':['rz','sx','x','cx'],'optimization_level':1,'seed_transpiler':12345,'num_processes':1}
    cycle_metrics=compute_metrics(transpile(cycle,**opts))
    chosen_metrics=compute_metrics(transpile(emit(selected[str(d)]),**opts))
    c=builder(selected);hist=Counter();profile=[]
    # Attribution is marginal removal under whole-circuit recompilation, not additive.
    full=score(c)
    for group in ('qft','multipliers'):
        sub=c.copy_empty_like()
        for item in c.data:
            ispower=item.operation.name.startswith('tier10_controlled')
            isqft=not ispower and item.operation.num_qubits==6
            if (group=='qft' and isqft) or (group=='multipliers' and ispower):continue
            sub.append(item.operation,item.qubits,item.clbits)
        result=score(sub);profile.append({'removed':group,'residual':result,'marginal_cx':full['metrics']['two_qubit_gates']-result['metrics']['two_qubit_gates']})
    # Explicit exact dirty borrowing: reuse other count wires, never assume zero.
    dirty=c.copy_empty_like()
    for item in c.data:
        wires=[c.find_bit(q).index for q in item.qubits];cb=[c.find_bit(q).index for q in item.clbits]
        if not item.operation.name.startswith('tier10_controlled'):
            dirty.append(item.operation,wires,cb);continue
        borrow=[j for j in range(12) if j!=wires[0]][:3];block=item.operation.definition
        alt=QuantumCircuit(11)
        for sub in block.data:
            idx=[block.find_bit(q).index for q in sub.qubits];n=getattr(sub.operation,'num_ctrl_qubits',0)
            if n>=4:
                tmp=synth_mcx_n_dirty_m15(n);count=tmp.num_qubits-n-1
                alt.compose(tmp,idx+list(range(8,8+count)),inplace=True)
            else:alt.append(sub.operation,idx)
        dirty.append(alt.to_gate().copy(name=item.operation.name),wires+borrow)
    dirty_score=score(dirty)
    # Different count controls prohibit identity cancellation of otherwise equal work gates.
    flat=c.decompose();adjacent=0
    for a,b in zip(flat.data,flat.data[1:]):
        if a.operation==b.operation and a.qubits==b.qubits and a.operation.name in ('x','cx','ccx','mcx'):adjacent+=1
    levels={str(level):score(c,level) for level in (0,2,3)}
    result={'probe_public_multiplier':d,'anf_output_delta_term_counts':terms,'anf_target_dependent_terms':dependent,'anf_out_of_place_extra_qubits':7,'cycle_isolated':cycle_metrics,'selected_isolated':chosen_metrics,'whole_circuit_removal_profile':profile,'dirty_strategy':dirty_score,'native_levels_official_level1':levels,'adjacent_self_inverse_pairs':adjacent,'note':'Removal circuits are attribution probes, not valid recovery candidates. ANF evaluator not integrated; target-dependent terms preclude naive in-place extraction.'}
    (OUT/'alternatives.json').write_text(json.dumps(result,indent=2)+'\n');print('alternatives complete',flush=True)
if __name__=='__main__':main()
