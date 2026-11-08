"""Tier 10 candidate C, opt-in local benchmark; never changes Tier 9 code."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from common import load_locked
from submissions.team3.tier10.circuit import build_exponent_mapping, build_qpe_circuit
from submissions.team3.tier07.qpe import build_inverse_qft
from submissions.team3.tier10.shared_control import shared_circuit, shared_multiplier



def baseline_circuit(p, g, A, t=6, w=7):
    qc = QuantumCircuit(2*t+w, 2*t)
    qc.x(2*t); qc.h(range(2*t))
    qc.compose(build_exponent_mapping(p,g,A,t,w), inplace=True)
    qft = build_inverse_qft(t).to_gate()
    qc.append(qft,range(t)); qc.append(qft,range(t,2*t))
    qc.measure(range(2*t),range(2*t))
    return qc


if __name__ == '__main__':
    import resource, time
    from tools.check_submission import compute_metrics
    mode = sys.argv[1]
    p = load_locked(10)['public_parameters']
    builder = {'A':baseline_circuit, 'B':build_qpe_circuit, 'C':shared_circuit}[mode]
    start=time.perf_counter()
    circuit=builder(p['p'],p['g'],p['A'])
    simulator=AerSimulator(method='statevector', max_memory_mb=512, max_parallel_threads=2)
    native=transpile(circuit, simulator, optimization_level=1,seed_transpiler=12345,num_processes=1)
    built=time.perf_counter()
    scored=transpile(native,basis_gates=['rz','sx','x','cx'],coupling_map=None,optimization_level=1,seed_transpiler=12345,num_processes=1)
    print(mode, compute_metrics(scored), 'build_native_s',round(built-start,3),
          'score_s',round(time.perf_counter()-built,3),
          'peak_rss_bytes',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, flush=True)
