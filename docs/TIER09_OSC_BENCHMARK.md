# OSC execution — 2026-11-08

Executed on OSC Cardinal CPU partition under an active project with a reported remaining budget of 500 before the jobs (OSCusage figures may lag). The authenticated identity and sensitive project details remain in private OSC storage. The 20 individual experiments used two CPU cores, 4 GiB Slurm memory and five-minute job limits, with a 120-second/1024 MiB worker cap. Jobs were submitted as serial Slurm dependencies, not arrays. Seeds 1000–10000, 64 shots per run, statevector CPU, double/default precision, simulator max 512 MiB and two threads. Actual forwarded seed and SHA-256 match were recorded by the harness for every PASS. Result JSON, node metadata, logs and job IDs remain in the private `tier09-osc-research` directory. Experiment job IDs 16339391, 16339392 and 16339394–16339411; checker job 16339412; CPU Aer smoke job 16339390. The earlier numbers shown by `sbatch --test-only` were not submitted jobs.

20 trials recorded Intel Xeon CPU Max 9470, Linux 5.14.0-570.154.1.el9_6 x86_64, Python 3.12.4, Qiskit 2.6.1, Aer 0.18.2, NumPy 2.5.4 and psutil 7.2.2. The hardware records show approximately 631 GiB node RAM, not the job allocation. Multiple nodes were used; CPU model matched, but node and load effects remain possible. No GPU used. The source commits, configuration, official checker and harness are unchanged from the preparation section below.

| seed | baseline / candidate | solve seconds baseline / candidate | sampled peak RSS MiB baseline / candidate |
|---:|---|---:|---:|
|1000|PASS / PASS|28.275 / 35.889|167.76 / 170.39|
|2000|PASS / PASS|28.337 / 35.490|172.39 / 171.59|
|3000|PASS / PASS|28.413 / 36.522|168.64 / 170.14|
|4000|PASS / PASS|28.561 / 36.436|166.97 / 171.26|
|5000|PASS / PASS|28.195 / 36.045|168.66 / 170.40|
|6000|PASS / PASS|27.975 / 35.804|167.21 / 169.86|
|7000|PASS / PASS|28.333 / 35.180|167.85 / 172.17|
|8000|PASS / PASS|28.084 / 36.725|169.77 / 171.77|
|9000|PASS / PASS|28.124 / 36.368|166.97 / 170.14|
|10000|PASS / PASS|28.010 / 36.530|169.67 / 169.67|

All 10 pairs passed with verified hash and forwarded seeds. Mean solve time 28.2307 versus 36.0989 seconds; mean sampled RSS approximately 168.59 versus 170.74 MiB. Both versions run on the same cluster and CPU model, but different nodes can affect timings. These results do not establish a runtime or memory improvement. Sampled process-tree RSS is not exact peak allocation. The one-off seed-2026 profile reported Aer elapsed 27.960 versus 36.026 seconds; this includes Aer internal work and is not pure simulation-kernel time. Scoring transpilation was 1.472 versus 1.537 seconds. Construction and native transpilation times were not independently measured. One profile RSS measurement favored candidate but is not a reproducible memory improvement.

On OSC, official `check_tier` in isolated Git archives and correctly named `submissions/team3` returned **full**, SHA-256 match, metrics **ok**, no flags and an executed circuit for each version. Baseline/candidate: two-qubit gates 89,075 / 55,999; depth 235,048 / 120,242; total gates 263,601 / 168,116; active qubits 21 / 22. These agree with the earlier local checker. Official solve times were 27.951 / 36.326 seconds. The official wrapper preserves its 370-second outer bound and official internal limits; profile has its own 120-second worker limit. The comparison tool returned INCONCLUSIVE; its reliability and rules review attestations were not asserted. Its nonzero exit is a recommendation, not a checker failure.

Correctness: supported by ten matching runs, the official checker, and the earlier independently designed mathematical audit described below; the proof was not rerun in this OSC session. Circuit resources: reductions confirmed, with one extra active qubit. Runtime: candidate slower in this sample. Memory: no reproducible improvement established. The ten-pair completion criterion was satisfied in this run, but the strict overall benchmark remains **INCONCLUSIVE** under the unchanged harness acceptance conditions; the original separate baseline timeout is retained. These results do not represent the official competition hardware.

# Tier 9 OSC benchmark preparation

**Historical preparation status (superseded by the OSC run below): OSC NOT EXECUTED.** On 2026-11-08 the local host had no Slurm commands, configured OSC-specific SSH identity, confirmed OSC username, allocation/account, balance, cluster access, Python environment, or permission to submit. These observations do not establish whether the user has an OSC account. No login, batch job, OSC software inspection, job ID or cluster measurement was obtained. Cardinal is a proposed target only. The scripts are locally syntax-checked and their two preflight paths checked using a local environment; they have not been tested under Slurm. Instructions and limitations are in `hpc/osc/README.md`. Account and partition must be selected from actual authorization, not fabricated.

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
