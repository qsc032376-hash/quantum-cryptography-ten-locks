"""Bounded prepared 18-qubit state equivalence; vectors stay in RAM only."""
import argparse
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time


def worker(root, variant, connection):
    try:
        sys.path.insert(0, str(root))
        import numpy as np
        from qiskit import transpile
        from qiskit_aer import AerSimulator
        from unittest.mock import patch
        from submissions.team3.tier08 import solution, modular
        started = time.perf_counter()
        if variant == 'baseline':
            with patch.object(solution, 'build_controlled_multiplier', modular._validated_hybrid_multiplier):
                circuit = solution.build_circuit()
        else:
            circuit = solution.build_circuit()
        circuit = circuit.remove_final_measurements(inplace=False)
        compiled = transpile(circuit, basis_gates=solution.BASIS_GATES,
                             optimization_level=1, seed_transpiler=12345, num_processes=1)
        compilation = time.perf_counter()-started
        compiled.save_statevector()
        simulator = AerSimulator(method='statevector', max_memory_mb=512, max_parallel_threads=2)
        sim_started = time.perf_counter()
        result = simulator.run(compiled, shots=1, seed_simulator=20261111).result()
        assert result.success
        vector = np.asarray(result.get_statevector(), dtype=np.complex128)
        connection.send({'status':'PASS','vector':vector,'qubits':circuit.num_qubits,
                         'compile_seconds':compilation,'aer_seconds':time.perf_counter()-sim_started,
                         'wall_seconds':time.perf_counter()-started})
    except Exception as exc:
        # Do not serialize exception text that might contain problem data.
        connection.send({'status':'FAIL','exception_class':type(exc).__name__})
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Do not overwrite prior evidence')
    import numpy as np
    context=mp.get_context('spawn')
    records={};vectors=[]
    for variant in ('baseline','candidate'):
        parent,child=context.Pipe(duplex=False)
        proc=context.Process(target=worker,args=(args.root,variant,child))
        proc.start();child.close()
        if not parent.poll(120):
            proc.kill();proc.join();records[variant]={'status':'TIMEOUT','cap_seconds':120}
            args.output.write_text(json.dumps({'status':'FAIL','runs':records},indent=2)+'\n')
            raise RuntimeError('Bounded state audit stopped; no retry')
        result=parent.recv();parent.close();proc.join(10)
        if proc.is_alive():proc.kill();proc.join()
        vector=result.pop('vector',None);records[variant]=result
        if result['status']!='PASS':
            args.output.write_text(json.dumps({'status':'FAIL','runs':records},indent=2)+'\n')
            raise RuntimeError('State audit failed; no retry')
        vectors.append(vector)
        print(variant,result,flush=True)
    a,b=vectors
    amplitude=float(np.max(np.abs(a-b)))
    probability=float(np.max(np.abs(np.abs(a)**2-np.abs(b)**2)))
    marginal=float(np.max(np.abs((np.abs(a)**2).reshape(64,4096).sum(axis=0)
                                 -(np.abs(b)**2).reshape(64,4096).sum(axis=0))))
    report={'status':'PASS' if max(amplitude,probability,marginal)<1e-8 else 'FAIL',
            'basis_amplitudes_compared':len(a),'prepared_state_only':True,
            'dense_whole_operator_claimed':False,'global_phase_alignment':False,
            'max_complex_amplitude_error':amplitude,'max_joint_probability_error':probability,
            'max_count_register_marginal_error':marginal,'tolerance':1e-8,
            'runs':records,'private_arrays_written':False,
            'measurement_circuits_modified':False,
            'method':'Remove final measurements for validation only; compile full prepared circuits as production, then save statevectors in RAM.',
            'runtime_sha256':{str(p.relative_to(args.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (args.root/'submissions/team3/tier08').glob('*.py')}}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print({k:report[k] for k in ('status','max_complex_amplitude_error','max_count_register_marginal_error')},flush=True)
    if report['status']!='PASS':raise RuntimeError('State equivalence failed')


if __name__ == '__main__':
    main()
