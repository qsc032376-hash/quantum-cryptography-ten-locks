# Tier 10 quantum discrete-log validation

Status: **PASS for real quantum exponent recovery and circuit scoring**.
Complete `solve()` / plaintext-hash validation is **pending classical-module
integration**. No exponent, raw counts, witness pair, shared secret, or plaintext
is stored in this report or its JSON companion.

## Scope and references

Only `submissions/team3/tier10/` is added. Tier 1–9, official files, other
branches, and shared classical modules are unchanged. No branch was merged.

- Official `tier10/README.md`: no supplied oracle/helper; public modular
  multiplication as a reversible permutation is explicitly allowed. Exponents
  must be recovered using a quantum circuit, with Aer inside `solve()` for full
  credit. This quantum-only validation does not claim complete challenge credit.
- Public instance: `p=83`, `g=3`, generator order `41`, `A=11`, `B=49`.
  These are public group elements, not recovered exponents.
- Sicheng's `docs/TIER10_THEORY.md` was read at commit
  `758aab5e33dd0ecae07e8d986f8f8d083739bf4a`, blob
  `06de7834213cdaaf1fddefd646362d129ea5f482`.
- Youyang's `submissions/team3/dh_classical.py` was read at commit
  `dc47b15bdfdd5411d6cc5524fa1641f4f8116816`, blob
  `83ab52a092ba40a2f7ac25bc1aa4914906f5d2bf`.
  Neither reference file was copied or merged into this branch.
- Existing, unchanged implementations reused:
  `tier09.modular.build_controlled_multiplier`,
  `tier07.qpe.build_inverse_qft`, and
  `tier08.order._prime_divisors_of_order` (only to verify the **public** generator
  order, not to search for an exponent).

## Circuit and reversible construction

There are 19 qubits and 12 classical bits: X on qubits 0–5, Z on 6–11,
and a little-endian 7-qubit work register on 12–18. The work register starts
in `|1>`; all 12 counting qubits receive H gates. For `j=0,...,5`, X_j
controls multiplication by `g^(2^j) mod p` and Z_j controls multiplication
by `A^(2^j) mod p`. Thus the work state becomes `|g^x A^z mod p>`.

The reused public permutation compiler maps work values `y<p` to `m*y mod p`
and fixes padding values `y>=p`. Invertibility of the public multiplier makes
this a permutation of the whole 7-qubit domain. The compiler reduces its
public truth table with positive-control reversible X gates, reverses that
reduction to implement the permutation, and adds the outer control. This
constructs the known group operation; it never tabulates discrete logarithms.
Repeated public multipliers share cached constructions. There is no dense
`UnitaryGate`, hidden oracle inspection, or extra/borrowed ancilla in this
construction. Inverse-operation tests check restoration of arbitrary work
values and preservation of the counting registers.

Both counting registers receive complete 6-qubit inverse QFTs, including
three SWAPs each. Each `X_j -> c_j` and `Z_j -> c_(6+j)`. Actual executed
wire-to-classical mappings were recorded and checked. Counts have exactly
12 bits: **left six Z, right six X**, including leading zeroes. Neither half
is reversed after the full inverse QFT.

There are 12 controlled-power blocks per shot (six powers for each public
base). Their exponent-weighted accounting is `2*(1+2+4+8+16+32)=126`
equivalent base multiplications per shot; this is distinct from counting the
compiled gate instructions. No official opaque oracle is supplied in Tier 10.

## Measurement interpretation and bounded recovery

For raw readings `y_x,y_z` in `0..63`, use exact half-up rounding

```
R(y) = ((2*41*y + 64) // 128) % 41
u = R(y_x); v = R(y_z)
(k1,k2) = ((-v) % 41, u)
```

This gives the candidate congruence `u*a = v (mod 41)`, or equivalently
`k1+k2*a = 0 (mod 41)`. For example, the public rounding boundary `y=32`
maps to 21, not Python's banker-rounded 20. A raw 6-bit value is never
interpreted directly as a frequency modulo 41.

Since 64 is not divisible by 41, rounded samples can be outliers. Each
equation is reduced independently using a gcd. Uninformative equations,
inconsistent equations, and noncoprime partial congruences are counted
separately. Partial congruences are never expanded into possible exponents.
Only full-modulus equations contribute candidate weights. Candidates are
ranked by their observed shot support, and at most eight new candidates per
batch are checked against the public relation `pow(g,a,p)==A`. Previously
tested candidates are not retested. No exponent range is enumerated and
incompatible samples are not merged.

The budget is one 128-shot batch and at most one supplemental batch: at most
256 shots and 16 distinct public checks. An Aer error stops execution;
insufficient evidence is reported instead of replaced with a classical answer.
The validator adds separate 120-second recovery and scoring time limits.

`recover_exponent()` returns the measured exponent residue modulo 41, **not**
the DH shared-secret key. `recover_exponent_with_diagnostics()` also returns
the actual 12-bit counts and one observed witness, in fields excluded from
the object's representation. These private fields remain in memory for
integration; only aggregate diagnostics are written to the repository.

## Actual run on 2026-11-07

Python 3.12.14, Qiskit 2.6.1, Qiskit Aer 0.18.2; CPU statevector backend,
two threads, `max_memory_mb=512`. Seeds: transpiler 12345, simulator 1010.
Tested base commit: `9cfc92ae139e2d9f955b98e56b50d2686a789357`.
Exact aggregate results are in `quantum_validation.json`.

