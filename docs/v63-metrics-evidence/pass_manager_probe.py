"""Read-only pass-manager inventory and bounded public compile/serialization probes.
No Aer run; no Oracle definitions, numeric parameters, or private payloads are saved.
"""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import numbers
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import warnings

BASIS=['rz','sx','x','cx']
SAFE_FIELDS=('method','_basis_gates','_target_basis','_min_qubits','_approximation_degree',
             '_plugin_config','_fallback_on_default','_pulse_optimize','_natural_direction',
             'qubits_initially_zero','recurse','_property','basis','basis_gates',
             'force_consolidate','requested_fidelity','split_swap','_instruction_names','_recurse')


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def safe(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,(set,frozenset)):return sorted(safe(v) for v in value)
    if isinstance(value,(tuple,list)):return [safe(v) for v in value]
    if isinstance(value,dict):return {str(k):safe(v) for k,v in sorted(value.items(),key=lambda x:str(x[0]))}
    return {'public_type':value.__class__.__module__+'.'+value.__class__.__qualname__}


def flow_tree(task):
    row={'class':task.__class__.__module__+'.'+task.__class__.__qualname__}
    attrs=vars(task)
    config={k:safe(attrs[k]) for k in SAFE_FIELDS if k in attrs}
    if config:row['configuration']=config
    for key in ('condition','do_while'):
        if key in attrs:
            fn=attrs[key];row[key]={'module':getattr(fn,'__module__',None),'qualname':getattr(fn,'__qualname__',fn.__class__.__qualname__)}
    if hasattr(task,'tasks'):row['tasks']=[flow_tree(x) for x in task.tasks]
    return row


def names(tree):
    yield tree['class'].split('.')[-1]
    for child in tree.get('tasks',[]):yield from names(child)


def manifests():
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_aer import AerSimulator
    result=[]
    for label,level,with_backend in [('official_scoring',1,False),('tier05_precompile',2,True),('tier06_tier07_precompile',2,False)]:
        kwargs={'optimization_level':level,'basis_gates':BASIS,'seed_transpiler':12345,
                'coupling_map':None,'initial_layout':None}
        if with_backend:kwargs['backend']=AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');pm=generate_preset_pass_manager(**kwargs)
        stages={stage:flow_tree(getattr(pm,stage).to_flow_controller()) for stage in pm.expanded_stages if getattr(pm,stage,None) is not None}
        classes=[n for tree in stages.values() for n in names(tree)]
        row={'label':label,'optimization_level':level,'basis_gates':BASIS,'seed_transpiler':12345,
             'coupling_map':None,'initial_layout':None,'backend_present':with_backend,
             'expanded_stage_order':list(pm.expanded_stages),'active_stages':stages,
             'layout_stage_present':pm.layout is not None,'routing_stage_present':pm.routing is not None,
             'sabre_or_stochastic_swap_passes_present':sorted(set(classes)&{'SabreLayout','SabreSwap','StochasticSwap'}),
             'flow_class_and_config_digest_sha256':digest(stages),
             'warnings':[{'category':w.category.__name__,'message':str(w.message)} for w in caught]}
        if with_backend:
            target=kwargs['backend'].target;row['backend_target_summary']={'num_qubits':target.num_qubits,
                'operation_names':sorted(target.operation_names),'basis_override_used_by_approved_solver':True}
        result.append(row)
    return result


def structure(circuit):
    rows=[]
    for item in circuit.data:
        op=item.operation;name=op.name
        if re.fullmatch(r'circuit-\d+',name):name='circuit-<generated-counter>'
        rows.append({'name':name,'public_class':op.base_class.__module__+'.'+op.base_class.__qualname__,
                     'qubits':[circuit.find_bit(q).index for q in item.qubits],
                     'clbits':[circuit.find_bit(q).index for q in item.clbits],
                     'parameter_count':len(op.params)})
    canonical={'qubits':circuit.num_qubits,'clbits':circuit.num_clbits,'instructions':rows}
    return digest(canonical)


def primitive_equal(a,b):
    allow={'rz','sx','x','cx','measure','barrier'}
    if not set(a.count_ops())<=allow or not set(b.count_ops())<=allow:return {'supported':False}
    if (a.num_qubits,a.num_clbits,len(a.data))!=(b.num_qubits,b.num_clbits,len(b.data)):return {'supported':True,'equal':False}
    equal=bool(a.global_phase==b.global_phase)
    for x,y in zip(a.data,b.data):
        if (x.operation.name!=y.operation.name or x.operation.base_class is not y.operation.base_class
            or [a.find_bit(q).index for q in x.qubits]!=[b.find_bit(q).index for q in y.qubits]
            or [a.find_bit(q).index for q in x.clbits]!=[b.find_bit(q).index for q in y.clbits]
            or len(x.operation.params)!=len(y.operation.params)):
            equal=False;break
        if not all(isinstance(l,numbers.Number) and isinstance(r,numbers.Number) and bool(l==r) for l,r in zip(x.operation.params,y.operation.params)):
            equal=False;break
    return {'supported':True,'equal':equal,'parameter_tolerance':0,'global_phase_included':True}


def roundtrip(circuit):
    from qiskit import qpy
    buf=io.BytesIO();qpy.dump(circuit,buf);buf.seek(0);result=qpy.load(buf);assert len(result)==1;return result[0]


