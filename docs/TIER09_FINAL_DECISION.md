# Tier 9 最终集成决策：INCLUDE_V2

Junqi Sheng · 2026-11-09（America/New_York）

工作分支：validation/tier09-final-decision

**最终建议：INCLUDE_V2。** 将准确的 Tier 9 v2 源码交给 Junrui 纳入 v6 的常规集成流程；
保留冻结 v5 回退，不在截止前改用 v3。这是结合已有数学独立审计、后续 OSC 十组配对
及官方 Checker 的新选型决定，**不是宣称 v6 已整包通过或已发布**，也不把历史
Harness 的 INCONCLUSIVE 改写成自动 ACCEPT。

本轮仅审查已有文件、源码指纹和评分算术，新增本决策文档。没有运行量子电路、
重新做 Checker、提交 OSC 作业或发展新优化。工作树从 v2 建立，相对分支起点唯一
变化是本报告；生产代码、评分工具、release 分支及提交包均未修改。

## 1. 固定来源与三候选对照

| 角色 | 分支／准确提交 |
| --- | --- |
| 冻结回退 v5 | release/ten-locks-v5-verified · `41c7c6775b8fc499c2acdd878b4829bd17e1210d` |
| **选定源码 v2** | optimization/tier09-v2 · `00fee41ee8707ccdd2b6920dd95cc877d2d506bf` |
| v2 原始受测源码快照 | `f9ded9fac59ebd8a2ed3e19232ffe2eaa88bac93`；最终 v2 只追加文档，生产指纹相同 |
| OSC 已完成报告 | research/tier09-osc-benchmark · `e133887728a60065470205e66982a1f44f12f8b8` |
| 未选的结构 v3 | research/tier09-structural-v3 · `2b5b2f3c565becd762b9dd3c1ec995b94f0fc13f` |
| 既有数学独立审计 | `c89c4744f07b436fcbd25e535a48b8bbd3276fc3` |
| 未改动 Benchmark Harness | `ab9676749e00da904d0b8076811a2407d3b7205f` |

此处 v2／v3 指 **Tier 9 算法候选**，不是团队历史整包 v2／v3。

| 官方评分指标 | 冻结 v5 | Tier 9 v2 | Tier 9 v3 |
| --- | ---: | ---: | ---: |
| 双比特门 C | 89,075 | **55,999** | 55,971 |
| 深度 D | 235,048 | **120,242** | 120,223 |
| 总门数 G | 263,601 | **168,116** | 168,088 |
| 活跃 qubits Q | 21 | **22** | 22 |
| 最充分的已有配对证据 | OSC 十组 | **OSC 十组** | 本机两组，缺少同等独立可靠性验收 |
| 本次处置 | 保留回退 | **进入后续集成** | 保留研究，不替换 v2 |

v2 相对 v5：C 减少 33,076（37.1328%），D 减少 114,806（48.8436%），
G 减少 95,485（36.2233%），Q 增加 1（4.7619%）。
v3 相对 v2：只少 28 CX（0.050001%）、19 深度（0.015801%）、28 总门（0.016655%）。
这些是实际执行电路的官方基门指标，不按 CCX 数量推算 CX。

本轮静态核对四个主引用的官方 tools、SCORING.md、common、hashes.txt、
requirements.txt、tier01–tier10 官方目录及 drafts 树与 v5 相同。
v5→v2 的团队生产差异恰好为第 6 节三份 Tier 9 文件；v2→v3 唯一生产差异是
shared_controls.py。其他 Tier 的运行源码没有包含在该变更集合中。

## 2. 数学、相位与辅助位证据

v2 使用公开完整置换：

\[
P_m(x)=
\begin{cases}
mx\bmod N,&x<N,\\
x,&x\ge N.
\end{cases}
\]

固定掩码消元处理行 i 时，先前较小行已固定；置换性保证 y=T(i)≥i。
以固定的 y 作控制补齐 i 缺少的位，再以固定的 i 作控制清掉多余位。两阶段受影响
状态分别≥y 和≥i，不破坏早先行。最终消到恒等，反序执行自逆门即得到 P_m。
给每个逻辑翻转加外控制，关闭分支为 I、开启分支为 P_m，覆盖全部 work 与 padding，
不是只验证从 |1⟩ 可达的轨道。

源级 X/CX/CCX/MCX 均为精确置换门，保留相对相位。原 emitter 的
F·MCX(C,p)·F 中 F 不改变控制且自逆。v2 改的是上游全局消元，没有把 v5 已有共享
控制扇出重复计为新优化；没有改官方 Oracle、预求隐藏阶／因子或用经典答案替代测量。

新增 synthesis_work 是**实际送入 Aer 的 22-qubit 电路**中的零初始化线，原生执行
空闲，官方 HLS 可以使用并恢复它。应同时说明：原生声明 22q、原生活跃 21q、
官方分解活跃 22q。clean 合成的契约是

