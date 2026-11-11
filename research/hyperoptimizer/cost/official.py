import time
from qiskit import transpile
from qiskit_aer import AerSimulator
from tools.check_submission import compute_metrics,load_config

def score(c,execution_basis=True):
 start=time.perf_counter();sim=AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2)
 native=transpile(c,basis_gates=['rz','sx','x','cx'],optimization_level=1,seed_transpiler=12345,num_processes=1) if execution_basis else transpile(c,sim,optimization_level=1,seed_transpiler=12345,num_processes=1)
 cfg=load_config();scored=transpile(native,**{k:cfg[k] for k in ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')},num_processes=1)
 return {'metrics':compute_metrics(scored),'compile_seconds':time.perf_counter()-start}
