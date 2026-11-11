# Team 3 Simplicity sensitivity and optimization strategy

Research date: November 11, 2026 (America/New_York). Deadline: November 13, 2026, 12:00 PM EST.

**Recommendation:** retain the verified final package. If further research is pursued, prioritize independent validation of Tier 10 v3, not immediate integration. All scores below are hypothetical; no opponent submissions were accessed.

## Formula and provenance

For tier i, Pᵢ = 0.375 × tier points. The pools sum to 15. For each metric, the global best includes Team 3 when eligible: b = min(c, x), where c is an independently specified rival minimum. The ratio is b/x when b > 0; when b = 0 it is 1 if x = 0, otherwise 1/(1+x). Tier score is Pᵢ Σₘ wₘ ratioₘ. Weights are 0.40 two-qubit gates, 0.30 depth, 0.20 total gates and 0.10 active qubits.

Sources: [official rubric](../SCORING.md), [ranking implementation](../tools/rank.py), [RC JSON](v6-rc/report.json), and [RC table](v6-rc/report.md). Eligibility requires full tier credit and valid metrics; rank.py uses full-credit fraction and a present metrics mapping. The calculator assumes eligible validated input, not that hypothetical circuits have passed eligibility checks. It rejects a supplied global best greater than our value; the separate competitor interface allows larger rival values and recomputes the minimum.

Pinned runtime: `c4455782ea9388d5897fc27270f42dd3786ed35d`. Independent runtime audit: `58853c2`, docs/v6-rc/INDEPENDENT_AUDIT.md. Final package: `ca7290c7f6b35e37e4ef94f3d5f79110309f594f`. This research branch starts at the runtime RC and changes no submission file or archive. No quantum simulation was rerun.

Official Tier 4 examples reproduce exactly: Alpha 1.06875 (display 1.069), Beta 0.975, Gamma 0.675. Tests compare the official ratio implementation on 1,326 integer pairs, including zero. Aggregate gates alone cannot determine this score.

## Verified baseline

| Tier | Pool | 2Q | Depth | Gates | Qubits |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.375 | 151 | 44 | 298 | 25 |
| 2 | 0.750 | 0 | 3 | 3 | 1 |
| 3 | 0.750 | 7808 | 8771 | 19497 | 7 |
| 4 | 1.125 | 183 | 195 | 455 | 20 |
| 5 | 1.500 | 14552 | 28132 | 40938 | 19 |
| 6 | 1.500 | 3000 | 5715 | 8752 | 22 |
| 7 | 1.875 | 209 | 266 | 727 | 15 |
| 8 | 2.250 | 33904 | 96055 | 102561 | 18 |
| 9 | 2.250 | 55999 | 120242 | 168116 | 22 |
| 10 | 2.625 | 46910 | 109763 | 132023 | 19 |

All ten tiers are FULL, hash-matched and flag-free in the stored audited evidence. Totals are 162,716 two-qubit gates, 369,186 sum of per-tier depths, and 473,370 gates. The depth sum is not a combined-circuit depth. No discrepancy with the requested baseline was found.

## Hypothetical competitor scenarios

A ties our baseline in every metric. B/C/D set positive gate and depth rival values to ceil(0.90x), ceil(0.75x), ceil(0.50x), respectively. Zero stays zero. These are approximate integer reductions, not exact uniform percentage scores. Depth and total gates remain at least one. Width uses a deliberately conservative architecture constraint: hold the documented register counts fixed except Tier 9, where the historical 21-qubit implementation provides a narrower reference. Thus percentage reductions in width are clipped at that evidence-supported floor. These are modeling constraints, not universal physical lower bounds; review thresholds are not physical bounds. No simultaneous realization of the hypothetical gate/width tuple is claimed.

E uses metric-specific percentage gaps (2Q/depth/gates): T1 10/20/10; T2 0/0/0; T3 40/35/30; T4 20/10/15; T5 25/20/25; T6 25/30/20; T7 5/0/5; T8 40/35/30; T9 50/40/45; T10 40/50/35. Width is unchanged except T9=21. Separate abstract specialists lead each metric, so no single competitor is assumed to attain every minimum. T2 is exactly tied in E and T7 close. Small-integer rounding keeps B/C T2 unchanged; D allows the hypothetical three-gate/depth circuit to become two, without asserting such an implementation exists.