\[
V(|\psi\rangle\otimes|0\rangle_a)=(U|\psi\rangle)\otimes|0\rangle_a.
\]

该式覆盖任意数据态及外部纠缠，**不声称辅助输入为一时完整算子也相等**。
work q14 制备为 1、14 个受控幂的顺序、完整逆 QFT、qj→cj 测量映射保持不变。
没有丢弃单独相对相位 Toffoli 的必要修正。

已有证据：

- v2 原报告的 7 项全局／合成测试及 2 项 clean 模板测试通过，涵盖实际源级控制、
  work、padding、人工编译电路的复振幅、概率与 clean 恢复。
- 独立审计 c89c474 用独立脚本检查五个实际公开乘子的 1,280 个控制/work 基态；
  三个人工模数的完整复算子逐元素比较，未拟合全局相位，最大误差 7.77e-15；
  既有 7＋2 测试在该审计也复跑通过，初始化和测量布局已核对。
- 没有物化完整 22-qubit 转译复算子。结论依赖全域组合证明、局部复算子、
  clean 子空间验证及实际测量，不把有限测试冒称无限范围的形式验证。
- 本轮未重跑这些测试；生产文件 SHA-256 与原受测清单重新核对一致。

## 3. OSC 已完成结果与证据层级

### 3.1 版本、种子与预算

以 e133887 报告**顶部 “OSC execution — 2026-11-08”**为已完成执行记录。
后半仍保留准备期的 pending/no OSC checker 文字，不应覆盖顶部后续结果。
脚本锁定 baseline=41c7c67、candidate=00fee41、Harness=ab96767，要求 Slurm 计算分配，
拒绝覆盖已有输出；没有提高 worker 时限来使原超时通过。

环境为 OSC Cardinal CPU、Intel Xeon CPU Max 9470，Python 3.12.4、
Qiskit 2.6.1、Aer 0.18.2、NumPy 2.5.4、psutil 7.2.2。每个 Slurm 作业
2 核／4 GiB／5 分钟，worker 仍为 120 秒／1024 MiB，Aer statevector CPU
默认双精度、512 MiB／2 线程。多个节点 CPU 型号一致，但节点和负载并不完全相同。

**下表逐项转录已提交的 OSC 汇总，不是本轮重新读取原始作业 JSON。**
每个版本每个 seed 64 shots，共 20 个完成 trial、每版 640 shots。
报告明确每个 PASS 均核验了实际 forwarded seed 和明文 SHA-256。

| seed | v5／v2 | solve 秒 v5／v2 | 采样峰值 RSS MiB v5／v2 |
| ---: | --- | ---: | ---: |
| 1000 | PASS／PASS | 28.275／35.889 | 167.76／170.39 |
| 2000 | PASS／PASS | 28.337／35.490 | 172.39／171.59 |
| 3000 | PASS／PASS | 28.413／36.522 | 168.64／170.14 |
| 4000 | PASS／PASS | 28.561／36.436 | 166.97／171.26 |
| 5000 | PASS／PASS | 28.195／36.045 | 168.66／170.40 |
| 6000 | PASS／PASS | 27.975／35.804 | 167.21／169.86 |
| 7000 | PASS／PASS | 28.333／35.180 | 167.85／172.17 |
| 8000 | PASS／PASS | 28.084／36.725 | 169.77／171.77 |
| 9000 | PASS／PASS | 28.124／36.368 | 166.97／170.14 |
| 10000 | PASS／PASS | 28.010／36.530 | 169.67／169.67 |

本轮只读核对脚本与原 Harness：AerBackend.run 实际接收 requested seed＋调用索引；
PASS 要求资源 ok、solve≤120 秒、哈希匹配、实际执行、所有 Aer job 完成、
记录电路数一致及正确 seed 转发。这里不是固定 seed909 重复十次。
cross PASS 也不等于每条 trial 另外执行了一次完整官方 FULL Checker。

### 3.2 官方 Checker 与资源

OSC 报告记录：对两个准确 Git archive，在隔离、正确命名的 submissions/team3 中，
原官方 check_tier 均为 **full、SHA-256 匹配、metrics ok、flags=[]、实际执行电路**。
四指标与第 1 节及原 Linux 官方结果一致。OSC 未另声明做过改名目录整包验证。

