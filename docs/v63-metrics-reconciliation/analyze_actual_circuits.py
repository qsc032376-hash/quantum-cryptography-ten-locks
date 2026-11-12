"""Compare actual official-scoring inputs without retaining private circuits.

Only Tiers 5/6/7's already compiled primitive circuits are compared. No Oracle
Gate decomposition or parameter is printed, inferred or recorded. Equality of
standard native scalar parameters is used transiently; only equality booleans and
public counts/metrics are saved. All original Checker outputs remain unchanged.
"""
import argparse
import io
import json
from pathlib import Path
import sys
import time


def load_records(path):
    from qiskit import qpy
    with path.open('rb') as f:
        sizes=json.loads(f.readline());records=[]
        for size in sizes:
            data=f.read(size);assert len(data)==size
            decoded=qpy.load(io.BytesIO(data));assert len(decoded)==1
            records.append(decoded[0])
        assert not f.read()
    return records


def same_primitive_sequence(a,b):
    allowed={'rz','sx','x','cx','measure','barrier'}
    if not set(a.count_ops())<=allowed or not set(b.count_ops())<=allowed:
        return {'supported':False,'reason':'Not inspecting non-native operation internals'}
    if any(getattr(item.operation,'condition',None) is not None for circuit in (a,b) for item in circuit.data):
        return {'supported':False,'reason':'Classically conditioned operation outside primitive comparison scope'}
    shape=(a.num_qubits,a.num_clbits,len(a.data))==(b.num_qubits,b.num_clbits,len(b.data))
    if not shape:return {'supported':True,'shape_equal':False,'exact_order_and_native_operations_equal':False,'global_phase_equal':False}
    equal=True
    import numbers
    def native_gate_equal(left,right):
        if (left.name != right.name or left.base_class is not right.base_class
            or left.num_qubits != right.num_qubits or left.num_clbits != right.num_clbits
            or len(left.params) != len(right.params)):
            return False
        # Compare compiled standard-gate scalar parameters exactly, transiently.
        # Do not call Instruction.__eq__: it may inspect definitions and use tolerance.
        return all(isinstance(x,numbers.Number) and isinstance(y,numbers.Number)
                   and bool(x==y) for x,y in zip(left.params,right.params))
    for left,right in zip(a.data,b.data):
        if (tuple(a.find_bit(q).index for q in left.qubits)!=tuple(b.find_bit(q).index for q in right.qubits)
            or tuple(a.find_bit(q).index for q in left.clbits)!=tuple(b.find_bit(q).index for q in right.clbits)
            or not native_gate_equal(left.operation,right.operation)):
            equal=False;break
    return {'supported':True,'shape_equal':True,'exact_order_and_native_operations_equal':equal,
            'global_phase_equal':bool(a.global_phase==b.global_phase)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--evidence',type=Path);a=p.parse_args()
    out=(a.evidence or a.repository/'docs/v63-metrics-reconciliation').resolve();output=out/'actual-circuits.json';assert not output.exists()
    runs=json.loads((out/'three-runs.json').read_text());assert runs.get('completed_runs')==3
    official=a.private_root/'official-1';sys.path.insert(0,str(official))
    from tools.check_submission import compute_metrics,load_config
    from qiskit import transpile
    cfg=load_config();loaded={};results=[]
    for run in range(1,4):
        original=json.loads((out/f'run-{run}/checker/report.json').read_text())
        for tier in (5,6,7):
            path=a.private_root/f'captured-{run}'/f'tier{tier:02d}.circuits'
            if not path.exists():raise RuntimeError('Missing actual scoring-input capture; do not substitute build_circuit')
            circuits=load_records(path);loaded[run,tier]=circuits
            assert len(circuits)==original['tiers'][str(tier)]['unique_circuits']
            row={'run':run,'tier':tier,'actual_unique_records':len(circuits),
                 'actual_total_executions':original['tiers'][str(tier)]['circuits_executed'],
                 'captured_from_actual_official_scoring_worker':True,'circuits':[]}
            scored_metrics=[]
            for index,circuit in enumerate(circuits):
                begin=time.monotonic()
                scored=transpile(circuit,**{k:cfg[k] for k in ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')})
                metrics=compute_metrics(scored);scored_metrics.append(metrics)
                row['circuits'].append({'record_index':index,'qubits':circuit.num_qubits,'classical_bits':circuit.num_clbits,
                    'native_count_ops':{k:int(v) for k,v in circuit.count_ops().items()},
                    'native_metrics':compute_metrics(circuit),'official_replay_metrics':metrics,
                    'official_replay_count_ops':{k:int(v) for k,v in scored.count_ops().items()},
                    'replay_compile_seconds':time.monotonic()-begin})
            winner=max(range(len(circuits)),key=lambda i:(scored_metrics[i]['two_qubit_gates'],scored_metrics[i]['depth']))
            row['scored_winner_record_index']=winner;row['reported_official_metrics']=original['tiers'][str(tier)]['metrics']
            row['replayed_winner_matches_actual_official_report']=scored_metrics[winner]==row['reported_official_metrics']
            assert row['replayed_winner_matches_actual_official_report']
            results.append(row)
    comparisons=[]
    for run in (2,3):
        for tier in (5,6,7):
            reference=loaded[1,tier];current=loaded[run,tier]
            item={'reference_run':1,'run':run,'tier':tier,'record_counts_equal':len(reference)==len(current),'per_record':[]}
            if len(reference)==len(current):
                for i,(left,right) in enumerate(zip(reference,current)):
                    item['per_record'].append({'record_index':i,**same_primitive_sequence(left,right)})
            winners=[next(x['scored_winner_record_index'] for x in results if x['run']==j and x['tier']==tier) for j in (1,run)]
            item['winner_indices_equal']=winners[0]==winners[1]
            item['selected_winner_equality']=same_primitive_sequence(reference[winners[0]],current[winners[1]])
            comparisons.append(item)
    result={'status':'ACTUAL_SCORING_INPUTS_COMPARED','results':results,'comparisons':comparisons,
            'all_official_winners_reproduced':all(x['replayed_winner_matches_actual_official_report'] for x in results),
            'all_selected_winners_exact_native_sequence_equal':all(x['selected_winner_equality'].get('exact_order_and_native_operations_equal') and x['selected_winner_equality'].get('global_phase_equal') for x in comparisons),
            'private_circuit_data_saved_in_evidence':False,'private_parameter_or_fingerprint_values_saved':False,
            'native_parameter_comparison_tolerance':0,'native_parameter_values_persisted':False,'oracle_internal_decomposition_inspected':False,'actual_aer_runs_added_by_this_analysis':0,
            'historical_actual_circuit_comparison_available':False,
            'scope':'Equality concerns actual recorder-normalized native scoring-input circuits across these three local runs, not missing historical remote circuit payloads; raw QPY UUID/metadata byte identity is not required.'}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','all_official_winners_reproduced','all_selected_winners_exact_native_sequence_equal')}))

if __name__=='__main__':main()
