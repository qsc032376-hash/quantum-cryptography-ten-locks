# Tier 8 Shor：局部精确 MCX 优化

Junqi Sheng；工作分支 `optimization/tier08-mcx`。

本轮实施审计 4.2 节的候选 A：用 Qiskit 的完整精确 Maslov dirty MCX
替换四控制及以上的 Iten dirty MCX。保留 Gray 路径模乘架构、完整相位估计和
真实 Aer 测量，不引入周期相关的电路裁剪。

**实测双比特门 49,920→42,810（减少 14.2428%），深度 135,160→123,320
（减少 8.7600%）。基线、候选及改名目录均获官方 `full` 和 SHA-256 匹配，
无 flags。最终保留 harness 的 `INCONCLUSIVE`：确定性复杂度改善已验证，
未补做其要求的十组配对种子可靠性实验。** 不把该统计标签误称为 Checker 失败，
也不声称已经达到 harness 的 ACCEPT 门槛。
完整安全记录见 [TIER08_OPTIMIZATION_RESULT.json](TIER08_OPTIMIZATION_RESULT.json)。

## 来源和修改范围

- 稳定基线：`release/ten-locks-v1@868fb65e20c73a27bffc118f3617080df9cf2f8b`。
- 只读参考：[电路审计 4.2 节](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/5390daffd586e60c8c48f7808c1e276284899a49/docs/CIRCUIT_OPTIMIZATION_AUDIT.md)。
- 原样复用 Junrui 的 benchmark harness，固定在
  `0f8e0b0e8a42f1a68b27c52446c346401823099e`；没有合并其他分支或另写比较框架。
- 唯一生产修改：[tier08/modular.py](../submissions/team3/tier08/modular.py)。
  新增[合成测试](../tests/test_tier08_mcx_optimization.py)、
  [冻结 release 夹具](../tests/fixtures/tier08_release_modular.py)及本报告和安全 JSON。

`solution.py`、`order.py`、逆 QFT、RSA 和 keystream 均未修改。
Tier 1–7、9–10 核心文件、官方工具／输入／哈希／评分设置保持 release 内容。
Tier 9/10 对 Tier 8 的复用仅涉及未改动的公开 `permutation_table`。
不修改 release、Tier 5 优化分支或已验证 v2/v3 候选，不合并 main，不创建 PR。

## 数学等价性

旧 MCX6 使用四条 dirty 线，新完整 `synth_mcx_n_dirty_m15(6)` 使用两条。
把新门嵌入旧门的空间，令 C 为六控制、t 为目标、D 为原四条借位：

\[
V_{old}=\operatorname{MCX}_{C,t}\otimes I_{D},\qquad
\widetilde V_{new}=\operatorname{MCX}_{C,t}\otimes I_{D}.
\]

这是精确复酉语义；dirty 线可非零、处于叠加态、与其他计数位纠缠。
新门不再借用的两条旧线恒等作用。M15 内部的相对相位片段在完整构造中抵消，
没有把单个相对相位 Toffoli 当作精确门，也没有启用 `action_only`。
一至三控制保留旧实现，避免三控制时增加辅助位。

每个相邻基态交换仍用相同的外控制及 work 条件；零控制的 X 归一化和撤销不变。
所以每条 Gray 路径、端点换位及完整受控公开模乘都保持原复酉矩阵。
外控制为零时恒等；work 值大于等于 N 的 padding 也恒等。
模乘应保留在 work 上；只撤销借位和 Gray 路径中间态，不能把目标模乘一并反计算。

由局部门替换的组合性，完整 Shor 末态及测量分布不变；不是依靠某次相同输出
或尝试明文哈希来证明。完整 12 个受控幂块、公开底数 2、work 的 `|1⟩`、带 SWAP
的逆 QFT、`q[j]→c[j]` 及直接二进制读数均保持不变。
物理布局仍为 12 个计数位加 6 个 work 位，共 18q/12c；借位 4→2 不等于总宽度减少。

## 正式执行前的验证

首次合成测试 **8 项全部 PASS，6.892 秒**。
未读取真实 locked 数据、周期、因子或明文。

- 对一至五控制，在相同 dirty 空间内逐元素比较原／新复矩阵和解析精确 MCX；
  不拟合或忽略相位。完整矩阵最多九 qubits。
- 人工小模数覆盖外控制零／一、全 work 域、padding、任意 dirty 基态及逆映射。
- 六控制使用旧 11q 公共空间上的固定随机全支撑复纠缠态，比较新／旧 MCX 和人工
  N=5、六位 work 模乘的全部振幅及解析置换。此项是指定态测试，**不是穷尽
  11q 全算子验证**；任意态正确性的结论另依赖完整精确 MCX 的数学语义。
