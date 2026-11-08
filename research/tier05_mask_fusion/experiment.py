"""Bounded exact adjacent-mask transition experiments; no Aer or checker."""
import importlib
import json
from collections import Counter
from pathlib import Path
import tempfile
import time
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from research.real_circuits.experiments import snapshot, REF58, gf2_runs
from research.circuit_optimizer.metrics import metrics
from research.circuit_optimizer.gf2_synthesis import optimize, extract_matrix
from qiskit.quantum_info import Operator, Statevector
import numpy as np


def term(circuit, inst):
    op=inst.operation.name
    if op not in ('cx','ccx'): raise ValueError(op)
    wires=tuple(circuit.find_bit(q).index for q in inst.qubits)
    return (tuple(sorted(wires[:-1])), wires[-1])


def synth(terms):
    q=QuantumCircuit(19)
    for (controls,target), parity in sorted(terms.items()):
        if parity % 2:
            if len(controls)==1: q.cx(controls[0],target)
            else: q.ccx(*controls,target)
    return q


def evaluate(circuit, k):
    work=0
    for inst in circuit.data:
        controls,target=term(circuit,inst)
        assert target in range(10,18) and all(c in range(10) for c in controls)
        if all((k >> c)&1 for c in controls): work ^= 1 << (target-10)
    return work


def score(circuit, sim):
    kw=dict(basis_gates=['rz','sx','x','cx'],optimization_level=1,seed_transpiler=12345,num_processes=1)
    start=time.perf_counter()
    native=transpile(circuit,sim,**kw)
    native_seconds=time.perf_counter()-start
    optimized, stats, _=gf2_runs(native)
    score=transpile(optimized,coupling_map=None,initial_layout=None,**kw)
    return {'source_ops':dict(circuit.count_ops()), 'native_cx':native.count_ops().get('cx',0),
            'scored':metrics(score), 'gf2_removed':stats['removed_cx'], 'compile_seconds':native_seconds}


def build_fused_oracle(o, ciphertext):
    a=o._build_mask_transform(0); b=o._build_mask_transform(1)
    transition=QuantumCircuit(19); transition.compose(a.inverse(),inplace=True); transition.compose(b,inplace=True)
    counts=Counter(term(transition,i) for i in transition.data)
    linear=synth(Counter({t:n for t,n in counts.items() if len(t[0])==1}))
    linear_opt,_=optimize(linear)
    quadratic=synth(Counter({t:n for t,n in counts.items() if len(t[0])==2}))
    mixed=linear_opt.compose(quadratic)
    targets=tuple(ciphertext[i] ^ ((o.helper.ROUND_CONSTANT*i)%256) ^ o.inverse_sbox_layer(o.inverse_permute(ch)) for i,ch in enumerate(b'QC'))
    cg,w=o._dirty_comparison_gate()
    def check(index,phase=False):
        c=QuantumCircuit(19); o._comparison_x(c,targets[index])
        if phase: c.h(o.FLAG_QUBIT)
        c.append(cg,w)
        if phase: c.h(o.FLAG_QUBIT)
        o._comparison_x(c,targets[index])
        return c
    ca=check(0); db=check(1,True)
    candidate=QuantumCircuit(19,name=o.ORACLE_NAME)
    for block in (a,ca,mixed,db,mixed.inverse(),ca.inverse(),a.inverse()): candidate.compose(block,inplace=True)
    return candidate


def build_fused_circuit(module,ciphertext,iterations):
    phase=build_fused_oracle(module.oracle,ciphertext)
    circuit=QuantumCircuit(19,10); circuit.h(range(10))
    for _ in range(iterations):
        circuit.append(phase.to_gate(),range(19))
        circuit.append(module.oracle.build_diffuser().to_gate(),range(19))
    circuit.measure(range(10),range(10))
    return circuit


