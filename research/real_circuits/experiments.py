"""Scout legal public blocks in pinned candidate snapshots, without Aer."""
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate
from research.circuit_optimizer.gf2_synthesis import optimize, extract_matrix
from research.circuit_optimizer.commutation_rules import cancel_inverses
from research.circuit_optimizer.metrics import compile_metrics

ROOT = Path(__file__).resolve().parents[2]
REF58 = '0988ac44d88d08cc12258f2010afaf792dd53e7b'
REF7 = '7aef6e714dbbc8d222ef168b4bd691078f823b6e'


def snapshot(ref, folder, name):
    data = subprocess.check_output(['git', 'archive', ref, 'submissions/team3'], cwd=ROOT)
    destination = Path(folder) / name
    destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(destination, filter='data')
    team = destination / 'submissions' / name
    (destination / 'submissions/team3').rename(team)
    sys.path.insert(0, str(team.parent))
    return team


def gf2_runs(circuit):
    """Maximal consecutive native CX windows; no nested definitions opened."""
    result = circuit.copy_empty_like()
    pending = []
    stats = {'windows': 0, 'accepted': 0, 'removed_cx': 0, 'max_window_wires': 0}
    certificates = []
    def flush():
        if not pending:
            return
        wires = sorted({circuit.find_bit(q).index for item in pending for q in item.qubits})
        block = QuantumCircuit(len(wires))
        for item in pending:
            block.cx(*[wires.index(circuit.find_bit(q).index) for q in item.qubits])
        candidate, accepted = optimize(block)
        assert np.array_equal(extract_matrix(block), extract_matrix(candidate))
        stats['windows'] += 1
        stats['accepted'] += accepted
        stats['removed_cx'] += block.size() - candidate.size()
        stats['max_window_wires'] = max(stats['max_window_wires'], len(wires))
        if accepted:
            certificates.append((block, candidate))
        for item in candidate.data:
            result.append(item.operation, [wires[candidate.find_bit(q).index] for q in item.qubits])
        pending.clear()
    for item in circuit.data:
        if item.operation.base_class is CXGate and item.operation.ctrl_state == 1:
            pending.append(item)
        else:
            flush()
            result.append(item)
    flush()
    return result, stats, certificates


def compare(label, circuit):
    native, native_metrics = compile_metrics(circuit)
    _, baseline = compile_metrics(native)
    records = []
    for method in ('source_gf2', 'source_cancel', 'compiled_cancel', 'compiled_gf2'):
        source = native if method.startswith('compiled') else circuit
        start = time.perf_counter()
        if method.endswith('gf2'):
            changed, stats, _ = gf2_runs(source)
        else:
            changed, removed = cancel_inverses(source)
            stats = {'removed_instructions': removed}
        pass_seconds = time.perf_counter() - start
        # Source changes receive solve-time compilation then official scoring.
        actual, first = compile_metrics(changed)
        _, scored = compile_metrics(actual)
        records.append({'case': label, 'method': method, 'baseline': baseline,
                        'candidate': scored, 'pass_seconds': pass_seconds,
                        'solve_compile_seconds': first['compilation_seconds'], 'stats': stats})
        print(label, method, baseline['two_qubit_gates'], baseline['depth'], '->',
              scored['two_qubit_gates'], scored['depth'], stats, flush=True)
    return records


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix='real-circuits-') as folder:
        snapshot(REF58, folder, 'real58')
        snapshot(REF7, folder, 'real7')
        s5 = importlib.import_module('real58.tier05.solution')
        s8 = importlib.import_module('real58.tier08.solution')
        q7 = importlib.import_module('real7.tier07.qpe')
        ciphertext, _ = s5._public_inputs()  # Published ciphertext, not hidden data.
        for name, c in [('tier5_mask0', s5.oracle._build_mask_transform(0)),
                        ('tier5_mask1', s5.oracle._build_mask_transform(1)),
                        ('tier5_diffuser', s5.oracle.build_diffuser()),
                        ('tier5_phase_oracle', s5.oracle.build_phase_oracle(ciphertext)),
                        ('tier5_full', s5.build_circuit(ciphertext=ciphertext))]:
            rows += compare(name, c)
        seen = set()
        for j in range(12):
            multiplier = pow(2, 1 << j, 35)
            if multiplier in seen:
                continue
            seen.add(multiplier)
            rows += compare(f'tier8_public_multiplier_{multiplier}',
                            s8.build_controlled_multiplier(multiplier, 35, 6))
        rows += compare('tier8_full', s8.build_circuit(modulus=35))
        rows += compare('tier7_qft_core', q7.build_inverse_qft(14, reverse_input=False))
    out = ROOT / 'research/real_circuits/results/scout.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'refs': {'tier5_8': REF58, 'tier7': REF7},
                              'official_checker_run': False, 'records': rows}, indent=2) + '\n')

if __name__ == '__main__':
    main()
