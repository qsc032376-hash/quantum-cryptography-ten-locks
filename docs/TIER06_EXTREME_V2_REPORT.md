# Tier 6 V2 research result

**INCONCLUSIVE for Tier 6.** The completed experiment measures two full Grover iterations on a public synthetic predicate. No official Tier 6 candidate was produced. The frozen v6 Checker result is historical evidence only: FULL, 3,000 CX, depth 5,715, 8,752 gates, 22 active wires. The later 5,691 / 8,680 figures were supplied in the brief and were not used as a comparison denominator.

## Coherent iteration experiment

We compared two exact realizations of the synthetic function f(x) = x0 AND (x1 XOR x3). One computes the parity into zero scratch, applies CZ and reverses both CXs. The second uses two CZs, since the product distributes over XOR in GF(2). Both apply the same sign on every data basis state. The scratch returns to zero before diffusion, so the same wire can serve as clean workspace for the reflection. This proof extends to superpositions by linearity. It applies to the synthetic predicate only.

The reflection is D = 2|s><s| - I. Two rounds implement (D diag((-1)^f)) squared. Each implementation uses two predicate calls and fixed data-to-classical bit numbering. Tests on five data wires compare all clean-input columns of the two-round complex operator, including output amplitudes in nonzero workspace sectors, with the analytic matrix. The largest absolute discrepancy was below 1.5e-14.

The 14-data-wire circuit allocates eight more wires in all four configurations. The entire prepared, measured two-round circuit was compiled as one unit, first at optimization level 2 and then at level 1 using rz/sx/x/cx and seed 12345. Table entries include measurement instructions in the circuit size. These are same-environment synthetic metrics.

| Reflection | Predicate | CX | Depth | Size | Active wires |
|---|---|---:|---:|---:|---:|
| M15 | Scratch |146|364|551|20|
| M15 | Direct |140|345|525|20|
| KG24 | Scratch |154|234|577|16|
| KG24 | Direct |148|218|557|16|

The two direct implementations form the Pareto frontier. Holding the scratch predicate fixed, KG24 costs eight more CX and 26 more instructions while cutting depth by 130. The equal isolated CX counts in V1 did not predict this outcome. With the direct predicate, M15 gives the lowest CX and KG24 the lowest depth.

## Fresh-process paired simulations

Five matched seeds (6600 through 6604), 2,048 shots per circuit, two Aer threads, statevector method, truncation disabled, fresh process for each sample, alternating execution order. The actual seed was checked in each Aer experiment result. The uniform initial marked fraction is 1/4, hence the two-round expected fraction is sin²(5π/6) = 1/4. Each sampled fraction was within five binomial standard deviations. This checks only an aggregate probability; the complex operator comparison above is a separate test.

| Reflection / predicate | Passed | Median compilation (s) | Median Aer run (s) | Median peak working set (MiB) |
|---|---:|---:|---:|---:|
| M15 / scratch |5/5|0.0243|0.1637|109.05|
| M15 / direct |5/5|0.0273|0.1379|108.88|
| KG24 / direct |5/5|0.0280|0.0561|94.05|

The Aer timer includes result delivery. Working set covers the entire worker. Five pairs are a small sample; these are neither solve-time measurements nor hardware performance estimates. Reproduce from the root of this branch on Windows with the pinned Python environment and psutil:

~~~text
python -m research.tier06_extreme_v2.study
~~~

[Per-seed data and per-circuit results](../research/tier06_extreme_v2/results.json). The search evaluated four circuits and sampled the reference and both frontier points. The previous isolated reflection experiment remains available on the parent commit.

## Scope and decision

No ciphertext-specific oracle synthesis, calibration change, automated key recovery, full-tier Checker, full solve or paired decryption tests were performed. No candidate official metrics, SHA verification, solve runtime or peak solve memory are available. None of the synthetic circuit counts establishes a Tier 6 milestone. The tier's maximum Simplicity pool is 1.5 points. As a sensitivity example, if only actual tier depth fell 10% and the new depth were field-best, the depth component could gain at most 1.5 × 0.30 × 0.10 = 0.045 points. No actual competition gain can be assigned.
