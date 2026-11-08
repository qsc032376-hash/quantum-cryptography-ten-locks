"""Bounded Tier 5 MCX synthesis and adjacent-predicate experiments."""
import importlib,json,tempfile,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit.circuit.library import RCCXGate
from qiskit.quantum_info import Operator,Statevector
from qiskit_aer import AerSimulator
from qiskit.synthesis import (synth_mcx_n_dirty_m15,synth_mcx_n_dirty_i15,
 synth_mcx_1_dirty_kg24,synth_mcx_2_dirty_kg24,synth_mcx_n_clean_m15)
from research.real_circuits.experiments import snapshot, REF58, gf2_runs
from research.circuit_optimizer.metrics import metrics


def compile_score(c):
    opts=dict(basis_gates=['rz','sx','x','cx'],optimization_level=1,seed_transpiler=12345,num_processes=1)
    t=time.perf_counter(); sim=AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2)
    native=transpile(c,sim,**opts); q,stats,_=gf2_runs(native)
    scored=transpile(q,coupling_map=None,initial_layout=None,**opts)
    return {'native_cx':native.count_ops().get('cx',0),'scored':metrics(scored),
            'gf2_removed':stats['removed_cx'],'compile_and_pass_seconds':time.perf_counter()-t}


def construct(method,n):
    if method=='m15': return synth_mcx_n_dirty_m15(n)
    if method=='i15': return synth_mcx_n_dirty_i15(n,relative_phase=False,action_only=False)
    if method=='kg1': return synth_mcx_1_dirty_kg24(n)
    if method=='kg2': return synth_mcx_2_dirty_kg24(n)
    raise ValueError(method)


def comparison(method,o):
    gate=construct(method,8); count=gate.num_qubits-9
    assert 0<=count<=10
    return gate.to_gate(label=method),o.WORK_QUBITS+(o.FLAG_QUBIT,)+o.KEY_QUBITS[:count]


def pair(n,joint):
    # Two *adjacent* equal predicates controlling X, then Z on one target.
    gate=construct('m15',n); d=gate.num_qubits-n-1
    target=n; clean=n+1+d; q=QuantumCircuit(clean+1)
    if joint:
        q.append(gate.to_gate(),list(range(n))+[clean]+list(range(n+1,n+1+d)))
        q.cx(clean,target); q.cz(clean,target)
        q.append(gate.inverse().to_gate(),list(range(n))+[clean]+list(range(n+1,n+1+d)))
    else:
        wires=list(range(n))+[target]+list(range(n+1,n+1+d))
        q.append(gate.to_gate(),wires); q.h(target); q.append(gate.to_gate(),wires); q.h(target)
    return q


def clean_circuit(m,ciphertext):
    # Three additional *clean* ancillas, returned to zero by every MCX.
    o=m.oracle; width=22
    a=o._build_mask_transform(0); b=o._build_mask_transform(1)
    targets=tuple(ciphertext[i] ^ ((o.helper.ROUND_CONSTANT*i)%256) ^ o.inverse_sbox_layer(o.inverse_permute(ch)) for i,ch in enumerate(b'QC'))
    gate=synth_mcx_n_clean_m15(8); assert gate.num_qubits==12
    wires=list(o.WORK_QUBITS)+[o.FLAG_QUBIT]+[19,20,21]
    def check(i, phase=False):
        c=QuantumCircuit(width); o._comparison_x(c,targets[i])
        if phase: c.h(o.FLAG_QUBIT)
        c.append(gate.to_gate(),wires)
        if phase: c.h(o.FLAG_QUBIT)
        o._comparison_x(c,targets[i]); return c
    def wide(q):
        c=QuantumCircuit(width); c.compose(q,qubits=list(range(19)),inplace=True); return c
    A=wide(a); B=wide(b); C=check(0); D=check(1,True)
    oracle=QuantumCircuit(width,name=o.ORACLE_NAME)
    for part in (A,C,A.inverse(),B,D,B.inverse(),A,C.inverse(),A.inverse()): oracle.compose(part,inplace=True)
    full=QuantumCircuit(width,10); full.h(range(10))
    diffuser=o.build_diffuser().to_gate()
    for _ in range(25):
        full.append(oracle.to_gate(),range(width)); full.append(diffuser,range(19))
    full.measure(range(10),range(10))
    return oracle,full