- 人工 N=15 Shor 比较完整复振幅、计数寄存器边缘分布和已知人工参考分布。
- 静态检查主布局、借位不碰撞、12 个幂块、初态、逆 QFT、shots、种子和位序不变。

最大复矩阵误差 `3.82e-14`；六控制纠缠态误差 `1.20e-15`；
小 Shor 新旧振幅差 `8.49e-15`、概率检查最大差 `4.64e-14`，均低于 `1e-9` 容差。
合成 Aer 只有一批、六条电路、各一 shot；两线程、512 MiB 上限。
测试转译显式设置 `qubits_initially_zero=False`，不让任意 dirty 输入变成零态假设。

## 局部模板与整电路评分

以下为实际局部模板转译，不是从 CCX 数量换算的估计。
采用 `rz,sx,x,cx`、优化级别 1、种子 12345、全连接、无 initial layout，
局部测试另设置 `qubits_initially_zero=False`。

| 控制数 | 旧→新 dirty | 旧→新双比特门 | 旧→新深度 | 旧→新总门数 |
| --- | ---: | ---: | ---: | ---: |
| 3 | 0→0 | 14→14 | 29→29 | 34→34 |
| 4 | 2→1 | 26→20 | 69→59 | 77→62 |
| 5 | 3→2 | 34→28 | 93→83 | 101→86 |
| 6 | 4→2 | 42→36 | 117→107 | 125→110 |

正式 Checker 前，先对完整 N=35 电路做与生产路径相同的原生转译，再按官方配置
评分转译，确认候选有收益。正式指标必须进一步与实际传给 Aer 的电路一致。

环境：Python 3.12.14、Qiskit 2.6.1、Aer 0.18.2、NumPy 2.5.4、PyYAML 6.0.3、
psutil 7.2.2。本轮没有安装依赖。
两边按同一官方配置重转译**实际送入 Aer 的电路**：基门 `rz,sx,x,cx`、优化级别 1、
转译种子 12345、全连接、无 initial layout。没有以原生 MCX 数量或更小展示电路评分。

| 官方指标 | release 基线 | 精确 M15 候选 | 减少量 | 相对减少 |
| --- | ---: | ---: | ---: | ---: |
| 双比特门 | 49,920 | **42,810** | 7,110 | **14.2428%** |
| 深度，不含测量 | 135,160 | **123,320** | 11,840 | **8.7600%** |
| 总门数，不含测量 | 148,085 | **130,190** | 17,895 | **12.0843%** |
| 活跃 qubits | 18 | **18** | 0 | 0% |

减少百分比统一为 `(baseline-candidate)/baseline*100`。
完整预检、配对 profile 和未注入种子的官方 Checker 四指标逐项一致。
Profile 在双方注入模拟器种子 2026；生产声明种子 808 不变，官方检查不注入种子。
两边原生转译参数日志相同，harness 确认实际 Aer 调用、转译和种子控制有效。

| 单次资源观测 | release 基线 | M15 候选 |
| --- | ---: | ---: |
| Profile solve 秒 | 57.296 | 31.462 |
| Profile Aer 提交至 result 完成秒 | 56.651837 | 30.914921 |
| Profile 官方评分转译秒 | 0.722978 | 0.558562 |
| Profile 总墙钟秒 | 60.6363 | 34.0300 |
| Profile 进程树采样峰值 RSS MiB | 461.949 | 425.809 |
| 未注入种子的官方 solve 秒 | 49.516 | 55.848 |
| 官方验证总墙钟秒 | 53.2759 | 58.8561 |
| 官方验证进程树采样峰值 RSS MiB | 474.047 | 433.105 |

原生构建加转译在前置静态检查中分别为 0.551549／0.600314 秒；该数包含构建，
不能称为纯转译时间。表中的官方评分转译则是单独计时。
**没有证明稳定模拟提速**：配对 profile 中候选较快，官方原始运行中却较慢。
保留两组相反方向的时间观测，不选择性报告、不追加运行追求更好时间。

## 官方和改名目录验证

| 检查 | 真实执行电路数 | 状态 | SHA-256 | 指标 | flags |
| --- | ---: | --- | --- | --- | --- |
| release 官方 | 1 | full | 匹配 | 完整有效，等于基线表 | 无 |
| 候选官方 | 1 | full | 匹配 | 完整有效，等于候选表 | 无 |
| 候选 `renamed_tier08_validation` | 1 | full | 匹配 | 完整有效，等于候选表 | 无 |

