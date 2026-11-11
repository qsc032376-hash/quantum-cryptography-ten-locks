# v6.3 Candidate A integration

**ACCEPT_INTEGRATION_RC**

Base aee41fb328027f8927a55d65c68e8a3e30332697. Tier 5 source 97fcc0c7d6dec3b7385dc237d47d89d4d6ffd15c. Tier 8 source 8b18d3d18a6ee6b744e5ce60af13ed1c4f259c9d. The two Tier 8 runtime files are identical to that commit, including its last-pivot native 7,856-CX network. Tier 9, Tier 10, the shared classical code, official helpers, official Checker and scoring configuration retain the v6.2 Git blobs.

Tier 5 ports the selected mask, transition and fused-oracle functions into the team oracle module. Local calls replace the research import and mock-patch cycle. The input validation is preserved. The production solver precompiles at level 2, retains GF(2) processing, runs 25 Grover iterations with 128 shots, and uses the original measured recovery. The final operation uses the actual adjoint to uncompute the relative-phase network.

## Complete official Checker runs

Source extraction and fresh official checkout fce7c3950d06bb4d23e3c057b4625f901c396de4 with just the ZIP extracted to submissions/ both passed 10/10 FULL. All ten hashes, quantum execution checks, scoring metrics and empty flag lists were verified. No final-run timeout. Source and archive per-tier metrics agree. Python 3.12, Qiskit 2.6.1 and Aer 0.18.2. Times below are per-run solve observations on a shared host.

| Tier | CX | Depth | Gates | Active | Source solve s | ZIP solve s |
|---|---:|---:|---:|---:|---:|---:|
|1|151|44|298|25|12.275|20.801|
|2|0|3|3|1|1.165|1.297|
|3|7,808|8,771|19,497|7|7.147|10.943|
|4|183|195|455|20|0.370|0.488|
|5|10,950|19,703|28,413|19|26.357|24.570|
|6|3,000|5,715|8,752|22|40.334|35.935|
|7|209|154|536|15|0.286|0.306|
|8|7,856|18,804|22,861|18|8.203|8.682|
|9|34,186|71,632|102,830|22|29.613|28.573|
|10|38,823|92,604|111,337|19|4.771|8.838|

Across ten separate scoring circuits the measured totals are **103,166 CX / 217,625 depth sum / 294,982 gates**. The v6.2 reference totals were 132,816 / 303,305 / 387,207. Only Tiers 5 and 8 changed. The projected total gate count was 50 lower. Replaying the original Tier 5 research builder and the integrated builder in this same environment reproduced identical pre-scoring gate counts and 28,413 scored gates for both, versus the historical 28,363. The exact cross-environment cause was not isolated. [Replay](v63-evidence/compiler-replay.json).

[Source Checker](v63-evidence/candidate-checker/report.json) and [ZIP Checker](v63-evidence/zip-checker/report.json). A preliminary source run used only the Tier 8 change after a Windows path error interrupted Tier 5 staging. It recorded a Tier 6 solve timeout while other jobs were running. Its distinct tree and report are retained under preflight-tier08-only. Neither its scores nor its outcomes are counted toward Candidate A.

## Operator verification

Tier 5 checked all 1,024 Boolean inputs, the relative Toffoli operator and phase-marking on a coherent input having support on every key. Maximum phase error was 7.92e-16, scratch leakage probability 2.78e-30, arbitrary-workspace sample error 2.96e-17 and compiled 25-round state error 6.36e-12. No phase fitting was used. Tier 8 checked all 512 complex basis columns for each public multiplier 2, 4, 11 and 16, including control-off, padding, inverse and every borrowed-bit value. Maximum entry error was below 2.76e-14 and measured borrowed-wire leakage was zero. Structure and Fourier tests also passed. [Tier 5](v63-evidence/tier05-equivalence.json), [Tier 8](v63-evidence/tier08-equivalence.json).

## Package and release risks

The ZIP uses exact Git bytes, contains all 37 runtime and documentation members, and was validated without research modules. The inherited v6 README and write-up carry an explicit v6.3 scope note. The frozen final ZIP stayed at SHA-256 b8e1b90b9cdc038b1b7a066d111c5e4c64a6994a95cab4f1add86f4a9a5818f1. [Cache and archive manifest](V63_CACHE_MANIFEST.md).

Candidate A was retained after validation. Optional B at 9ca45f31039409f16dd7d7865e11fe8186fc16f5 used the CRLF-rendered Tier 10 cache and a research-only module/configuration. The cache content discrepancy is explained by line endings. B would still require a separate production port and independent operator, seed, package and ten-tier validation against the LF package. Its projected improvement of 660 CX is not included. Final approval by a different reviewer and any competition upload remain outstanding. [Independent handoff](V63_RELEASE_AUDIT_HANDOFF.md).

## Independent simulator seeds on the extracted package

Five fresh worker processes per tier, seeds supplied to the actual Aer call, under the v6.1 harness's 120-second outer limit. Reported peak RSS is sampled every 20 ms. Seeded timings do not establish a hardware speedup or a universal success probability.

| Tier | Seeds | Pass | Median solve s | Median transpile s | Median peak RSS MiB |
|---|---|---:|---:|---:|---:|
| 5 | 5301-5305 | 5/5 | 12.062 | 0.134 | 192.07 |
| 8 | 8301-8305 | 5/5 | 2.106 | 0.051 | 144.59 |

[Full seed records](v63-evidence/seeds.json).