def main():
    # Exact 3-control test for every dirty/control/target branch, clean=0;
    # compare complex columns, including work restoration and relative phases.
    ref=Operator(pair(3,False)).data; new=Operator(pair(3,True)).data
    dim=ref.shape[0]; clean_bit=pair(3,True).num_qubits-1
    cols=[i for i in range(dim) if not ((i>>clean_bit)&1)]
    err=float(np.max(np.abs(ref[:,cols]-new[:,cols]))); assert err<1e-12
    # 8-control positive-phase full-support state, arbitrary dirty input and
    # clean bit zero: additional numeric evidence, not a full operator proof.
    base=pair(8,False); alt=pair(8,True)
    rng=np.random.default_rng(612)
    size=2**base.num_qubits; vec=np.zeros(size,dtype=complex)
    z=rng.normal(size=size//2)+1j*rng.normal(size=size//2); vec[:size//2]=z/np.linalg.norm(z)
    diff=float(np.max(np.abs(Statevector(vec).evolve(base).data-Statevector(vec).evolve(alt).data)))
    assert diff<1e-11
    exact=QuantumCircuit(4); exact.ccx(0,1,2); exact.cz(2,3); exact.ccx(0,1,2)
    relative=QuantumCircuit(4); relative.append(RCCXGate(),[0,1,2]); relative.cz(2,3); relative.append(RCCXGate().inverse(),[0,1,2])
    relative_error=float(np.max(np.abs(Operator(exact).data-Operator(relative).data)))
    assert relative_error<1e-12
    results={'relative_phase_fragment':{'full_operator_max_error':relative_error,
              'exact':compile_score(exact),'relative':compile_score(relative),
              'qualification':'valid here because the intermediate controlled-Z is diagonal; not established across actual mask transitions'},
             'source_commit':REF58,'candidate_reference':'4d79b7fa66d0acd4786d71be3c3ac2d291618c69',
             'clean_pair_operator_error_3_controls':err,'pair8_random_superposition_error':diff,
             'hypothetical_pair_baseline':compile_score(base),'hypothetical_pair_joint':compile_score(alt),
             'note':'pair is hypothetical: actual comparisons are separated by work-changing masks', 'templates':{}}
    for method in ('m15','i15','kg1','kg2'):
        gate=construct(method,8)
        results['templates'][method]={'borrowed':gate.num_qubits-9,'block':compile_score(gate)}
        # Controlled 3-qubit input/target columns across all dirty inputs for each template.
        small=construct(method,3)
        ideal=QuantumCircuit(small.num_qubits); ideal.mcx([0,1,2],3)
        op_err=float(np.max(np.abs(Operator(small).data-Operator(ideal).data)))
        assert op_err<1e-11
        results['templates'][method]['small_exact_operator_error']=op_err
    clean_small=synth_mcx_n_clean_m15(4)
    ideal_clean=QuantumCircuit(clean_small.num_qubits); ideal_clean.mcx(list(range(4)),4)
    x=Operator(clean_small).data; y=Operator(ideal_clean).data
    clean_cols=list(range(2**5))
    clean_error=float(np.max(np.abs(x[:,clean_cols]-y[:,clean_cols]))); assert clean_error<1e-11
    results['clean_small_operator_error']=clean_error
    clean=synth_mcx_n_clean_m15(8)
    # Test every controls+target basis input, with exactly the three clean
    # ancillas initialized to zero; compare the complex expected column.
    maxerr=0.0
    for index in range(512):
        output=Statevector.from_int(index,2**12).evolve(clean).data
        expected=index ^ ((1<<8) if index & 255 == 255 else 0)
        expected_vector=np.zeros(2**12,dtype=complex); expected_vector[expected]=1
        maxerr=max(maxerr,float(np.max(np.abs(output-expected_vector))))
    assert maxerr < 1e-11
    results['clean8_all_512_complex_columns_max_error']=maxerr
    results['extra_clean_alternative']={'clean_ancillas':clean.num_qubits-9,'block':compile_score(clean),'full_circuit':'not run; key wires are dirty'}
    with tempfile.TemporaryDirectory(prefix='tier05-joint-') as folder:
        snapshot(REF58,folder,'joint_snapshot'); m=importlib.import_module('joint_snapshot.tier05.solution')
        ciphertext,_=m._public_inputs()
        clean_oracle,clean_full=clean_circuit(m,ciphertext)
        measure=[(clean_full.find_bit(i.qubits[0]).index,clean_full.find_bit(i.clbits[0]).index) for i in clean_full.data if i.operation.name=='measure']
        assert measure==[(i,i) for i in range(10)]
        assert sum(i.operation.name==m.oracle.ORACLE_NAME for i in clean_full.data)==25
        results['measurement_mapping_and_25_iterations_verified']=True
        results['extra_clean_alternative']['oracle']=compile_score(clean_oracle)
        results['extra_clean_alternative']['full']=compile_score(clean_full)
        results['extra_clean_alternative']['full_circuit']='research-only, extra 3 clean qubits'
        for method in ('m15','i15','kg1','kg2'):
            with patch.object(m.oracle,'_dirty_comparison_gate',lambda: comparison(method,m.oracle)):
                oracle=m.oracle.build_phase_oracle(ciphertext)
                full=m.build_circuit(ciphertext=ciphertext)
                results['templates'][method]['oracle']=compile_score(oracle)
                results['templates'][method]['full']=compile_score(full)
    Path('research/tier05_joint_mcx/results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__': main()