| Tier | A | B | C | D | E | E gap |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.375000 | 0.342573 | 0.291496 | 0.206747 | 0.332346 | 0.042654 |
| 2 | 0.750000 | 0.750000 | 0.750000 | 0.625000 | 0.750000 | 0.000000 |
| 3 | 0.750000 | 0.682539 | 0.581271 | 0.412517 | 0.506280 | 0.243720 |
| 4 | 1.125000 | 1.025600 | 0.875388 | 0.621092 | 0.969964 | 0.155036 |
| 5 | 1.500000 | 1.365017 | 1.162504 | 0.825000 | 1.185010 | 0.314990 |
| 6 | 1.500000 | 1.365046 | 1.162559 | 0.825039 | 1.155053 | 0.344947 |
| 7 | 1.875000 | 1.711110 | 1.455466 | 1.033302 | 1.820545 | 0.054455 |
| 8 | 2.250000 | 2.047515 | 1.743756 | 1.237506 | 1.518769 | 0.731231 |
| 9 | 2.250000 | 2.037290 | 1.733538 | 1.227281 | 1.317286 | 0.932714 |
| 10 | 2.625000 | 2.388753 | 2.034395 | 1.443756 | 1.627504 | 0.997496 |
| **Total / 15** | 15.000000 | 13.715443 | 11.790373 | 8.457239 | 11.182758 | 3.817242 |

All rival minima and every metric contribution/loss are exported by the default JSON command. No scenario is assigned a probability. Gaps from full in any scenario equal the pool minus the corresponding table entry.

## Sensitivity and bounds

For positive fixed rival minimum c and x > c: Sₘ = Pᵢwₘc/x, dSₘ/dx = −Pᵢwₘc/x². A small fractional reduction ε has gain approximately Pᵢwₘ(c/x)ε; this compares fractional engineering progress, whereas the derivative compares removal of one unit. At x=c the function has a kink; below c it is flat at full credit. At c=0 use the official 1/(1+x) rule (derivative −Pᵢwₘ/(1+x)² for x>0), not c/x. At zero, ratio is 1. Integer rounding and saturation require finite differences, not derivative extrapolation.

For a positive reduction x→y, the greatest possible gain over fixed integer rival minima is Pᵢwₘ(1−y/x), attained at c=y. For c<y gain grows with c; for y≤c<x it decreases with c; for c≥x it is zero. Independent metric leaders make the sum of these bounds attainable in the abstract metric model, not evidence of a realizable opponent. No benefit remains when we already lead all affected metrics.

Each following cell is the isolated point gain for 1% / 5% / 10% / 20% / 30% requested reduction, using y=ceil((1−ε)x), clipped to the stated bounds. Other metrics and rival minima stay fixed. These are score sensitivities, not invented candidate measurements. Gate count, depth and width are coupled physically, so isolated improvements need circuit validation. A has zero gain for every row and is omitted here; all five scenarios and all four metrics are in JSON.

