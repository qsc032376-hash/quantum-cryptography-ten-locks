"""Whole-circuit and isolated contribution screen; contains no secrets."""
from pathlib import Path
import json,sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
from submissions.team3.tier10 import solution
from screen import score
from qiskit import QuantumCircuit
c=solution.build_circuit();blocks=[]
for item in c.data:
    if item.operation.name.startswith('tier10_controlled_'):
        block=item.operation.definition
        widths=Counter(getattr(x.operation,'num_ctrl_qubits',0) for x in block.data)
        blocks.append({'index':len(blocks),'logical_controls_histogram':dict(widths),'isolated_scoring':score(block)})
qfts=[i.operation.definition for i in c.data if i.operation.name not in ('measure','h','x') and not i.operation.name.startswith('tier10_controlled_')]
assert len(blocks)==12 and len(qfts)==2
result={'blocks':blocks,'qft_isolated':score(qfts[0]),'whole':score(c)}
print(json.dumps(result,indent=2));(ROOT/'research/tier10_structural_v3/costs.json').write_text(json.dumps(result,indent=2)+'\n')