def worker(root,tier):
    sys.path.insert(0,str(root))
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from tools.check_submission import compute_metrics,load_config
    path=root/f'submissions/team3/tier{tier:02d}/solution.py'
    spec=importlib.util.spec_from_file_location(f'pass_probe_tier{tier}',path)
    solution=importlib.util.module_from_spec(spec);sys.modules[spec.name]=solution;spec.loader.exec_module(solution)
    original=solution.build_circuit();cfg=load_config();native=[];scored=[];rows=[]
    for variant,constructed in [('direct',original),('qpy_roundtrip_before_precompile',roundtrip(original))]:
        started=time.monotonic()
        if tier==5:
            backend=AerSimulator(method='statevector',max_memory_mb=512,max_parallel_threads=2)
            compiled=transpile(constructed,backend,basis_gates=solution.BASIS_GATES,optimization_level=2,seed_transpiler=solution.SEED_TRANSPILER,num_processes=1)
            compiled,_,_=solution.gf2_synthesis.gf2_runs(compiled)
        else:
            compiled=transpile(constructed,basis_gates=solution.BASIS_GATES,optimization_level=solution.PRE_OPTIMIZATION_LEVEL,seed_transpiler=solution.SEED_TRANSPILER,num_processes=1)
        # Preserve official recorder's metadata/name canonicalization and QPY transport.
        actual=compiled.copy();actual.metadata={};actual.name='scored';actual=roundtrip(actual)
        score=transpile(actual,**{k:cfg[k] for k in ('basis_gates','coupling_map','initial_layout','optimization_level','seed_transpiler')})
        def summary(c):return {'structural_digest_sha256':structure(c),'metrics':compute_metrics(c),'count_ops':{k:int(v) for k,v in c.count_ops().items()}}
        rows.append({'variant':variant,'constructed':summary(constructed),'precompiled':summary(compiled),'scored':summary(score),'seconds':time.monotonic()-started})
        native.append(compiled);scored.append(score)
    return {'tier':tier,'rows':rows,'roundtrip_native_equality':primitive_equal(*native),'roundtrip_scored_equality':primitive_equal(*scored),
            'scope':'Tier5 sole solver circuit compile flow' if tier==5 else 'Tier6 nominal default12-round builder only; no measured calibration or Aer execution',
            'aer_runs':0}


def main():
    p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--official-root',type=Path,required=True);p.add_argument('--worker',type=int);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.worker:print(json.dumps(worker(a.official_root,a.worker)));return
    assert a.output and not a.output.exists()
    start=time.monotonic();env=os.environ.copy();env.update(PYTHONHASHSEED='0',QISKIT_PARALLEL='FALSE',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    result={'status':'RUNNING','python':platform.python_version(),'qiskit':importlib.metadata.version('qiskit'),'qiskit_aer':importlib.metadata.version('qiskit-aer'),
            'pass_managers':manifests(),'trials':[],'planned_trials':'Two fresh processes per publicTier5/Tier6 builder, direct and QPY-roundtrip-before-precompile ineach',
            'aer_runs':0,'production_or_official_files_modified':False,'oracle_definitions_inspected':False,
            'structural_digest_schema':'sha256canonicalJSON_v1: ordered public gate class/name, qubit/clbit indices andparametercount; excludesnumericparameter/globalphasevalues,labels,registerUUID,metadata,opaqueinternals',
            'structural_digest_is_not_unitary_identity':True,'parameter_values_saved':False,
            'thread_environment':{k:env.get(k) for k in ('PYTHONHASHSEED','QISKIT_PARALLEL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','RAYON_NUM_THREADS')},
            'historical_actual_pass_trace_available':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    for tier in (5,6):
        for trial in (1,2):
            cmd=[sys.executable,str(Path(__file__).resolve()),'--repository',str(a.repository),'--official-root',str(a.official_root),'--worker',str(tier)]
            try:
                done=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=25)
                if done.returncode:row={'tier':tier,'trial':trial,'status':'FAILED','private_error_output_saved':False}
                else:row={'trial':trial,'status':'PASS',**json.loads(done.stdout)}
            except subprocess.TimeoutExpired:row={'tier':tier,'trial':trial,'status':'TIMEOUT'}
            result['trials'].append(row);a.output.write_text(json.dumps(result,indent=2)+'\n')
            if row['status']!='PASS':result['status']='INCOMPLETE';break
        if result['status']=='INCOMPLETE':break
    comparison={}
    for tier in (5,6):
        pair=[x for x in result['trials'] if x['tier']==tier and x['status']=='PASS']
        if len(pair)!=2:continue
        def stable(trial):return [{k:row[k] for k in ('variant','constructed','precompiled','scored')} for row in trial['rows']]
        comparison[str(tier)]={'fresh_process_structural_digests_and_counts_equal':stable(pair[0])==stable(pair[1]),
            'qpy_roundtrip_before_precompile_preserves_native_and_scored_exact_primitive_sequences':all(x['roundtrip_native_equality'].get('equal') and x['roundtrip_scored_equality'].get('equal') for x in pair)}
    result['comparison']=comparison;result['elapsed_seconds']=time.monotonic()-start
    if result['status']!='INCOMPLETE':result['status']='COMPLETE'
    result['conclusion']='Bounded same-host probes identify pass plans and test serialization/order stability; they do not isolate missing historical platform or native-library cause.'
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'elapsed_seconds':result['elapsed_seconds'],'comparison':comparison}))

if __name__=='__main__':main()