| Tier | Metric | B gains | C gains | D gains | E gains |
|---:|---|---|---|---|---|
| 1 | two_qubit_gates | 0.00090 / 0.00657 / 0.01490 / 0.01490 / 0.01490 | 0.00075 / 0.00550 / 0.01249 / 0.02808 / 0.03675 | 0.00050 / 0.00367 / 0.00833 / 0.01872 / 0.03205 | 0.00090 / 0.00657 / 0.01490 / 0.01490 / 0.01490 |
| 1 | depth | 0.00000 / 0.00487 / 0.01023 / 0.01023 / 0.01023 | 0.00000 / 0.00402 / 0.00844 / 0.01875 / 0.02813 | 0.00000 / 0.00268 / 0.00562 / 0.01250 / 0.02359 | 0.00000 / 0.00438 / 0.00920 / 0.02045 / 0.02045 |
| 1 | total_gates | 0.00046 / 0.00334 / 0.00730 / 0.00730 / 0.00730 | 0.00038 / 0.00278 / 0.00608 / 0.01392 / 0.01862 | 0.00025 / 0.00185 / 0.00404 / 0.00926 / 0.01597 | 0.00046 / 0.00334 / 0.00730 / 0.00730 / 0.00730 |
| 2 | two_qubit_gates | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 |
| 2 | depth | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 |
| 2 | total_gates | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 |
| 3 | two_qubit_gates | 0.00272 / 0.01420 / 0.02997 / 0.02997 / 0.02997 | 0.00227 / 0.01183 / 0.02497 / 0.05622 / 0.07500 | 0.00151 / 0.00789 / 0.01665 / 0.03748 / 0.06427 | 0.00182 / 0.00946 / 0.01998 / 0.04498 / 0.07713 |
| 3 | depth | 0.00203 / 0.01064 / 0.02250 / 0.02250 / 0.02250 | 0.00169 / 0.00887 / 0.01875 / 0.04219 / 0.05623 | 0.00113 / 0.00591 / 0.01250 / 0.02812 / 0.04821 | 0.00147 / 0.00769 / 0.01625 / 0.03656 / 0.06268 |
| 3 | total_gates | 0.00136 / 0.00710 / 0.01499 / 0.01499 / 0.01499 | 0.00113 / 0.00592 / 0.01250 / 0.02812 / 0.03750 | 0.00075 / 0.00394 / 0.00833 / 0.01875 / 0.03214 | 0.00106 / 0.00552 / 0.01166 / 0.02625 / 0.04500 |
| 4 | two_qubit_gates | 0.00223 / 0.02099 / 0.04426 / 0.04426 / 0.04426 | 0.00186 / 0.01755 / 0.03702 / 0.08310 / 0.11066 | 0.00124 / 0.01170 / 0.02468 / 0.05540 / 0.09470 | 0.00199 / 0.01870 / 0.03943 / 0.08852 / 0.08852 |
| 4 | depth | 0.00157 / 0.01474 / 0.03288 / 0.03288 / 0.03288 | 0.00131 / 0.01231 / 0.02747 / 0.06361 / 0.08308 | 0.00087 / 0.00821 / 0.01831 / 0.04240 / 0.07181 | 0.00157 / 0.01474 / 0.03288 / 0.03288 / 0.03288 |
| 4 | total_gates | 0.00180 / 0.01030 / 0.02225 / 0.02225 / 0.02225 | 0.00150 / 0.00859 / 0.01856 / 0.04228 / 0.05588 | 0.00100 / 0.00573 / 0.01237 / 0.02819 / 0.04807 | 0.00170 / 0.00972 / 0.02100 / 0.03363 / 0.03363 |
| 5 | two_qubit_gates | 0.00543 / 0.02840 / 0.05999 / 0.05999 / 0.05999 | 0.00453 / 0.02366 / 0.04999 / 0.11248 / 0.15000 | 0.00302 / 0.01578 / 0.03333 / 0.07499 / 0.12855 | 0.00453 / 0.02366 / 0.04999 / 0.11248 / 0.15000 |
| 5 | depth | 0.00409 / 0.02131 / 0.04500 / 0.04500 / 0.04500 | 0.00341 / 0.01776 / 0.03750 / 0.08437 / 0.11250 | 0.00227 / 0.01184 / 0.02500 / 0.05625 / 0.09642 | 0.00363 / 0.01894 / 0.04000 / 0.08999 / 0.08999 |
| 5 | total_gates | 0.00272 / 0.01420 / 0.02999 / 0.02999 / 0.02999 | 0.00227 / 0.01184 / 0.02499 / 0.05625 / 0.07500 | 0.00151 / 0.00789 / 0.01666 / 0.03750 / 0.06428 | 0.00227 / 0.01184 / 0.02499 / 0.05625 / 0.07500 |
| 6 | two_qubit_gates | 0.00545 / 0.02842 / 0.06000 / 0.06000 / 0.06000 | 0.00455 / 0.02368 / 0.05000 / 0.11250 / 0.15000 | 0.00303 / 0.01579 / 0.03333 / 0.07500 / 0.12857 | 0.00455 / 0.02368 / 0.05000 / 0.11250 / 0.15000 |
| 6 | depth | 0.00408 / 0.02126 / 0.04496 / 0.04496 / 0.04496 | 0.00340 / 0.01772 / 0.03747 / 0.08439 / 0.11244 | 0.00227 / 0.01181 / 0.02498 / 0.05626 / 0.09641 | 0.00317 / 0.01654 / 0.03497 / 0.07876 / 0.13496 |
| 6 | total_gates | 0.00271 / 0.01419 / 0.02999 / 0.02999 / 0.02999 | 0.00226 / 0.01183 / 0.02499 / 0.05623 / 0.07500 | 0.00151 / 0.00788 / 0.01666 / 0.03749 / 0.06426 | 0.00241 / 0.01261 / 0.02666 / 0.05999 / 0.05999 |
| 7 | two_qubit_gates | 0.00655 / 0.03408 / 0.07177 / 0.07177 / 0.07177 | 0.00544 / 0.02831 / 0.05962 / 0.13750 / 0.18660 | 0.00364 / 0.01893 / 0.03987 / 0.09196 / 0.15892 | 0.00690 / 0.03589 / 0.03589 / 0.03589 / 0.03589 |
| 7 | depth | 0.00384 / 0.02608 / 0.05498 / 0.05498 / 0.05498 | 0.00320 / 0.02173 / 0.04582 / 0.10524 / 0.13957 | 0.00213 / 0.01445 / 0.03047 / 0.06998 / 0.11882 | 0.00000 / 0.00000 / 0.00000 / 0.00000 / 0.00000 |
| 7 | total_gates | 0.00328 / 0.01760 / 0.03714 / 0.03714 / 0.03714 | 0.00274 / 0.01467 / 0.03096 / 0.07017 / 0.09336 | 0.00183 / 0.00978 / 0.02064 / 0.04678 / 0.08041 | 0.00347 / 0.01857 / 0.01857 / 0.01857 / 0.01857 |
| 8 | two_qubit_gates | 0.00818 / 0.04263 / 0.08999 / 0.08999 / 0.08999 | 0.00682 / 0.03552 / 0.07499 / 0.16873 / 0.22500 | 0.00454 / 0.02368 / 0.04999 / 0.11248 / 0.19285 | 0.00545 / 0.02842 / 0.05999 / 0.13498 / 0.23143 |
| 8 | depth | 0.00613 / 0.03197 / 0.06750 / 0.06750 / 0.06750 | 0.00511 / 0.02664 / 0.05625 / 0.12656 / 0.16874 | 0.00341 / 0.01776 / 0.03750 / 0.08438 / 0.14464 | 0.00443 / 0.02309 / 0.04875 / 0.10969 / 0.18803 |
| 8 | total_gates | 0.00409 / 0.02132 / 0.04500 / 0.04500 / 0.04500 | 0.00341 / 0.01776 / 0.03750 / 0.08437 / 0.11250 | 0.00227 / 0.01184 / 0.02500 / 0.05625 / 0.09643 | 0.00318 / 0.01658 / 0.03500 / 0.07875 / 0.13500 |
| 9 | two_qubit_gates | 0.00817 / 0.04262 / 0.08999 / 0.08999 / 0.08999 | 0.00681 / 0.03551 / 0.07499 / 0.16874 / 0.22499 | 0.00454 / 0.02368 / 0.04999 / 0.11249 / 0.19285 | 0.00454 / 0.02368 / 0.04999 / 0.11249 / 0.19285 |
| 9 | depth | 0.00613 / 0.03197 / 0.06750 / 0.06750 / 0.06750 | 0.00511 / 0.02664 / 0.05625 / 0.12656 / 0.16875 | 0.00341 / 0.01776 / 0.03750 / 0.08437 / 0.14464 | 0.00409 / 0.02132 / 0.04500 / 0.10125 / 0.17357 |
| 9 | total_gates | 0.00409 / 0.02131 / 0.04500 / 0.04500 / 0.04500 | 0.00341 / 0.01776 / 0.03750 / 0.08437 / 0.11250 | 0.00227 / 0.01184 / 0.02500 / 0.05625 / 0.09643 | 0.00250 / 0.01303 / 0.02750 / 0.06187 / 0.10607 |
| 10 | two_qubit_gates | 0.00954 / 0.04973 / 0.10500 / 0.10500 / 0.10500 | 0.00795 / 0.04144 / 0.08750 / 0.19688 / 0.26249 | 0.00530 / 0.02763 / 0.05833 / 0.13125 / 0.22500 | 0.00636 / 0.03315 / 0.07000 / 0.15750 / 0.27000 |
| 10 | depth | 0.00715 / 0.03730 / 0.07875 / 0.07875 / 0.07875 | 0.00596 / 0.03108 / 0.06562 / 0.14765 / 0.19687 | 0.00398 / 0.02072 / 0.04375 / 0.09844 / 0.16874 | 0.00398 / 0.02072 / 0.04375 / 0.09844 / 0.16874 |
| 10 | total_gates | 0.00477 / 0.02487 / 0.05250 / 0.05250 / 0.05250 | 0.00398 / 0.02072 / 0.04375 / 0.09844 / 0.13125 | 0.00265 / 0.01382 / 0.02917 / 0.06562 / 0.11250 | 0.00345 / 0.01796 / 0.03792 / 0.08531 / 0.14625 |

