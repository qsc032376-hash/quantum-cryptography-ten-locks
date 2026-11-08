# Tier 2 BB84 接收器优化

**ACCEPT，仅限团队代码的执行效率。** 从冻结 v5 `41c7c6775b8fc499c2acdd878b4829bd17e1210d` 出发，唯一生产改动为 tier02/solution.py。Bob 每次求解从构造 2,048 个 QuantumCircuit 改为构造两个局部模板。16 组不加探针的配对计时全部更快，候选的进程峰值内存也较低；官方评分指标相同。基线/候选 solution.py 的 Git blob 为 `4cc64128cfb9a2a2f605483e37cdd942e02a9276` / `f0cec79e578e0ac189ad3c67294cfa1e6a3c5ec0`。这是实验分支，无须更改冻结版或最终提交文件。

## 实际执行路径

1. 官方 Alice/Eve 输入由 Channel 提供。对 Bob 收到的状态，Channel 在每个新电路上按输入位施加可选 X，再按输入基施加可选 H。公开题意为一条干净链路、一条 Eve 随机基截获重发的链路；正式 solve 无需自行模拟 Eve，也不接触隐藏输入。四态是 0、1、+、−。
2. Bob 使用独立于题目数据的伪随机序列选基，固定生产种子 20261107。两个链路的全部 2,048 次抽取发生在接收和公开 Alice 信息之前。Z 接收器仅测量；X 接收器先 H 再测量，均为 q0 → c0。此处没有 H-H、X-X、Z 或旋转可直接消去。在某些输入上 Alice 和 Bob 的 H 在组合后会相邻，但 Bob 不能预知输入或基，且组合/转译属于官方 Channel。
3. 官方实现对每条链路复制各位置的接收电路写入日志，分别将其与独立的输入电路组合，再批量转译并执行 Aer。两条链路各一个批次、每批 1,024 个电路、每个位置一 shot。Helper 每条链路建立模拟器和转译；团队侧预编译接收器仍不能替代**组合后的**转译。这两项官方开销是主要时间来源。
4. receive_all 完成后才能 finish。只用同基公开检查位置估计 QBER，选择错误比例较低的一条链路；平局或没有检查样本时失败。保留同基且不在公开检查集的 **原位置索引**，仅协调一次，用返回的字节做官方 XOR 并返回 UTF-8 文本。该逻辑保持原样；筛选耗时中位约 0.39 ms，不值得改变其实现。详见[题目](../tier02/README.md)及[已有集成验证](TIER02_TIER03_INTEGRATION.md)。

## 正确性与统计

每次 solve 内新建两个接收模板后只读引用，build_circuit 对外仍返回新电路。Channel 的 copy 和非原地 compose 保留每个位置的独立量子实验。缓存的是 Bob 操作，而不是测量结果、输入态、基序列或编译后的秘密输入。对基 b 的测量算子仍为 U†|k⟩⟨k|U，U 分别为 I 或 H；对任意输入态的测量概率不变。

- 新增 6 项测试均通过。逐一核对四个合成制备态、两种测量的投影算子与线序，以及两链全部随机选基先于任何测量/披露。合成夹具验证非同基位被筛去、公开检查位被排除、保留索引正确及平局处理。
- 两个 Aer 种子（207、208）各测 8 种 bit/基组合，每组 4,096 shots。相同基误差为零；不同基的错位频率在 49.22%–50.49% 内。预设容差为 0.05，在理想独立 Bernoulli(0.5) 下，每次比较双侧 Hoeffding 上界 2 exp(−2 × 4096 × 0.05²) < 2.6×10⁻⁹。验收依据概率，不要求相同测量串。
- 合成 Eve 测量后重发，均匀覆盖相同/不同 Eve 基；同基检查 QBER 为 24.524%，接近 25%，干净对照为零。对真实协议另取 8 个 Bob 基种子 300–307，两端均哈希匹配，逐链检查样本数、错误数和保留位数逐项相同；这些是 Bob 选基种子，未修改官方 Aer 种子。每次完整探针核对 Channel 日志顺序、盲选 PRNG 序列、真实 Aer 调用及完成状态。原有 Tier 2 集成探针也通过。
- 开发代码无新增输出、文件访问、固定答案或对 Channel 私有数据的读取。记录仅含汇总量，没有原始测量串、密钥、私有信道数据或明文。