| 测量项 | v5 | v2 | 解读 |
| --- | ---: | ---: | --- |
| 十组平均 solve 秒 | 28.2307 | 36.0989 | v2 增加 27.8711%，约 7.87 秒 |
| 十组最大 solve 秒 | 28.561 | 36.725 | 该批均低于 120 秒 |
| 平均采样峰值 RSS MiB | 168.589 | 170.739 | 约多 2.15 MiB，无稳定内存改善 |
| 最大采样峰值 RSS MiB | 172.39 | 172.17 | 单个最大值不能证明改善 |
| seed2026 profile Aer elapsed 秒 | 27.960 | 36.026 | 含 Aer 内部工作与等待 |
| profile 评分转译秒 | 1.472 | 1.537 | 建电路与 native 转译未单独测量 |
| 官方 solve 秒 | 27.951 | 36.326 | 两版在官方时限内 |

RSS 是采样进程树合计，可能漏掉短峰、重复计共享页，不是精确分配器峰值。
报告没有表明本批发生超时或内存异常；节点约 631 GiB RAM 不是本作业的 4 GiB 分配，
不能混用。没有 GPU 或量子硬件加速结论。

### 3.3 保留历史结论与原始证据边界

OSC 原比较工具仍为 **INCONCLUSIVE**：rules/reliability 审查声明未置位；
十组完成条件已满足，不代表全部严格条件自动成为 true。本次选型不编辑原结果、
不添加虚构人工签名，非零退出码也不等于官方 Checker 失败。

原 Linux 基线 seed1000 超时继续保留，实际 seed、完成 shots、hash 仍未知。
候选该轮最大 solve 为 111.225 秒，显示环境敏感性；新 OSC 成功不能解释旧超时原因。
c89c474 在当时证据不完整时给出的 INCONCLUSIVE 也仍是历史事实。

**原始 OSC JSON、节点元数据与日志保存在私有 tier09-osc-research，未随 e133887 提交。**
本轮确认固定报告、工具契约和版本绑定，没有逐条重审这些原始文件，亦未新制造
“独立十组测试”。如 Junrui 需要溯源，应读取已有私有记录，无需为本决定再提交大型
OSC 作业。有限十种子不能保证所有种子或官方机器表现。

## 4. v3 的收益不足以承担截止前替换

v3 唯一生产变更是 shared_controls.py 将扇出 pivot 从首个目标改为最后目标。
任一 pivot 的 F·MCX(C,p)·F 都条件翻转同一集合，控制关闭为 I；没有发现控制、
padding、相位或 clean 契约问题。报告含五个实际块完整 256×256 复算子与逆算子检查
（最大误差 2.27e-13）、原 7＋2 测试及隔离官方 full／哈希／有效指标／无 flags。

但只有 macOS 本机 seed1000、2000 两对，每次 64 shots：v2 solve 为 17.663、17.677 秒，
v3 为 19.172、18.246 秒，两次候选都更慢；首对与算子测试重叠。隔离 Checker
solve 17.717 秒，采样 RSS 194.98 MiB。这些不能跨机器与 OSC 直接比速度，也不能
替代 v2 的独立十组可靠性记录。原 v3 报告明确 INCONCLUSIVE，没有同等独立可靠性验收。

相对于 v2，28 CX、19 深度和 28 总门的额外收益很小。截止前引入新生产 blob、
重新核对打包与验收的成本没有被该收益抵消。**保留 v3 研究，选择 v2，不安排新 v3 OSC。**

## 5. 官方 Simplicity 的实际权衡

按未改的 SCORING.md／tools/scoring_config.yaml：

\[
S=0.4\,b_C/C+0.3\,b_D/D+0.2\,b_G/G+0.1\,b_Q/Q,\qquad
P_9=(0.375\times6)S=2.25S.
\]

b 是本关所有合格参赛队的对应最优值。若 b=0，官方另规定 team=0 时 ratio=1，
否则 ratio=1/(1+team)。只有 full 且指标有效者有资格。评分取 solve() 实际执行、
官方转译后双比特门最多的电路，不是展示用 build_circuit()。

v2 大幅改善合计 **90% 权重**的 C、D、G，代价是 **10% 权重**的 Q 从 21→22。
在固定可比较最优值下，单独 qubit 项的最大分数损失不超过

\[
2.25\times0.1/22=0.0102273\text{ 分}.
\]

不知道其他队伍的 b，不能保证净比赛分数一定更高，也不能把资源减少的加权百分比
当成 Simplicity 实际增分。选择依据是已确认的三项大幅资源收益与有限宽度代价，
不是虚构的排名或最终分数。

v3 相对 v2 的候选自身额外得分上界为

\[
\Delta P_9 \le 2.25\left(
0.4\frac{28}{55999}+
0.3\frac{19}{120242}+
0.2\frac{28}{168116}\right)
=0.000631616.
\]