### Active-qubit sensitivity

No fractional qubits are used. For T1–8 and T10, none of the requested percentage reductions is supported within the preserved architecture: the calculator clips to the current width, giving zero modeled gain. This does not prove global width optimality. Tier 9 can be compared to the documented 21-qubit architecture; ceil rounding gives widths 22/21/21/21/21 at 1/5/10/20/30%. Holding v2 gates fixed while removing its synthesis wire is only a conditional tradeoff, not a tested candidate.

| Tier | Current width | Supported lower comparison | E gain at lower width | E loss adding one qubit |
|---:|---:|---:|---:|---:|
| 1 | 25 | 25 | 0.000000 | 0.001442 |
| 2 | 1 | 1 | 0.000000 | 0.037500 |
| 3 | 7 | 7 | 0.000000 | 0.009375 |
| 4 | 20 | 20 | 0.000000 | 0.005357 |
| 5 | 19 | 19 | 0.000000 | 0.007500 |
| 6 | 22 | 22 | 0.000000 | 0.006522 |
| 7 | 15 | 15 | 0.000000 | 0.011719 |
| 8 | 18 | 18 | 0.000000 | 0.011842 |
| 9 | 22 | 21 | 0.010227 | 0.009338 |
| 10 | 19 | 19 | 0.000000 | 0.013125 |

