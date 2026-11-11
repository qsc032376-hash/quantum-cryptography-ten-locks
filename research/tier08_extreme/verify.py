"""Independent, phase-sensitive Tier 8 controlled-block verification.

The complete-block comparison extends the earlier independent audit at
3dac27e9d5c9ea9cf98a6a90edbb3afcbaca02bc:research/tier08_osc/audit.py.
Expected matrices are constructed directly from the PUBLIC modular mapping,
not from the synthesis implementation or an inferred order. No secret values,
recovered factors, raw measurement strings or plaintext are recorded.

Run with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1.
This is a finite numerical audit, not a formal proof of floating-point code.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "submissions")]

import numpy as np
from qiskit.quantum_info import Operator, Statevector

BASELINE = "c4455782ea9388d5897fc27270f42dd3786ed35d"
PUBLIC_MULTIPLIERS = (2, 4, 11, 16)
TOLERANCE = 1e-9


def public_destination(column: int, multiplier: int, modulus: int, work_bits: int) -> int:
    """Independent mathematical controlled permutation, preserving every extra bit."""
    control = column & 1
    work_mask = (1 << work_bits) - 1
    value = (column >> 1) & work_mask
    result = multiplier * value % modulus if control and value < modulus else value
    return (column & ~(work_mask << 1)) | (result << 1)


def operator_check(circuit, multiplier: int, modulus: int, work_bits: int) -> dict:
    started = time.monotonic()
    wires = circuit.num_qubits
    dimension = 1 << wires
    if wires > 10:
        raise ValueError("Refusing an unexpectedly large dense operator")
    actual = Operator(circuit).data
    destinations = np.array([
        public_destination(column, multiplier, modulus, work_bits)
        for column in range(dimension)
    ])
    if len(set(map(int, destinations))) != dimension:
        raise AssertionError("The independently constructed mapping is not bijective")
    expected = np.zeros_like(actual)
    expected[destinations, np.arange(dimension)] = 1.0
    difference = np.abs(actual - expected)
    error = float(difference.max())
    inverse_error = float(np.max(np.abs(actual.conj().T - expected.T)))
    control_off = np.arange(0, dimension, 2)
    padding = [column for column in range(dimension)
               if ((column >> 1) & ((1 << work_bits) - 1)) >= modulus]
    extra_mask = ((1 << wires) - 1) ^ ((1 << (work_bits + 1)) - 1)
    rows = np.arange(dimension)
    max_dirty_leakage = max(
        float(np.sum(np.abs(actual[(rows & extra_mask) != (column & extra_mask), column]) ** 2))
        for column in range(dimension)
    )
    assert error < TOLERANCE, (multiplier, "operator mismatch", error)
    assert inverse_error < TOLERANCE, (multiplier, "inverse mismatch", inverse_error)
    assert max_dirty_leakage < TOLERANCE ** 2, (multiplier, "dirty leakage", max_dirty_leakage)
    return {
        "multiplier": multiplier,
        "modulus": modulus,
        "work_bits": work_bits,
        "total_local_wires": wires,
        "borrowed_wires": wires - work_bits - 1,
        "complete_basis_columns": dimension,
        "operator_shape": [dimension, dimension],
        "full_complex_operator_max_error": error,
        "inverse_max_error": inverse_error,
        "control_off_max_error": float(difference[:, control_off].max()),
        "padding_max_error": float(difference[:, padding].max()) if padding else 0.0,
        "max_borrowed_wire_leakage_probability": max_dirty_leakage,
        "global_phase_alignment_applied": False,
        "all_borrowed_input_values_included": True,
        "seconds": round(time.monotonic() - started, 6),
        "status": "PASS",
    }


def unchanged_sources() -> dict:
    """Identity checks protect measurement and recovery, not substitute for gate proofs."""
    checked = {}
    for path in ("submissions/team3/tier08/solution.py", "submissions/team3/tier08/order.py",
                 "submissions/team3/tier07/qpe.py"):
        baseline = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)
        current = (ROOT / path).read_bytes()
        checked[path] = {
            "same_as_baseline": current == baseline,
            "sha256": hashlib.sha256(current).hexdigest(),
        }
        assert current == baseline, f"Protected measurement/recovery source changed: {path}"
    return checked


def order_finding_structure(solution) -> dict:
    circuit = solution.build_circuit(modulus=35)
    prefix = "tier08_controlled_modmul_power_"
    blocks = [instruction for instruction in circuit.data if instruction.operation.name.startswith(prefix)]
    exponents = [int(instruction.operation.name[len(prefix):]) for instruction in blocks]
    controls = [circuit.find_bit(instruction.qubits[0]).index for instruction in blocks]
    measurements = [
        [circuit.find_bit(instruction.qubits[0]).index, circuit.find_bit(instruction.clbits[0]).index]
        for instruction in circuit.data if instruction.operation.name == "measure"
    ]
    assert circuit.num_qubits == 18 and circuit.num_clbits == 12
    assert exponents == [1 << j for j in range(12)]
    assert controls == list(reversed(range(12)))
    assert measurements == [[j, j] for j in range(12)]
    first = circuit.data[0]
    assert first.operation.name == "x" and circuit.find_bit(first.qubits[0]).index == 12
    return {
        "qubits": circuit.num_qubits,
        "classical_bits": circuit.num_clbits,
        "controlled_power_blocks": len(blocks),
        "public_power_exponents": exponents,
        "physical_controls_in_block_order": controls,
        "measurement_mapping": measurements,
        "work_integer_one_prepared": True,
        "status": "PASS",
    }


def synthetic_fourier_state(solution) -> dict:
    """Full small final state versus independently evaluated Fourier formula.

    N=5/base=2 is a synthetic public toy example, never actual challenge data.
    The formula checks the SWAP-absorbed wiring and all complex phases jointly.
    """
    phase_bits, work_bits, modulus, base = 4, 3, 5, 2
    circuit = solution.build_circuit(modulus=modulus, base=base,
                                     phase_bits=phase_bits, work_bits=work_bits)
    circuit = circuit.remove_final_measurements(inplace=False)
    actual = Statevector.from_instruction(circuit).data
    width = 1 << phase_bits
    expected = np.zeros(1 << (phase_bits + work_bits), dtype=complex)
    for x in range(width):
        work = pow(base, x, modulus)
        for frequency in range(width):
            expected[frequency | (work << phase_bits)] += np.exp(-2j * math.pi * x * frequency / width) / width
    error = float(np.max(np.abs(actual - expected)))
    probability_error = float(np.max(np.abs(np.abs(actual) ** 2 - np.abs(expected) ** 2)))
    assert error < 1e-10, ("synthetic full Fourier state", error)
    return {
        "synthetic_public_modulus": modulus,
        "synthetic_public_base": base,
        "phase_bits": phase_bits,
        "work_bits": work_bits,
        "full_complex_state_max_error": error,
        "joint_probability_max_error": probability_error,
        "global_phase_alignment_applied": False,
        "status": "PASS",
    }


def mixed_predicate_fanout(emitter_module: str, mode: str) -> list[dict]:
    """Arbitrary target inputs, negative controls and XOR cancellation.

    The expectation is a single conditional XOR on the whole target mask,
    not a simulation of the emitter's pivot/fanout implementation.
    """
    emitter = importlib.import_module(emitter_module)
    cases = [
        ("mixed_three_targets", 0b000011, 0b000001, (2, 3, 4), 0b011100),
        ("external_control_only", 0, 0, (0, 1, 5), 0b100011),
        ("all_work_bits_participate", 0b001101, 0b000100, (1, 4, 5), 0b110010),
        ("repeated_target_cancels", 0b000011, 0b000001, (2, 3, 2), 0b001000),
    ]
    rows = []
    for label, mask, value, targets, target_mask in cases:
        ops = [(mask, value, target) for target in targets]
        for pivot in ("first", "last"):
            circuit = emitter.build_from_operations(ops, work_bits=6, mode=mode, pivot=pivot)
            dimension = 1 << circuit.num_qubits
            actual = Operator(circuit).data
            expected = np.zeros_like(actual)
            for column in range(dimension):
                control = column & 1
                work = (column >> 1) & 63
                destination_work = work ^ target_mask if control and (work & mask) == value else work
                destination = (column & ~126) | (destination_work << 1)
                expected[destination, column] = 1
            error = float(np.max(np.abs(actual - expected)))
            assert error < TOLERANCE, (label, pivot, "predicate fanout", error)
            rows.append({"case": label, "pivot": pivot, "mode": mode,
                         "complete_basis_columns": dimension,
                         "full_complex_operator_max_error": error,
                         "arbitrary_target_and_borrowed_states_included": True,
                         "global_phase_alignment_applied": False, "status": "PASS"})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", default="team3.tier08.modular")
    parser.add_argument("--output", type=Path, default=ROOT / "research/tier08_extreme/verification.json")
    parser.add_argument("--skip-structure", action="store_true",
                        help="Audit an isolated module before production integration")
    parser.add_argument("--emitter-module", default="research.tier08_extreme.emitter")
    parser.add_argument("--emitter-mode", default="dirty")
    parser.add_argument("--pivot", default="first", choices=("first", "last"))
    parser.add_argument("--allocation", default="work_first", choices=("work_first", "external_first"))
    parser.add_argument("--skip-emitter", action="store_true")
    parser.add_argument("--operations", type=Path,
                        help="Optional JSON mapping public multiplier to operation triples; no production edit needed")
    args = parser.parse_args()
    module = importlib.import_module(args.module)
    source = Path(module.__file__)
    builder = module.build_controlled_multiplier
    selected = None
    if args.operations:
        selected = json.loads(args.operations.read_text())
        emitter = importlib.import_module(args.emitter_module)
        original_builder = builder
        def builder(multiplier, modulus, work_bits=6):
            if modulus == 35 and work_bits == 6:
                return emitter.build_from_operations(selected[str(multiplier % modulus)], work_bits=work_bits,
                                                       mode=args.emitter_mode, pivot=args.pivot,
                                                       allocation=args.allocation)
            return original_builder(multiplier, modulus, work_bits)
    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": BASELINE,
        "module": args.module,
        "module_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "thread_environment": {key: os.environ.get(key) for key in
                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        "tolerance": TOLERANCE,
        "no_aer_or_secret_recovery_executed": True,
        "prior_audit_reference": "3dac27e:research/tier08_osc/audit.py",
        "blocks": [],
    }
    if not args.skip_emitter or args.operations:
        emitter_source = Path(importlib.import_module(args.emitter_module).__file__)
        report["emitter_sha256"] = hashlib.sha256(emitter_source.read_bytes()).hexdigest()
    if args.operations:
        report["operations_sha256"] = hashlib.sha256(args.operations.read_bytes()).hexdigest()
        report["selected_emission"] = {"mode": args.emitter_mode, "pivot": args.pivot,
                                       "allocation": args.allocation}
    started = time.monotonic()
    for multiplier in PUBLIC_MULTIPLIERS:
        row = operator_check(builder(multiplier, 35, 6), multiplier, 35, 6)
        report["blocks"].append(row)
        print(json.dumps(row), flush=True)
    if not args.skip_emitter:
        report["mixed_predicate_fanout"] = mixed_predicate_fanout(args.emitter_module, args.emitter_mode)
    if not args.skip_structure:
        report["protected_source_identity"] = unchanged_sources()
        solution = importlib.import_module("team3.tier08.solution")
        if args.operations:
            # Only this private verification process is redirected; source stays unchanged.
            solution.build_controlled_multiplier = builder
        report["full_circuit_structure"] = order_finding_structure(solution)
        report["synthetic_fourier_state"] = synthetic_fourier_state(solution)
    report["seconds"] = round(time.monotonic() - started, 6)
    report["status"] = "PASS"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "seconds": report["seconds"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
