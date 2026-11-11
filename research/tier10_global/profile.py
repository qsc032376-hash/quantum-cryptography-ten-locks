"""Rank each public-power block by whole-circuit removal cost (non-additive)."""
import json,time
from search import *
def main():
    selected=json.loads((OUT/'candidate.json').read_text())['operations'];result={}
    for label,c in [('baseline',solution.build_circuit()),('candidate',builder(selected))]:
        full=score(c);rows=[]
        for index,item in enumerate(c.data):
            if not item.operation.name.startswith('tier10_controlled'):continue
            sub=c.copy_empty_like()
            for j,op in enumerate(c.data):
                if j!=index:sub.append(op.operation,op.qubits,op.clbits)
            measured=score(sub)
            rows.append({'public_power_block':item.operation.name,'marginal_cx':full['metrics']['two_qubit_gates']-measured['metrics']['two_qubit_gates'],'residual':measured})
        result[label]={'full':full,'ranked_removal_cost':sorted(rows,key=lambda r:r['marginal_cx'],reverse=True)}
    (OUT/'profile.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
