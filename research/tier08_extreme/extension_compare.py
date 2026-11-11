"""Score bounded post-authorization whole-circuit architecture alternatives.

No Aer job executes and no production source is modified. General-linear
coordinates have explicit unconditional pre/post CNOT boundaries included
in each controlled multiplier before the complete scoring pipeline.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from qiskit import QuantumCircuit
from research.tier08_extreme import affine_linear,screen
from research.tier08_extreme.emitter import build_from_operations
from submissions.team3.tier08 import solution


def linear_circuit(specification):
    def multiplier(d,p,w):
        assert p==35 and w==6
        candidate=specification[str(d)]
        affine_linear.verify(candidate,d)
        middle=build_from_operations(candidate['operations'],w,mode='native')
        c=QuantumCircuit(middle.num_qubits,name='tier08_controlled_modular_multiply')
        for control,target in candidate['pre_cx']:
            c.cx(control+1,target+1)
        c.compose(middle,inplace=True)
        for control,target in candidate['post_cx']:
            c.cx(control+1,target+1)
        return c
    with patch.object(solution,'build_controlled_multiplier',multiplier):
        return solution.build_circuit()


def main():
    out=Path(__file__).parent;start=time.perf_counter()
    target=out/'extension_candidates.json';assert not target.exists()
    names=['extension_compare.py','affine_linear.py','affine_linear.json','adaptive_boolean.json',
           'adaptive_whole.json','screen.py','emitter.py']
    result={'source_inputs':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names},
            'note':'Post-authorization new architecture screens; actual complete solve-time plus official scoring transpilation, no Aer execution.',
            'baseline_adaptive':json.loads((out/'adaptive_whole.json').read_text()),'candidates':[]}
    affine=json.loads((out/'affine_linear.json').read_text())['selected']
    circuit=linear_circuit(affine)
    result['candidates'].append({'name':'general_linear_native','whole':screen.score(circuit),
                                 'powers':solution.count_modular_powers(circuit)})
    adaptive=json.loads((out/'adaptive_boolean.json').read_text())['selected']
    for name,emission in [
        ('adaptive_native_last',{'mode':'native','pivot':'last','allocation':'work_first'}),
        ('adaptive_dirty_first',{'mode':'dirty','pivot':'first','allocation':'work_first'}),
        ('adaptive_dirty_last_external',{'mode':'dirty','pivot':'last','allocation':'external_first'})]:
        circuit=screen.build(adaptive,**emission)
        result['candidates'].append({'name':name,'emission':emission,'whole':screen.score(circuit),
                                     'powers':solution.count_modular_powers(circuit)})
    result['seconds']=time.perf_counter()-start
    target.write_text(json.dumps(result,indent=2)+'\n')
    for row in result['candidates']:
        print(row['name'],row['whole']['metrics'],flush=True)


if __name__=='__main__':main()