## 实测

Windows 11、Python 3.12.10、Qiskit 2.6.1、Aer 0.18.2，OMP_NUM_THREADS=2、QISKIT_PARALLEL=FALSE，使用原版 Channel 与默认生产种子。每个 worker 均在独立进程中先做一次无关的 Aer 预热；每种测量模式还丢弃首个配对。基线和候选轮换 AB/BA，16 组配对，避免始终先测同一端。表内时间单位 ms，括号为经验四分位区间。solve 计时排除进程启动和外部哈希比对。峰值内存是 Windows 单 worker 生命周期的 peak working set，包括 Python/Qiskit 及预热。

| 指标 | v5 基线 | 候选 |
|---|---:|---:|
| 官方双比特门 | 0 | 0 |
| 官方单比特门 / 总门 | 3 / 3 | 3 / 3 |
| 官方深度 / 活跃位 | 3 / 1 | 3 / 1 |
| 官方 Checker | full，SHA 匹配，flags=[] | full，SHA 匹配，flags=[] |
| 无探针 solve 平均 | 485.93 | 454.73 |
| 无探针 solve 中位（Q1–Q3） | 476.58（474.57–492.49） | 452.06（447.70–455.66） |
| 无探针峰值内存中位，MiB（Q1–Q3） | 144.86（144.78–144.97） | 137.96（137.87–138.07） |
| 两个 Aer 作业合计中位（Q1–Q3） | 167.58（163.27–170.90） | 166.35（164.81–167.12） |
| 创建 Bob 电路时间中位（Q1–Q3） | 41.29（40.77–41.46） | 0.12（0.11–0.13） |
| Channel 批转译中位（Q1–Q3） | 191.35（189.76–192.92） | 190.12（189.20–192.06） |

时间分解来自另一套 16 组配对（带探针），Aer 作业从提交到 result 完成，不能与无探针时间逐项相减。solve 配对节省中位 26.58 ms，16/16 组为正；内存配对节省中位 6.91 MiB。两种测量中的实际接收电路数均保持 2,048；构造调用数从 2,048 降为 2。有重叠的 Aer 区间不支持模拟内核变快。官方在两个干净快照的 submissions/team3 中仅发现 Tier 2，均为 full / hash_ok / metrics_status=ok，记录 2,048 条电路、零重复测量；四个指标来自 Checker 对 Bob 接收电路的官方转译，测量本身不计门。[基线 Checker](evidence/tier02-bb84/baseline-checker.json) · [候选 Checker](evidence/tier02-bb84/candidate-checker.json) · [逐组计时](evidence/tier02-bb84/paired-benchmark.json)

## 复验和边界

在项目依赖环境、此分支根目录运行（计时还使用 psutil，提交实现不依赖它）：

```text
python -m tests.test_tier02_bb84_optimization
python tests/validate_tier02_tier03.py 2
python experiments/tier02_bb84_benchmark.py --candidate HEAD --out reports/tier02-profile.json
python experiments/tier02_bb84_benchmark.py --candidate HEAD --plain --out reports/tier02-plain.json
```

单关官方复验：将原版 tools、common、hashes.txt、tier02 与 submissions/team3/tier02/solution.py 放入干净快照，从快照根运行 `python -I tools/check_submission.py submissions/team3 --out <独立报告目录>`。无需重跑十关。此次接受的是本机可重复的经典构造时间和内存改善，不代表量子硬件加速、评分提升或所有随机种子都成功。进一步减少逐输入组合/编译需要改变官方 Channel 的实现，不在本分支范围。