### Ranked opportunities under E

Combined sensitivity means 10% improvement in each of 2Q, depth and total gates with width held fixed. It is a planning target, not a claim that an untested circuit exists. Marginal means a 1% 2Q reduction; 10% 2Q isolates the highest-weight metric. Ordering uses combined point gain, not gate counts.

| Rank | Tier | Pool | E score | Gap | 1% 2Q gain | 10% 2Q gain | Combined 10% gain |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 2.625000 | 1.627504 | 0.997496 | 0.006362 | 0.070000 | 0.151665 |
| 2 | 8 | 2.250000 | 1.518769 | 0.731231 | 0.005454 | 0.059994 | 0.143741 |
| 3 | 9 | 2.250000 | 1.317286 | 0.932714 | 0.004537 | 0.049992 | 0.122491 |
| 4 | 5 | 1.500000 | 1.185010 | 0.314990 | 0.004529 | 0.049992 | 0.114985 |
| 5 | 6 | 1.500000 | 1.155053 | 0.344947 | 0.004545 | 0.050000 | 0.111632 |
| 6 | 4 | 1.125000 | 0.969964 | 0.155036 | 0.001986 | 0.039434 | 0.093323 |
| 7 | 7 | 1.875000 | 1.820545 | 0.054455 | 0.006900 | 0.035885 | 0.054455 |
| 8 | 3 | 0.750000 | 0.506280 | 0.243720 | 0.001816 | 0.019978 | 0.047891 |
| 9 | 1 | 0.375000 | 0.332346 | 0.042654 | 0.000901 | 0.014901 | 0.031404 |
| 10 | 2 | 0.750000 | 0.750000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

Tier 10 has the largest pool (2.625) and largest combined 10% gain in E; two-qubit gates have its largest weight. Tier 8 and Tier 9 each have 2.25 points. Tier 7 has 1.875 points but is already near the assumed best in E and quickly saturates; in C/D it deserves much more attention. Tier 3 has a severe E gap despite only 0.75 points; inspect whether a low-effort exact rewrite is available before undertaking a risky large-tier redesign. Engineering effort has not been measured, so no points-per-hour ranking is asserted. A severe gap creates headroom but also lowers local sensitivity when the rival is far ahead.

## Documented research candidates

| Tier candidate | 2Q / depth / gates / qubits | A gain | B gain | C gain | D gain | E gain | Maximum positive gain bound |
|---|---|---:|---:|---:|---:|---:|---:|
| T5 clean ancilla (rejected) | 13802 / 19480 / 38556 / 22 | -0.02045455 | 0.07056731 | 0.13039922 | 0.10504774 | 0.10789282 | 0.18677680 |
| T9 v3 | 55971 / 120223 / 168088 / 22 | 0.00000000 | 0.00056869 | 0.00047391 | 0.00031594 | 0.00033036 | 0.00063162 |
| T10 v3 | 46038 / 107877 / 129606 / 19 | 0.00000000 | 0.03910174 | 0.03258510 | 0.02172326 | 0.02518061 | 0.04266082 |

