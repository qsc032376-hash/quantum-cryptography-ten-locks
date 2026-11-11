"""Coherent consistency audit of the pinned Tier 6 baseline; outputs scalars only."""
import json


import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from submissions.team3.tier06 import solution as tier


def run():
    byte = tier._public_inputs()[0][0]
    phase = tier.build_phase_oracle(byte)
    marker = tier.build_bit_oracle(byte)
    data = list(range(tier.KEY_BITS))
    work = list(range(tier.KEY_BITS, phase.num_qubits))
    flag = marker.num_qubits - 1
    circuit = QuantumCircuit(marker.num_qubits)
    circuit.h(data)
    circuit.x(flag)
    circuit.h(flag)
    circuit.compose(phase, range(phase.num_qubits), inplace=True)
    circuit.save_probabilities(work, label="phase_workspace")
    circuit.compose(marker, inplace=True)
    circuit.save_probabilities(work, label="marker_workspace")
    circuit.h(flag)
    circuit.x(flag)
    circuit.h(data)
    # Check return of the full register without exporting any amplitude array.
    circuit.save_amplitudes([0], label="return_amplitude")
    backend = AerSimulator(method="statevector", max_parallel_threads=2, max_memory_mb=1024)
    compiled = transpile(circuit, backend, optimization_level=0, seed_transpiler=12345)
    result = backend.run(compiled, shots=1).result()
    if not result.success:
        raise RuntimeError(result.status)
    saved = result.data()
    search = tier.build_circuit(iterations=2)
    mapping = [(search.find_bit(op.qubits[0]).index, search.find_bit(op.clbits[0]).index)
               for op in search.data if op.operation.name == "measure"]
    stats = {
        "phase_workspace_leakage": float(np.sum(saved["phase_workspace"][1:])),
        "combined_workspace_leakage": float(np.sum(saved["marker_workspace"][1:])),
        "return_amplitude_error": float(abs(saved["return_amplitude"][0] - 1)),
        "two_round_search_query_count": tier.count_oracle_calls(search),
        "search_measurement_identity": mapping == list(zip(data, data)),
    }
    assert max(stats[k] for k in ("phase_workspace_leakage", "combined_workspace_leakage",
                                   "return_amplitude_error")) < 1e-10
    assert stats["two_round_search_query_count"] == {"phase": 2, "bit_predicate": 0} and stats["search_measurement_identity"]
    return stats


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
