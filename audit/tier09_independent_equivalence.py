"""Independent exhaustive native-gate basis audit; run in Tier 9 candidate tree."""
import itertools
import numpy as np
from qiskit.quantum_info import Operator
from submissions.team3.tier09.shared_controls import build_controlled_multiplier
from submissions.team3.tier09.solution import build_circuit

multipliers = sorted({pow(2, 1 << j, 77) for j in range(14)})
cases = 0
for mult in multipliers:
    circuit = build_controlled_multiplier(mult, 77, 7)
    for control, work in itertools.product(range(2), range(128)):
        value = control | (work << 1)
        for instruction in circuit.data:
            op = instruction.operation
            bits = [circuit.find_bit(q).index for q in instruction.qubits]
            assert op.name in ('cx', 'ccx', 'mcx', 'mcx_vchain', 'mcx_recursive') or op.name.startswith('mcx')
            if all(value & (1 << bit) for bit in bits[:-1]):
                value ^= 1 << bits[-1]
        expected = (mult * work % 77 if work < 77 and control else work)
        assert value == control | (expected << 1), (mult, control, work)
        cases += 1
# A separate dense-complex comparison checks phases for both control branches and padding.
max_error = 0.0
for mult, modulus, width in [(2, 5, 3), (3, 7, 3), (2, 9, 4)]:
    matrix = Operator(build_controlled_multiplier(mult, modulus, width)).data
    expected = np.zeros_like(matrix)
    for x in range(1 << (width + 1)):
        control, work = x & 1, x >> 1
        y = (mult * work % modulus if control and work < modulus else work)
        expected[control | (y << 1), x] = 1
    max_error = max(max_error, float(np.max(np.abs(matrix - expected))))
    assert max_error < 1e-10
c = build_circuit(modulus=77)
assert (c.num_qubits, c.num_clbits) == (22, 14)
assert [c.find_bit(i.qubits[0]).index for i in c.data if i.operation.name == 'x'] == [14]
assert [(c.find_bit(i.qubits[0]).index, c.find_bit(i.clbits[0]).index) for i in c.data if i.operation.name == 'measure'] == [(i, i) for i in range(14)]
assert not any(c.find_bit(q).index == 21 for i in c.data for q in i.qubits)
print(f'PASS multipliers={len(multipliers)} real_basis_cases={cases} small_complex_operators=3 max_error={max_error:.3g} mapping=identity clean_wire_idle=yes')
