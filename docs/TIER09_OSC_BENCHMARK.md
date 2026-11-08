# Tier 9 OSC benchmark preparation

**Status: OSC NOT EXECUTED.** On 2026-11-08 the local host had no Slurm commands, configured OSC-specific SSH identity, confirmed OSC username, allocation/account, balance, cluster access, Python environment, or permission to submit. These observations do not establish whether the user has an OSC account. No login, batch job, OSC software inspection, job ID or cluster measurement was obtained. Cardinal is a proposed target only. The scripts are locally syntax-checked and their two preflight paths checked using a local environment; they have not been tested under Slurm. Instructions and limitations are in `hpc/osc/README.md`. Account and partition must be selected from actual authorization, not fabricated.

Frozen baseline `41c7c6775b8fc499c2acdd878b4829bd17e1210d`; candidate `00fee41ee8707ccdd2b6920dd95cc877d2d506bf`; independent harness `ab9676749e00da904d0b8076811a2407d3b7205f`. The two scripts request 2 CPU cores, 4 GiB, five minutes and run one seed in a separate process, preserving the harness limits of 120 seconds and 1024 MiB RSS per worker. Before use validate software, resource policy and job permission. Seed plan: 1000 through 10000 in increments of 1000, 64 shots per completed run, same versions and configuration; preserve actual forwarded seeds and every timeout. The overall strict threshold is ten completed paired passes, not a post-hoc subset. Simulation uses statevector CPU, default precision, two threads, 512 MiB simulator limit. Qiskit native transpilation uses each unchanged solution's settings; scoring uses `tools/scoring_config.yaml` in the snapshots. Exact node, operating system, memory and CPU, compiler and versions are pending on OSC. Local preflight: macOS, Python 3.13.9, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4, psutil 7.2.2. No local simulation was run for this preparation.

## Earlier evidence, not OSC measurements

Original Linux experiment (candidate `docs/TIER09_ADVANCED_OPTIMIZATION.md` and JSON): all 10 candidates passed; baseline seed 1000 timed out, the other nine passed. Each pair below is baseline/candidate. The timeout's actual forwarded seed and shots are unknown. Times are solve seconds, not paired OSC measurements.

| Seed | Baseline | Candidate |
|---:|---:|---:|
|1000|TIMEOUT|PASS 59.674|
|2000|PASS 32.275|PASS 111.225|
|3000|PASS 30.011|PASS 41.276|
|4000|PASS 27.359|PASS 36.661|
|5000|PASS 32.934|PASS 37.053|
|6000|PASS 32.232|PASS 40.478|
|7000|PASS 33.496|PASS 62.338|
|8000|PASS 27.977|PASS 38.595|
|9000|PASS 47.439|PASS 47.939|
|10000|PASS 27.653|PASS 55.837|

Completed nine-pair mean solve 32.375 versus 52.378 seconds; execution order and load confound the comparison. Prior sampled worker RSS values are documented in independent audit `c89c474:docs/V6_TIER09_INDEPENDENT_AUDIT.md`; they do not establish a reproducible memory improvement. Neither runtime nor memory has an OSC comparison. Circuit construction and native compilation time remain unmeasured separately by these batch scripts.

| Official scoring metric | baseline | candidate |
|---|---:|---:|
| Two-qubit gates | 89,075 | 55,999 |
| Depth | 235,048 | 120,242 |
| Total gates | 263,601 | 168,116 |
| Active qubits | 21 | 22 |

The earlier independent audit reports exhaustive 1,280 actual public multiplier/control basis cases including padding, small full complex operators, initialization and measurement mapping; fixed-mask elimination and inverse composition give a permutation identity, while ideal X/CX/MCX gates preserve relative phase. Workspace restoration depends on clean-zero initialization. It does not exhaustively verify the complete transpiled 22-qubit operator. Earlier local official checker reports both full, SHA-256 matching, metrics ok, flags empty; no OSC checker was run. These are prior findings, not freshly reproduced here. See `c89c474:docs/V6_TIER09_INDEPENDENT_AUDIT.md` for the proof, caveats and reproducibility.

Correctness: supported by prior finite and compositional evidence; OSC validation pending. Circuit resources: prior measurements support reductions in gates and depth with one additional active qubit. Runtime and memory: **INCONCLUSIVE**. Strict benchmark: **INCONCLUSIVE**, with the previous timeout retained. Overall **INCONCLUSIVE**. No official competition hardware is represented as OSC.