改名验证在独立候选快照内，通过未修改的 `tools/check_submission.py` CLI 执行。
该快照的原 `submissions/team3` 已删除，完整依赖随新目录提供，报告只含 Tier 8。
改名 solve 42.289 秒，CLI 墙钟 45.960169 秒，采样峰值 RSS 509.945 MiB。
所有 profile、官方检查和改名检查的资源状态均为 `ok`，没有缺指标、超时或内存失败。

本轮正式挑战共五次 solve：基线 profile／官方各一次、候选 profile／官方／改名
各一次。全部一个 Aer 批次、每批 64 shots，共 320 shots，无补采样或失败重试。
Profile 直接记录 shots；官方三次各记录一次执行电路，配合未变的每批 64 shots
代码确定采样总量。合成测试的六条人工电路另计，不冒充正式挑战成功。

## 最终建议

**INCONCLUSIVE（harness 的严格统计接受口径）。** 局部优化已经达到本轮要求的
门数／深度改善、数学相位与借位验证、真实 Aer、完整官方解密及改名目录验收。
逐项核对 harness 其余门槛均成立；未提供的是双方至少十个配对种子的证据及
`reliability_reviewed` 接受标记，故原样保留其退出码 1 和推荐值。
这不是 REJECT，也不是测量恢复或 Checker FAIL。

建议保留此提交作为待集成候选，冻结 release 和现有 v2/v3 不动；若后续需要
harness 的 ACCEPT 标签，再单独安排有预算的跨种子可靠性评估。
没有为改变统计标签追加二十次真实求解。无需重写算术架构，也未实施相对相位
近似、删 QFT、改 shots、缩短幂序列或依据隐藏周期消除门等其他优化。

## 合规性和采样风险

官方 Tier 8 没有隐藏 Oracle Helper；允许根据公开参数构造模乘，并要求量子电路
参与因数恢复。本轮只更换精确 MCX 分解，没有经典试除 N、穷举阶、读取隐藏参数
或硬编码周期／因子。公开置换循环只用来编译可逆电路，其长度不作为求阶答案。
生产求解仍从 Aer counts 取连分数分母及其有界 LCM 候选，验证并约简测得的周期，
再经 GCD 取因子、共享 RSA 解密和完整 SHA-256 验证。

默认每批 64 shots、最多两批 128 shots；补采样只允许测量证据不足且时间充足。
每 shot 保留 12 个受控幂块，等效基本模乘次数总和为 4,095。
Checker 的 `oracle_calls=null` 不能解读为零查询；本关没有供该字段计数的官方 Gate。
本报告不保存周期、因子、原始 counts、密钥或明文。

时间和 RSS 是有限观测，不能证明稳定提速或失败率为零。RSS 每 20 ms 对进程树
求和采样，可能漏过短峰或重复计入共享页，不是精确操作系统峰值。
Aer 仍限 512 MiB、两线程；profile 外部预算为 120 秒／1024 MiB，官方 solve 和
评分转译各限 120 秒，harness 官方包装器和改名 CLI 另限总计 370 秒／1024 MiB。

## 快照一致性和复现

Harness 只读取提交。因此先用独立临时索引建立不可变受测快照
`36277525627f4d54909a03af19298754eeb594cb`，没有移动任何分支。
快照包含生产补丁及两份测试文件；正式交付另附报告。JSON 的
`tested_source_sha256` 用于核对交付内容与受测文件逐字节一致。
复现可以使用最终交付提交，不要求临时快照永久保留。

合成测试：

```sh
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  python -B tests/test_tier08_mcx_optimization.py
```

在固定版本 harness 的同仓库工作树中，把最终交付 SHA 填入 CANDIDATE_SHA：

```sh
PYTHONDONTWRITEBYTECODE=1 python -B benchmarks/circuit_benchmark.py \
  --baseline 868fb65e20c73a27bffc118f3617080df9cf2f8b \
  --candidate CANDIDATE_SHA --tier 8 --seed 2026 --official --rules-reviewed \
  --timeout 120 --memory-mb 1024 --output /private/path/tier08_comparison.json
```

这会再次执行四次真实求解，不应为刷新报告反复执行。
改名验证应从同一候选建立完整临时快照，仅把 `tier08/`、`tier07/qpe.py`、
`rsa_classical.py` 和 `classical_keystream.py` 放入新团队目录，删除快照中原 `team3`，
避免固定名字回退；只保留 Tier 8 的 `solution.py`，再运行未改动的官方 CLI：

```sh
python -B tools/check_submission.py submissions/renamed_tier08_validation \
  --out /private/path/tier08_renamed_checker
```

应核对报告仅检查 Tier 8、`full`、`hash_ok=true`、指标有效且 flags 为空。
原始临时日志／电路／报告不提交；只保留安全白名单汇总。
