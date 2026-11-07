"""Simon recovery from measured equations, with a finite sampling budget.

The output register starts in zero and remains unmeasured. Ignoring that
register gives the same input marginal distribution as measuring and ignoring
its outcome. Keys, equation rows, and measurement counts are never logged.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from common import load_locked
from tier04 import helper


def _load_local_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __package__:
    from .gf2 import row_reduce, recover_unique_nonzero
else:
    # The official Checker loads solution.py by path as a top-level module.
    _gf2 = _load_local_module("team_tier04_gf2", Path(__file__).with_name("gf2.py"))
    row_reduce = _gf2.row_reduce
    recover_unique_nonzero = _gf2.recover_unique_nonzero


N_INPUT_QUBITS = 10
N_QUBITS = 20
ORACLE_NAME = "tier04_oracle"
BATCH_SHOTS = 32
MAX_SHOTS = 128
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 12345


class SamplingLimitError(RuntimeError):
    """A bounded run ended before uniqueness; exposes only nonsecret counts."""

    def __init__(self, rank, shots):
        super().__init__(f"Sampling limit reached at rank {rank} after {shots} shots")
        self.rank = rank
        self.shots = shots


def count_oracle_calls(circuit):
    """Count our opaque outer Oracle blocks before transpilation.

    Tier 4 has no official counter. This does not traverse any gate definition.
    Each shot of this circuit represents one Oracle query.
    """
    return sum(item.operation.name == ORACLE_NAME for item in circuit.data)


def build_circuit():
    """Build 20q/10c: input H -> one Oracle -> input H -> input measurement."""
    circuit = QuantumCircuit(N_QUBITS, N_INPUT_QUBITS, name="tier04_simon")
    circuit.h(range(N_INPUT_QUBITS))
    oracle = helper.build_oracle()
    if oracle.num_qubits != N_QUBITS or oracle.num_clbits != 0:
        raise ValueError("Tier 4 requires a 20-qubit oracle without classical bits")
    block = oracle.to_gate(label="Simon Oracle")
    block.name = ORACLE_NAME  # Name only the new outer wrapper, not its definition.
    circuit.append(block, range(N_QUBITS))
    circuit.h(range(N_INPUT_QUBITS))
    circuit.measure(range(N_INPUT_QUBITS), range(N_INPUT_QUBITS))
    if count_oracle_calls(circuit) != 1:
        raise ValueError("The Simon sampling circuit must contain one oracle block")
    return circuit


def measurement_to_equation(bitstring: str) -> int:
    """Decode c9...c0 so bit j is coefficient j in y dot s = 0 over GF(2)."""
    if not isinstance(bitstring, str):
        raise TypeError("The measurement must be a binary string")
    if len(bitstring) != N_INPUT_QUBITS or any(bit not in "01" for bit in bitstring):
        raise ValueError("Expected exactly 10 binary digits from one register")
    return int(bitstring, 2)


def recover_period_with_diagnostics(*, batch_shots=BATCH_SHOTS, max_shots=MAX_SHOTS):
    """Measure bounded batches, stop at rank 9, and return the unique nonzero s.

    The returned diagnostics contain only ranks, resource counts, and booleans.
    No equation, pivot column, nullspace vector, or actual period is recorded.
    Aer errors propagate without retry. More shots are requested only when
    successful earlier measurements leave the linear system underdetermined.
    """
    if type(batch_shots) is not int or type(max_shots) is not int:
        raise TypeError("Shot budgets must be integers")
    if not 1 <= batch_shots <= MAX_SHOTS or not N_INPUT_QUBITS - 1 <= max_shots <= MAX_SHOTS:
        raise ValueError("Use a positive batch and a total budget between 9 and 128 shots")

    circuit = build_circuit()
    oracle_calls = count_oracle_calls(circuit)
    if oracle_calls != 1:
        raise ValueError("Expected one Oracle query per sampling circuit")
    simulator = AerSimulator(method="statevector", max_memory_mb=512, max_parallel_threads=2)
    compiled = transpile(
        circuit, simulator, basis_gates=BASIS_GATES, optimization_level=1,
        seed_transpiler=SEED_TRANSPILER,
    )
    rows = set()
    total_shots = 0
    history = []
    rank = 0
    while total_shots < max_shots:
        shots = min(batch_shots, max_shots - total_shots)
        result = simulator.run(compiled, shots=shots).result()
        if not result.success:
            raise RuntimeError("Aer failed to execute the Simon circuit")
        counts = result.get_counts(compiled)
        if not counts or any(type(count) is not int or count <= 0 for count in counts.values()):
            raise RuntimeError("Invalid Simon measurement frequencies")
        if sum(counts.values()) != shots:
            raise RuntimeError("Simon measurement count does not match requested shots")
        rows.update(measurement_to_equation(bitstring) for bitstring in counts)
        total_shots += shots
        _, pivots = row_reduce(rows, N_INPUT_QUBITS)
        rank = len(pivots)
        history.append({"shots": shots, "cumulative_shots": total_shots, "rank": rank})
        if rank == N_INPUT_QUBITS:
            raise RuntimeError("Full-rank measurements contradict the nonzero Simon promise")
        if rank == N_INPUT_QUBITS - 1:
            period = recover_unique_nonzero(rows, N_INPUT_QUBITS)
            satisfied = all((row & period).bit_count() % 2 == 0 for row in rows)
            if not 0 < period < 2**N_INPUT_QUBITS or not satisfied:
                raise RuntimeError("GF(2) recovery failed the nonzero nullspace checks")
            return period, {
                "shots": total_shots,
                "max_shots": max_shots,
                "batch_shots": batch_shots,
                "aer_run_calls": len(history),
                "oracle_calls_per_circuit": oracle_calls,
                "oracle_queries_including_shots": oracle_calls * total_shots,
                "rank": rank,
                "nullity": N_INPUT_QUBITS - rank,
                "unique_nonzero_candidate": True,
                "all_observed_equations_satisfied": satisfied,
                "distinct_equations": len(rows),
                "rank_history": history,
            }
    raise SamplingLimitError(rank, total_shots)


def recover_period() -> int:
    """Return the measured 10-bit integer period without printing it."""
    period, _ = recover_period_with_diagnostics()
    return period


def _load_decrypt():
    """Resolve the team module without relying on the team's directory name."""
    if __package__:
        try:
            from ..classical_keystream import decrypt_tier4
        except ModuleNotFoundError as error:
            if error.name != f"{__package__.rsplit('.', 1)[0]}.classical_keystream":
                raise
            raise NotImplementedError("Team classical_keystream.py is missing") from None
        return decrypt_tier4

    path = Path(__file__).resolve().parents[1] / "classical_keystream.py"
    if not path.is_file():
        raise NotImplementedError("Team classical_keystream.py is missing")
    return _load_local_module("team_classical_keystream", path).decrypt_tier4


def solve() -> str:
    """Measure Simon's period and pass its integer to the shared decryptor."""
    decrypt_tier4 = _load_decrypt()
    period = recover_period()
    plaintext = decrypt_tier4(period, load_locked(4)["ciphertext_hex"])
    if not isinstance(plaintext, str):
        raise TypeError("The classical module must return plaintext as a string")
    return plaintext