def main():
    with tempfile.TemporaryDirectory(prefix='tier05-mask-fusion-') as d:
        snapshot(REF58,d,'fusion_snapshot')
        m=importlib.import_module('fusion_snapshot.tier05.solution')
        o=m.oracle
        a=o._build_mask_transform(0); b=o._build_mask_transform(1)
        baseline=QuantumCircuit(19); baseline.compose(a.inverse(),inplace=True); baseline.compose(b,inplace=True)
        counts=Counter(term(baseline,i) for i in baseline.data)
        fused=synth(counts)
        original_terms=Counter(term(baseline,i) for i in baseline.data)
        fused_terms=Counter(term(fused,i) for i in fused.data)
        assert {t:n%2 for t,n in original_terms.items() if n%2} == {t:n%2 for t,n in fused_terms.items() if n%2}
        assert all(evaluate(baseline,k)==evaluate(fused,k) for k in range(1024))
        # Every key-controlled XOR commutes, so collect the linear terms and
        # synthesize their complete GF(2) map before the quadratic terms.
        linear=synth(Counter({t:n for t,n in counts.items() if len(t[0])==1}))
        linear_opt, accepted=optimize(linear)
        assert np.array_equal(extract_matrix(linear),extract_matrix(linear_opt))
        quadratic=synth(Counter({t:n for t,n in counts.items() if len(t[0])==2}))
        mixed=linear_opt.compose(quadratic)
        assert all(evaluate(baseline,k)==evaluate(mixed,k) for k in range(1024))
        # Full complex operator, including relative phases, on a representative
        # shared-control fragment with arbitrary target inputs.
        q=QuantumCircuit(4); q.ccx(0,1,2); q.cx(0,3); q.ccx(0,1,3)
        z=QuantumCircuit(4); z.ccx(0,1,3); z.cx(0,3); z.ccx(0,1,2)
        complex_error=float(np.max(np.abs(Operator(q).data-Operator(z).data)))
        assert complex_error < 1e-12
        initial=QuantumCircuit(19); initial.h(range(10)); initial.x([10,12,15]); initial.h(18)
        sv_a=Statevector.from_instruction(initial.compose(baseline))
        sv_b=Statevector.from_instruction(initial.compose(mixed))
        state_error=float(np.max(np.abs(sv_a.data-sv_b.data)))
        assert state_error < 1e-12
        sim=AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2)
        report={'snapshot':REF58,'research_candidate':'4d79b7fa66d0acd4786d71be3c3ac2d291618c69',
          'transition':'inverse(mask0); mask1', 'original_terms':sum(original_terms.values()),
          'unique_terms':len(original_terms),'cancelled_term_pairs':sum(n//2 for n in original_terms.values()),
          'odd_terms':sum(n%2 for n in original_terms.values()),
          'all_1024_key_branches_equal':True,'method':'ANF parity of key-controlled XORs; targets do not control any gate',
          'baseline':score(baseline,sim),'fusion':score(fused,sim),
          'gf2_linear_then_quadratic':score(mixed,sim), 'linear_gf2_accepted':bool(accepted),
          'representative_complex_operator_max_error':complex_error,
          '19_qubit_superposition_max_error':state_error,
          'limitations':'No comparisons crossed; arbitrary work, flag and borrowed key wires are unchanged except for proven work XOR.'}
        # Substitute only the exact adjacent transitions, without crossing comparisons.
        ciphertext,_=m._public_inputs()
        candidate=build_fused_oracle(o,ciphertext)
        original=o.build_phase_oracle(ciphertext)
        assert original.num_qubits == candidate.num_qubits == 19
        report['full_oracle_baseline']=score(original,sim)
        report['full_oracle_fused']=score(candidate,sim)
        old_full=m.build_circuit(ciphertext=ciphertext)
        new_full=build_fused_circuit(m,ciphertext,25)
        def measurement_map(circuit):
            return [(circuit.find_bit(i.qubits[0]).index,circuit.find_bit(i.clbits[0]).index)
                    for i in circuit.data if i.operation.name=='measure']
        assert measurement_map(old_full)==measurement_map(new_full)==[(j,j) for j in range(10)]
        assert sum(i.operation.name==o.ORACLE_NAME for i in new_full.data)==25
        report['measurement_map_verified']=True
        report['full_grover_baseline']=score(old_full,sim)
        report['full_grover_fused']=score(new_full,sim)
        report['whole_equivalence']='exact operator substitution F=A^-1 B and inverse; all comparison operations unchanged'
        print(json.dumps(report,indent=2))
        Path('research/tier05_mask_fusion/results.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__': main()