T5 upper bound ignores the unavoidable width penalty for a fixed low-width rival and is not a practical score forecast. The exact gains in the five scenarios include that penalty. The documented total-gate count is 38,556, rather than an inferred value. All ten strict OSC candidate solves exceeded 120 seconds and were circuit_only, making them ineligible for Simplicity in those runs; one unseeded FULL result at 118.116 seconds does not erase the failures. Retain accepted GF(2), 14,552 / 28,132 / 40,938 / 19.

T9 v3 (55,971 / 120,223 / 168,088 / 22) passes an isolated Checker, but only two local paired seeds were tested and both were slower than v2. Its tiny upper bound is below the competition’s 0.01 tie tolerance by itself; do not confuse this with a guaranteed tie outcome when other scores differ. Do not integrate without independent reliability verification. The accepted v2 OSC benchmark retains its original INCONCLUSIVE label even though the later integration decision selected v2.

T10 v3 (46,038 / 107,877 / 129,606 / 19) and v2 both passed isolated Checker validation. v3 has three local paired seeds rather than v2’s accepted broader evidence; its mean local solve increased 4.005→5.651 seconds. The selector is a research wrapper requiring production integration and revalidation. The mathematical upper bound is a ceiling over unknown rivals, not an expected reward.

T8 trajectory: frozen v5 42,810 / 123,320; immediately preceding baseline 42,792 / 123,300 / 130,171 / 18; accepted hybrid 33,904 / 96,055 / 102,561 / 18. Hybrid fixed-mask/cycle-anchor synthesis passed independent full controlled-block operator checks and ten OSC pairs. These savings are already in v6; no new T8 candidate or extra reduction is claimed.

## Scenario-based release decision

| Option | Score opportunity | Correctness / runtime evidence | Effort and release risk | Decision |
|---|---|---|---|---|
| Keep accepted package | No incremental gain; preserves all scenario baseline scores | Independent 10/10 FULL runtime audit | No integration required | Recommended before deadline |
| T5 clean ancilla | Conditional metric gains; width +3 | 10/10 strict OSC solve overruns | High timeout risk; loses eligibility | Reject |
| T9 v3 | Very small absolute ceiling | Isolated FULL; two local pairs; independent reliability incomplete | New integration and package audit for negligible gain | Defer |
| T10 v3 | Largest documented remaining ceiling; zero in A | Isolated FULL, scoped phase tests, three local pairs; slower | Broader independent validation, explicit selector integration, full artifact audit needed | First research target, not immediate release |
| New T8/T10 changes | Hypothetical sensitivity only | No candidate evidence | Unknown engineering/validation effort | Do not promise a deliverable before deadline |

There are fewer than two calendar days from the analysis date to the deadline. Preserving ten FULL tiers is worth more than these small candidate ceilings: losing FULL can also lose tier-solution points and the entire tier Simplicity pool. We assign no fabricated failure probabilities or expected value. Any candidate must preserve genuine measurement-driven quantum execution, have supported mathematical correctness, pass the official Checker and timeout limits, receive independent verification, and be included in a rebuilt and audited final artifact before consideration. A later resubmission resets the official tie-break timestamp. This analysis does not authorize or perform integration, release creation or submission.

## Evidence and reproduction

Evidence read from immutable Git snapshots: `0134d0d:docs/TIER05_FINAL_SELECTION.md`; `aed4e77:docs/TIER05_CLEAN_ANCILLA_OSC_VALIDATION.md`; `3dac27e:docs/TIER08_OSC_VALIDATION.md`; `2b5b2f3c565becd762b9dd3c1ec995b94f0fc13f:docs/TIER09_STRUCTURAL_V3_RESEARCH.md`; `8b741156e9d00c0c80a7d6890fa0ee2d1cada2d8:docs/TIER10_STRUCTURAL_V3_RESEARCH.md`. Historical reports are evidence, not files assumed to exist in the final ZIP. No private opponent data, secrets or plaintext were used.

See [calculator instructions and tests](../research/simplicity_analysis/README.md). The program exports all integer assumptions, per-metric gains/losses, all scenario scores and 200 sensitivity rows per scenario. Its deterministic report generator reproduces these tables. Bounds and conditional improvements do not certify physical feasibility, compiler equivalence or future seed reliability.