| Observation | Actual result |
| --- | ---: |
| Real Tier 10 Aer calls / shots | 1 / 128 |
| Supplemental batches | 0 |
| Distinct measured 12-bit outcomes | 78 |
| Full-modulus informative shots | 120 |
| Uninformative / inconsistent / partial shots | 8 / 0 / 0 |
| Distinct measurement-derived candidates | 19 |
| Candidates checked against the public relation | 1 |
| Informative shots supporting the verified candidate | 95 |
| Support among all / informative shots | 74.21875% / 79.16667% |
| Exponent recovered from actual measurements | PASS |
| Public relation and observed full-modulus witness | PASS |
| Shot-weighted controlled-power blocks | 1,536 |
| Shot-weighted equivalent base multiplications | 16,128 |
| Circuit build and native transpilation | 0.430791 s |
| Aer run and counts collection | 2.283360 s |
| Complete quantum recovery | 2.714644 s |
| Official-basis scoring transpilation | 5.050056 s |
| Process peak RSS before scoring | 141.719 MiB |
| Process peak RSS including scoring | 336.750 MiB |

The support percentages are descriptive statistics from this same measured
batch, not an independent estimate of algorithm success probability. The
eight uninformative shots are not counted as successful evidence; 25
informative shots support other candidates. One successful session does not
establish a 100% success probability. No further actual-instance sampling
was performed after success. RSS is Linux process maximum resident memory,
not a GPU measurement or a whole-machine memory figure.

## Single executed circuit and scoring

Aer ran a native-basis circuit containing 4,014 MCX, 220 CCX, 30 controlled
phase gates, 24 H, six SWAP, one X, and 12 measurements. Native multi-qubit
gates make the native two-qubit count misleading as a simplicity score.
The **exact native circuit passed to `AerSimulator.run`** was subsequently
transpiled to the official `rz,sx,x,cx` basis, optimization level 1,
seed 12345, no coupling map or fixed layout, for scoring. This did not
execute an additional quantum simulation.

| Metric | Native executed circuit | Official-basis scoring circuit |
| --- | ---: | ---: |
| Qubits / active qubits | 19 / 19 | 19 / 19 |
| Classical bits | 12 | 12 |
| Gates, excluding measurements | 4,295 | 317,957 |
| Gate depth, excluding measurements | 4,247 | 287,674 |
| Two-qubit gates | 36 | 107,168 |
| Operations including measurements | 4,307 | 317,969 |
| Depth including measurements | 4,248 | 287,675 |

Gate depth excludes measurement/reset/barrier instructions, matching the
scoring metric. The JSON also retains the measurement-inclusive values so
the two definitions cannot be confused. The high basis-expanded cost remains
an optimization opportunity; this report claims correctness and a measured
cost, not an optimal circuit.

## Tests and reproducibility

All **43** Tier 10 tests have passing final results:

- `test_readout.py`: 17 synthetic tests (0.001 s), covering fixed width and
  leading zeroes, bit order, sign convention, half-up rounding, noncoprime
  coefficients, inconsistent/uninformative samples, and aggregation without
  whole-batch congruence merging.
- `test_solution.py`: 22 mocked/artificial-group tests (0.044 s), covering
  measured-candidate ranking, rejection of wrong candidates, honest support
  accounting, bounded supplementation and deduplication, failure propagation,
  private representations, and all four classical API calls using only a
  verified full-modulus witness.
- `test_circuit.py`: four circuit tests, covering exhaustive small-group
  basis mapping, inverse/restoration, padding states, controlled relative
  phase, two IQFTs with SWAPs, work initialization, and synthetic Aer sampling.
  One synthetic Aer batch tested three artificial instances with 128 shots
  each. The `p=83` synthetic case uses a deliberately chosen known exponent
  and a public A different from the challenge's A; it is not actual-instance
  recovery evidence.

An initial arbitrary-input matrix test failed because Qiskit's default
`qubits_initially_zero=True` allows unused wires to be treated as clean.
The bare mapping subcircuit test was corrected to set
`qubits_initially_zero=False` and to respect transpiler layout via
`Operator.from_circuit`. The failed matrix check was then rerun and passed
(0.759 s), with maximum matrix error about `1.67e-13`. A prepared small QPE
circuit also agrees under the normal zero-initialized contract. No algorithm
or tolerance was changed to hide a mismatch; previously passing synthetic
Aer runs were not repeated. The 43 passing results therefore come from
the original test runs plus this targeted correction, not a claimed single
all-green initial run.

From the repository root, these commands reproduce the tests and the real
bounded run respectively (the last command performs new actual measurements
and overwrites the aggregate JSON):

```
python -B -m unittest submissions.team3.tier10.test_readout submissions.team3.tier10.test_solution submissions.team3.tier10.test_circuit
python -B -m submissions.team3.tier10.validate_quantum
```

## Classical integration and remaining limits

This branch does not contain Youyang's shared `dh_classical.py`. `solve()`
therefore raises a clear `NotImplementedError` until integration; full
decryption and the official plaintext hash have **not** been validated.
The quantum entry point is independently runnable.

The reviewed classical version unconditionally merges incoming equations
and may enumerate residual cosets when evidence is incomplete. The prepared
adapter avoids both paths: it supplies only one actual, verified,
full-modulus witness. It calls the shared `measurement_from_counts()` and
`equation_from_counts()` on that counts string, checks their convention,
then calls `recover_exponent([pair], parameters)` and
`decrypt_tier10([pair], parameters, ciphertext_hex)`. Final plaintext-hash
verification remains mandatory. DH shared-secret derivation and keystream
decryption are not reimplemented here. Junrui can integrate the stable
classical module and perform the final full `solve()` validation.

Finite sampling, off-grid Fourier rounding, the intentionally bounded
candidate budget, and the large basis-expanded circuit remain limitations.
This was an ideal CPU Aer run, not noisy-hardware validation. The current
actual run needed no retry and did not encounter a resource limit.