这个上界也适用于本队只提交二者之一。对任一改善指标，记 x=v2、y=v3（y<x），
固定其他队伍的最优值为 b_other：若 b_other≥x，两种提交该维都得满比率，增益为零；
若 y<b_other<x，增益为 1−b_other/x≤1−y/x；若 0<b_other≤y，增益为
b_other(1/y−1/x)≤1−y/x。best=0 的特殊规则也不超过此界。乘对应权重及分池后求和，
qubit 项无变化，即得上述结果。这是上界，不是预计得分。
其量级远小于官方 0.01 平分阈值，但不能断言绝不影响排名。结合可靠性缺口，
它不足以支持截止前换掉 v2。

配置固定为 rz/sx/x/cx、optimization_level=1、seed_transpiler=12345、
全连接、无 initial_layout；solve 和评分转译各 120 秒。配置及规则 blob 已核对相同。

## 6. 给 Junrui 的最小生产交接

**只从 `00fee41ee8707ccdd2b6920dd95cc877d2d506bf` 取以下三份文件。**
不整分支合并 OSC/v3 研究，不将测试、报告、hpc 工具或临时结果装入生产包。

| 操作／文件 | 用途 | SHA-256 |
| --- | --- | --- |
| 新增 submissions/team3/tier09/global_permutation.py | 固定掩码完整置换编译 | `7c1c6bc167ecadff5f64619c15d1d9f3db3d3617387590e41cadfe979b5d5a0c` |
| 替换 submissions/team3/tier09/shared_controls.py | 沿用 v5 emitter，仅导入新编译器 | `cb4879a6b610d8c459ceea8b4f14b9d7605eb431d7fbf04e5e018d0ccc8a7bb6` |
| 替换 submissions/team3/tier09/solution.py | 加入实际 clean 线路及诊断 | `5ac6efab5b99af915fdcccd94ff99e1f99ffeb0336e938d6962066396da2d256` |

预期单关官方指标：**55,999 / 120,242 / 168,116 / 22**（C / D / G / Q）。

保留旧 tier09/modular.py，因为 Tier 10 仍依赖它；保留 Tier 8 的公开置换表／阶恢复、
Tier 7 QFT、RSA 经典模块及其余各关。不能只复制 import 修改，ZIP 清单必须新增
global_permutation.py；不能误取 v3 的末 pivot 文件。官方 inputs/tools 保持原样。

集成后的常规交接检查由 Junrui 执行：核对准确源码指纹与依赖、独立包改名导入、
整包官方 Checker 的 full／哈希／指标／flags、资源与回退包。**这是后续 v6 整包流程，
不是本轮已执行结果，也不要求再开大型 OSC 作业。**
若真实集成出现导入、哈希、指标或时限阻断，采用准确 v5 对应文件／整包回退，
不反复跑到成功或临时掺入 v3。冻结 v5 不作任何修改。

交接须保留运行风险：多一条 qubit；OSC 样本平均慢约 28%；Linux 曾接近 120 秒；
采样 RSS 非精确峰值；有限理想模拟不保证任意种子、噪声或硬件成功率。

## 7. 可追溯来源

1. [v2 数学、测试、Linux 结果及指纹](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/00fee41ee8707ccdd2b6920dd95cc877d2d506bf/docs/TIER09_ADVANCED_OPTIMIZATION.md)
   ／[安全 JSON](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/00fee41ee8707ccdd2b6920dd95cc877d2d506bf/docs/TIER09_ADVANCED_OPTIMIZATION.json)。
2. [既有数学独立审计](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/c89c4744f07b436fcbd25e535a48b8bbd3276fc3/docs/V6_TIER09_INDEPENDENT_AUDIT.md)。
3. [OSC 已完成执行报告](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/e133887728a60065470205e66982a1f44f12f8b8/docs/TIER09_OSC_BENCHMARK.md)
   ／[锁定版本和预算的脚本](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/e133887728a60065470205e66982a1f44f12f8b8/hpc/osc/tier09_benchmark.py)。
4. [v3 研究及证据](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/2b5b2f3c565becd762b9dd3c1ec995b94f0fc13f/docs/TIER09_STRUCTURAL_V3_RESEARCH.md)
   ／[两对本机结果](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/2b5b2f3c565becd762b9dd3c1ec995b94f0fc13f/docs/evidence/tier09_structural_v3/local-results.json)
   ／[隔离 Checker](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/2b5b2f3c565becd762b9dd3c1ec995b94f0fc13f/docs/evidence/tier09_structural_v3/isolated-checker.json)。
5. [官方评分](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/41c7c6775b8fc499c2acdd878b4829bd17e1210d/SCORING.md)
   ／[固定配置](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/41c7c6775b8fc499c2acdd878b4829bd17e1210d/tools/scoring_config.yaml)。
6. [原 Harness 的种子及 PASS 定义](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ab9676749e00da904d0b8076811a2407d3b7205f/benchmarks/cross_seed_regression.py)
   ／[实际 seed 转发](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ab9676749e00da904d0b8076811a2407d3b7205f/benchmarks/worker.py)。
