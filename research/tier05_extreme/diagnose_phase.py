"""Investigate failed raw-amplitude comparison without recording statevectors."""
import json,numpy as np
from search import *
from verify import evolve
cfg=json.loads((OUT/'candidate.json').read_text());init=np.zeros(1<<19,complex);init[0]=1
vectors=[];rows=[]
for label,c,config in [('baseline',solution.build_circuit(),{'level':1,'gf2':True}),('candidate',build_config(cfg),cfg),('candidate_L1',build_config(cfg),{**cfg,'level':1})]:
 native=compile_actual(c,config)[1].remove_final_measurements(inplace=False)
 vectors.append(evolve(native,init));rows.append({'label':label,'logical_global_phase':float(c.global_phase),'compiled_global_phase':float(native.global_phase)})
for row,v in zip(rows,vectors):
 overlap=np.vdot(vectors[0],v);row.update(overlap_real=float(overlap.real),overlap_imag=float(overlap.imag),max_probability_difference=float(np.max(np.abs(np.abs(v)**2-np.abs(vectors[0])**2))),aligned_error=float(np.max(np.abs(v-overlap/abs(overlap)*vectors[0]))))
(OUT/'phase-diagnostic.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows,flush=True)
