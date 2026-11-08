"""New fixed-budget MCX alternatives and already-absorbed QFT detection."""
import importlib
import json
import tempfile
from unittest.mock import patch
from qiskit.synthesis import (synth_mcx_1_dirty_kg24, synth_mcx_2_dirty_kg24,
    synth_mcx_1_clean_kg24, synth_mcx_2_clean_kg24,
    synth_mcx_n_clean_m15, synth_mcx_n_dirty_m15)
from research.circuit_optimizer.metrics import compile_metrics
from research.circuit_optimizer.qft_relabeling import split_boundary_reversal
from research.real_circuits.experiments import ROOT, REF58, REF7, snapshot, gf2_runs


def run():
    rows=[]
    for n,budget,kind,builders in (
        (8,3,'dirty',[synth_mcx_n_dirty_m15,synth_mcx_1_dirty_kg24,synth_mcx_2_dirty_kg24]),
        (6,2,'dirty',[synth_mcx_n_dirty_m15,synth_mcx_1_dirty_kg24,synth_mcx_2_dirty_kg24]),
        (9,4,'clean',[synth_mcx_n_clean_m15,synth_mcx_1_clean_kg24,synth_mcx_2_clean_kg24])):
        for fn in builders:
            circuit=fn(n)
            workspace=circuit.num_qubits-n-1
            assert workspace<=budget
            _,metrics=compile_metrics(circuit)
            rows.append({'controls':n,'budget':budget,'contract':kind,'workspace':workspace,
                         'synthesis':fn.__name__,**metrics})
    with tempfile.TemporaryDirectory(prefix='mcx-screen-') as folder:
        snapshot(REF58,folder,'screen58');snapshot(REF7,folder,'screen7')
        s5=importlib.import_module('screen58.tier05.solution')
        s8=importlib.import_module('screen58.tier08.solution')
        q7=importlib.import_module('screen7.tier07.qpe')
        qft=[]
        for name,circuit in [('tier8',s8._inverse_qft_core(12)),
                             ('tier7',q7.build_inverse_qft(14,reverse_input=False))]:
            try:split_boundary_reversal(circuit,range(circuit.num_qubits))
            except ValueError:qft.append({'tier':name,'boundary_reversal_detected':False})
            else:raise AssertionError('Expected already absorbed input SWAPs')
        full=[]
        with patch.object(s5.oracle,'synth_mcx_n_clean_m15',synth_mcx_2_clean_kg24):
            actual,compile_info=compile_metrics(s5.build_circuit())
            _,score=compile_metrics(actual)
            full.append({'method':'two_clean_only','scoring':score,'solve_compile':compile_info})
            optimized,stats,_=gf2_runs(actual)
            _,score=compile_metrics(optimized)
            full.append({'method':'two_clean_and_gf2','scoring':score,'gf2_stats':stats})
    return {'templates':rows,'qft':qft,'full_tier5':full}

if __name__=='__main__':
    result=run()
    (ROOT/'research/real_circuits/results/mcx_screen.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Fixed-budget template rows:',len(result['templates']))
