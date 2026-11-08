"""Secret-free, phase-sensitive checks for the two advanced circuit changes."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from qiskit.quantum_info import Statevector
from qiskit.synthesis import synth_mcx_n_dirty_m15

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "submissions" / "team3")]

from submissions.team3.tier05 import oracle as tier05_oracle  # noqa: E402
from submissions.team3.tier08 import modular as tier08_modular  # noqa: E402
from submissions.team3.tier08 import solution as tier08_solution  # noqa: E402


def baseline_module(source, module_name, folder):
    path = Path(folder) / (module_name.rsplit(".", 1)[-1] + ".py")
    path.write_bytes(subprocess.check_output(
        ["git", "show", f"41c7c6775b8fc499c2acdd878b4829bd17e1210d:{source}"],
        cwd=ROOT,
    ))
    spec = spec_from_file_location(module_name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdvancedEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = TemporaryDirectory(prefix="tier58-baseline-")
        cls.addClassCleanup(temporary.cleanup)
        cls.old_oracle = baseline_module(
            "submissions/team3/tier05/oracle.py",
            "submissions.team3.tier05.old_oracle", temporary.name,
        )
        cls.old_tier08 = baseline_module(
            "submissions/team3/tier08/solution.py",
            "submissions.team3.tier08.old_solution", temporary.name,
        )

    def test_m15_four_controls_all_basis_phases_and_dirty_restoration(self):
        gate = synth_mcx_n_dirty_m15(4)
        self.assertEqual(gate.num_qubits, 6)
        for basis in range(1 << 6):
            control_all = (basis & 0x0f) == 0x0f
            expected = basis ^ (0x10 if control_all else 0)
            actual = Statevector.from_int(basis, 1 << 6).evolve(gate).data
            target = np.zeros(1 << 6, dtype=complex)
            target[expected] = 1
            np.testing.assert_allclose(actual, target, atol=1e-12)

    def test_m15_eight_controls_selected_dirty_states(self):
        gate, wires = tier05_oracle._dirty_comparison_gate()
        self.assertEqual(len(wires), 12)
        self.assertEqual(wires[-3:], (0, 1, 2))
        for controls in (0, 1, 0x55, 0x7f, 0xfe, 0xff):
            for target in (0, 1):
                for dirty in (0, 1, 5, 7):
                    basis = controls | (target << 8) | (dirty << 9)
                    expected = basis ^ (1 << 8 if controls == 0xff else 0)
                    actual = Statevector.from_int(basis, 1 << 12).evolve(gate).data
                    self.assertAlmostEqual(actual[expected], 1, delta=1e-11)
                    self.assertAlmostEqual(np.linalg.norm(actual), 1, delta=1e-11)

    def test_tier05_oracle_selected_keys_and_superposition(self):
        ciphertext = bytes((0x12, 0x34))
        old = self.old_oracle.build_phase_oracle(ciphertext)
        new = tier05_oracle.build_phase_oracle(ciphertext)
        for state in (
            Statevector.from_int(0, 1 << 19),
            Statevector.from_int(1023, 1 << 19),
            Statevector.from_int(0x155 | (0xA5 << 10) | (1 << 18), 1 << 19),
            (Statevector.from_int(0, 1 << 19)
             + Statevector.from_int(1023, 1 << 19)) / np.sqrt(2),
        ):
            np.testing.assert_allclose(state.evolve(old).data, state.evolve(new).data,
                                       atol=1e-10)

    def test_small_modular_block_all_basis_states(self):
        circuit = tier08_modular.build_controlled_multiplier(2, 15, 4)
        table = tier08_modular.permutation_table(2, 15, 4)
        self.assertEqual(circuit.num_qubits, 6)
        for basis in range(1 << 6):
            control, work = basis & 1, (basis >> 1) & 15
            mapped = table[work] if control else work
            expected = (basis & ~(15 << 1)) | (mapped << 1)
            actual = Statevector.from_int(basis, 1 << 6).evolve(circuit).data
            target = np.zeros(1 << 6, dtype=complex)
            target[expected] = 1
            np.testing.assert_allclose(actual, target, atol=1e-11)

    def test_tier08_complete_small_qft_state_all_work_basis(self):
        kwargs = dict(modulus=15, base=2, phase_bits=4, work_bits=4)
        old = self.old_tier08.build_circuit(**kwargs).remove_final_measurements(inplace=False)
        new = tier08_solution.build_circuit(**kwargs).remove_final_measurements(inplace=False)
        for work in range(1 << 4):
            initial = Statevector.from_int(work << 4, 1 << 8)
            np.testing.assert_allclose(initial.evolve(old).data, initial.evolve(new).data,
                                       atol=1e-10)
        superposed = (Statevector.from_int(0, 1 << 8)
                      + 1j * Statevector.from_int(15 << 4, 1 << 8)) / np.sqrt(2)
        np.testing.assert_allclose(superposed.evolve(old).data,
                                   superposed.evolve(new).data, atol=1e-10)


if __name__ == "__main__":
    unittest.main()
