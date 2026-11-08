"""Bounded public-circuit ablation; report metrics only, never recover a log."""
import argparse
import inspect
from itertools import permutations
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import CCXGate, RCCXGate
from qiskit.quantum_info import Operator
from qiskit.synthesis import synth_mcx_1_clean_kg24, synth_mcx_noaux_v24
from qiskit_aer import AerSimulator
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import load_locked
from submissions.team3.tier09.modular import _compiled_operations
from submissions.team3.tier10 import shared_control, solution
from submissions.team3.tier10.synthesis import select_operations
from tools.check_submission import compute_metrics, load_config


def replace_high_controls(circuit, clean):
    result = QuantumCircuit(circuit.num_qubits + int(clean))
    for instr in circuit.data:
        wires = [circuit.find_bit(q).index for q in instr.qubits]
        k = len(wires)-1
        if k >= 4:
            if clean:
                template = synth_mcx_1_clean_kg24(k)
                wires.append(circuit.num_qubits)
            else:
                template = synth_mcx_noaux_v24(k)
            result.compose(template, wires, inplace=True)
        else:
            result.append(instr.operation, wires)
    return result


def with_clean_scratch(circuit):
    """Compile-only alternative: lend the same new zero wire to every MCX."""
    out = QuantumCircuit(circuit.num_qubits+1, circuit.num_clbits)
    for instr in circuit.data:
        wires = [circuit.find_bit(q).index for q in instr.qubits]
        cbits = [circuit.find_bit(c).index for c in instr.clbits]
        if instr.operation.name.startswith("tier10_controlled_"):
            block = replace_high_controls(instr.operation.definition, clean=True)
            gate = block.to_gate().copy(name=instr.operation.name)
            out.append(gate, [*wires,circuit.num_qubits])
        else:
            out.append(instr.operation, wires, cbits)
    return out


def edge_cancellations(d, p, width):
    # Only immediate native cancellations; label each distinct outer control
    # separately. Work wires keep the same labels across all 12 blocks.
    sequences = []
    for ctrl, multiplier in enumerate(d):
        circuit = shared_control.fanout_multiplier(multiplier,p,width)
        seq = []
        for instr in circuit.data:
            ids = [circuit.find_bit(q).index for q in instr.qubits]
            mapped = [i if i else -(ctrl+1) for i in ids]
            seq.append((tuple(sorted(mapped[:-1])), mapped[-1]))
        sequences.append(seq)
    def exposable(gates):
        controls, targets, movable = set(), set(), set()
        for gate in gates:
            predicate, target = gate
            if target not in controls and not targets.intersection(predicate):
                movable.add(gate)
            controls.update(predicate)
            targets.add(target)
        return movable

    heads = [exposable(seq) for seq in sequences]
    tails = [exposable(reversed(seq)) for seq in sequences]
    movable = {(i,j):len(tails[i] & heads[j]) for i,j in permutations(range(len(d)),2)}
    overlaps = {}
    for i,j in permutations(range(len(d)),2):
        n = 0
        for left,right in zip(reversed(sequences[i]),sequences[j]):
            if left != right:
                break
            n += 1
        overlaps[i,j] = n
    return {"current_order_commuting_matches":sum(movable[i,i+1] for i in range(len(d)-1)),
            "best_commuting_boundary":max(movable.values(),default=0),
            "ordered_pairs_with_commuting_matches":sum(n>0 for n in movable.values()),
            "current_order_adjacent_pairs":sum(overlaps[i,i+1] for i in range(len(d)-1)),
            "best_single_boundary":max(overlaps.values(),default=0),
            "ordered_pairs_with_overlap":sum(n>0 for n in overlaps.values())}


def main():
    public = load_locked(10)["public_parameters"]
    p,g,A = (public[k] for k in ("p","g","A"))
    cfg = load_config()
    official = {k:cfg[k] for k in ("basis_gates","coupling_map","initial_layout","optimization_level","seed_transpiler")}
    sim = AerSimulator(method="statevector",max_memory_mb=512,max_parallel_threads=2)
    def metrics(circuit):
        native = transpile(circuit,sim,optimization_level=1,seed_transpiler=12345,num_processes=1)
        return compute_metrics(transpile(native,**official))

    report = {"whole_preflight":{}, "isolated_first_power":{}}
    for name, selector in (("v5",_compiled_operations),("short",select_operations)):
        with patch.object(shared_control,"select_operations",selector):
            report["whole_preflight"][name] = metrics(solution.build_circuit())
            block = shared_control.fanout_multiplier(g,p,7)
            report["isolated_first_power"][name] = metrics(block)
    report["whole_preflight"]["one_clean_kg24"] = metrics(with_clean_scratch(solution.build_circuit()))
    for name,clean in (("explicit_noaux_v24",False),("one_clean_kg24",True)):
        block = replace_high_controls(shared_control.fanout_multiplier(g,p,7),clean)
        report["isolated_first_power"][name] = metrics(block)
    # Check the optional clean template's zero-input columns, including leakage.
    check = {}
    from qiskit.circuit.library import MCXGate
    for n in range(4,8):
        ideal = Operator(MCXGate(n)).data
        size = ideal.shape[0]
        actual = Operator(synth_mcx_1_clean_kg24(n)).data[:, :size]
        err = max(np.max(np.abs(actual[:size]-ideal)),np.max(np.abs(actual[size:])))
        if err >= 1e-12:
            raise RuntimeError("Ancilla or relative phase mismatch")
        check[str(n)] = float(err)
    report["clean_template_column_error"] = check
    report["uncompensated_rccx_vs_ccx_max_error"] = float(np.max(np.abs(
        Operator(RCCXGate()).data-Operator(CCXGate()).data)))
    multipliers = [pow(base,1<<j,p) for base in (g,A) for j in range(6)]
    report["edges"] = edge_cancellations(multipliers,p,7)
    print(json.dumps(report,indent=2))


def clean_trials(harness, out_dir, official):
    """Compare a research-only 20-wire snapshot; never change the submission."""
    sys.path.insert(0,str(harness.resolve()))
    from benchmarks.common import snapshot, run_worker

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        snapshot("191f1f0abcb21dd9ad19b3ebaff1d7cacefd4dcd", root)
        solution_py = root/"submissions/team3/tier10/solution.py"
        with solution_py.open("a",encoding="utf-8") as f:
            f.write("\nfrom qiskit import QuantumCircuit\n")
            f.write("from qiskit.synthesis import synth_mcx_noaux_v24, synth_mcx_1_clean_kg24\n")
            f.write(inspect.getsource(replace_high_controls)+"\n"+inspect.getsource(with_clean_scratch))
            f.write("\n_original_builder = build_circuit\n"
                    "def build_circuit(**kwargs):\n    return with_clean_scratch(_original_builder(**kwargs))\n")
        if official:
            result = run_worker("official",root,10,None,300,1536)
            (out_dir/"clean-official.json").write_text(json.dumps(result,indent=2))
        trials = []
        for seed in (1000,1001):
            row = run_worker("cross",root,10,seed,120,1536)
            trials.append(row)
            print(seed,row.get("hash_ok"),row["resource"]["state"],flush=True)
        (out_dir/"clean-seeds.json").write_text(json.dumps(trials,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-harness",type=Path)
    parser.add_argument("--out",type=Path,default=Path("reports"))
    parser.add_argument("--official",action="store_true")
    args = parser.parse_args()
    if args.clean_harness:
        clean_trials(args.clean_harness,args.out,args.official)
    else:
        main()
