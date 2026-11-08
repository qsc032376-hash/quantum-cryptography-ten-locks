# Tier 5：Grover Oracle 公开常量折叠结果

Junqi Sheng，2026-11-08，`optimization/tier05-oracle`。

**实际评分双比特门 21,150 → 15,150（−28.37%），深度 33,055 → 29,503
（−10.75%）。原版、优化版及改名团队目录均通过官方 Checker：`full`、SHA-256
匹配、有效指标、无 flags。** 本次只实现公开 S-box／PERM 常量折叠。
完整安全记录见 [TIER05_OPTIMIZATION_RESULT.json](TIER05_OPTIMIZATION_RESULT.json)。
Harness 的较严格可靠性接受判定仍为 `INCONCLUSIVE`，原因及限制见下文，未改报 `ACCEPT`。

## 固定来源及修改范围

- 稳定基线：`release/ten-locks-v1@868fb65e20c73a27bffc118f3617080df9cf2f8b`。
  新工作树直接从此提交创建；release 分支没有修改。
- 数学方案：[MATHEMATICAL_OPTIMIZATION_PLAN.md 的 Tier 5 A 节](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/8b6d36c31b8d42b0c1aa6c5c375c21a58a8cd03c/docs/MATHEMATICAL_OPTIMIZATION_PLAN.md)。
- 电路审计：[CIRCUIT_OPTIMIZATION_AUDIT.md 的 Tier 5 节](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/5390daffd586e60c8c48f7808c1e276284899a49/docs/CIRCUIT_OPTIMIZATION_AUDIT.md)。
  该审计的旧「待集成」状态不适用于当前完整 release；本轮实际验证完整解密。
- 原样复用 Junrui 的 `optimization/benchmark-harness@0f8e0b0e8a42f1a68b27c52446c346401823099e`。
  数学、审计、harness 均只读获取，没有合并其分支，也没有另写比较框架。

唯一修改的生产文件为 [tier05/oracle.py](../submissions/team3/tier05/oracle.py)。
新增 [合成等价测试](../tests/test_tier05_constant_folding.py)、
[冻结 release Oracle 夹具](../tests/fixtures/tier05_release_oracle.py) 及本报告和 JSON。
`tier05/solution.py`、Diffuser、完整字节变换接口、经典解密模块、其他九关、官方
Helper／数据／Checker／哈希／评分配置均保持基线内容。未合并 main、未创建 PR。

## 数学等价与电路变化

令 S 为双半字节 S-box，P 为公开位排列，R_i 为密钥左旋 3i，M 为不含轮常量的
公开 mask，d_i 为轮常量，c_i 为密文字节，b_0=Q、b_1=C。对任意密钥 k：

\[
P(S(c_i\oplus d_i\oplus M(R_i k)))=b_i
\iff M(R_i k)=c_i\oplus d_i\oplus S^{-1}(P^{-1}(b_i)).
\]

新电路仅在经典端计算右侧两个**公开常量**。量子端仍通过公开 `mask_gates`
中的 CX/CCX 在叠加态中计算密钥相关 mask，比较两个字节，并完整反计算。
它没有在经典端求解 mask 方程、枚举正式密钥或硬编码隐藏答案。
新 mask bit j 写入 `WORK_QUBITS[j]`；旧完整字节变换中吸收 PERM 的线路重标记
不能误用到这个未置换的比较常量上。旋转仍为 `(j-3*i) mod 10`，轮常量仅计入一次。

令 e_i(k) 为第 i 字节比较结果。第一次比较把 flag 从 0 写成 e_0 并清空 work；
第二次比较的精确 `H–MCX–H` 产生相位 `(-1)^(e_0 e_1)`；随后撤销第二个 mask
并逆执行第一次比较。新旧均严格实现

\[
|k\rangle|0^8\rangle|0\rangle
\longmapsto (-1)^{e_0(k)e_1(k)}|k\rangle|0^8\rangle|0\rangle.
\]

比较器继续使用精确 dirty MCX，恢复借用 key 位的值与相干相位；没有启用 RCCX、
`relative_phase` 或 `action_only`。这证明任意 key 叠加态张量零 work/flag 的
**承诺子空间上完全等价**，不声称在任意非零 clean-work 输入上全算子等价。
相同 Diffuser 保持该子空间，因此每轮归纳给出 25 轮末态及完整测量分布相同。
该证明不依赖唯一解假设，也不靠有限次测量恰好得到相同答案。

保留的运行契约：10 个搜索位 + 8 个 work + 1 个 flag，共 19 qubits；
10 classical bits；**25 个 Oracle + 25 个 Diffuser、128 shots、一次 Aer 调用**。
仍是 `q[j]→c[j]`，Qiskit 的 `c9…c0` 直接转整数，不反转。
每 shot 25 次逻辑查询，一次真实求解的 shot 加权查询数为 3,200。
只测得的候选会进入经典前缀检查，完整解密仍由原经典模块完成。

结构上，每轮省掉六次字节变换中的双 S-box 层，即 36 CCX + 24 CX；25 轮为
**900 CCX + 600 CX**。PERM 原本已是免费线路重标记，没有虚构额外 SWAP 节省。
实际净 CX 降幅必须由转译测量决定：本轮实测为 6,000，虽然恰与孤立 CCX 的
六 CX 换算吻合，仍不能把这种吻合当通用成本公式。

## 正式运行前的等价性测试

10 项新增测试及 2 项现有 `test_tier05_integration.py` 测试取得 PASS 证据。

- 用预先指定人工密钥生成 QC、仅 Q、仅 C、均不匹配四类人工密文；未读取正式
  `locked.json`。只对人工数据建立 1,024 个基态的参考相位标签，不做正式密钥搜索。
- 每类准备非均匀、含复相位并有 key 位纠缠的全支撑态，比较原版和优化版的全部
  1,024 个 clean-auxiliary 子空间振幅及解析基态相位，而非仅比较测得密钥。
- 检查零 work/flag 子空间概率和为 1、key 概率不变；QC 实例再接同一 Diffuser，
  对照解析振幅 `2*mean(amplitudes)-amplitudes`，验证一轮干涉与完整概率。
- 检查完整字节 API、Diffuser、19q/10c 布局、默认 25+25 块、测量连线、非法输入。
  原有集成测试另覆盖改名导入、前导零位序和完整 `QC-05: ` 前缀。

数值容差 `2e-10`。初批原版／优化版最大相位振幅差约 `1.81e-16`、概率差约
`1.44e-16`。定向 QC 复核中，相位振幅对解析值最大误差约 `8.87e-16`，
一轮振幅误差约 `1.39e-15`，零辅助子空间概率缺口约 `2.65e-14`。
比较没有按观测结果拟合全局相位，实际检查比「相差任意全局相位」更严格。

**测试修正记录：** 首次九项测试有一项夹具失败。Qiskit 的 `compose` 把后缀
Diffuser 的已知全局 π 相位合并到整条电路，因此更早的 `save_amplitudes` 已带上
这个后缀标量。测试改为仅移除明示的后缀相位元数据，未修改生产算法或放宽容差。
随后只复核受影响 QC 的旧／新两条人工电路，并补一项默认结构检查；六项定向
检查通过。初批其他六条已通过电路未重跑。最终十项各有通过证据，不宣称首次全绿。

人工 Aer 总计两次调用、8+2=10 条 19-qubit 电路，各 1 shot，最多一轮；
没有构造 19-qubit 完整矩阵，也没有为等价证明再模拟人工 25 轮。

## 同环境 Before／After 实测

环境：Linux、Python 3.12.14、Qiskit 2.6.1、Aer 0.18.2、NumPy 2.5.4、
PyYAML 6.0.3、psutil 7.2.2。Checker 所需的 PyYAML 按官方固定版本补齐。
两边实际送往 Aer 的电路均按同一官方配置评分：`rz,sx,x,cx`、优化级别 1、
转译种子 12345、全连接、无 initial layout。没有用展示电路或原生块数冒充指标。

| 官方基门指标 | release 基线 | 常量折叠 | 相对减少 |
| --- | ---: | ---: | ---: |
| 双比特门 | 21,150 | **15,150** | **28.3688%** |
| 门深，不含测量 | 33,055 | **29,503** | **10.7457%** |
| 总门数，不含测量 | 58,620 | **42,211** | **27.9922%** |
| 活跃 qubits | 19 | **19** | 0% |

Profile 在双方注入相同模拟器种子 2026；各一次 `solve()`、128 shots。
另用原始官方 Checker 分别做不注入种子的完整验证。生产代码的参数没有被改写。
双方 profile 与官方四指标逐项相同，仪表控制确认通过，所有资源状态均为 `ok`。

| 单次观测 | release 基线 | 常量折叠 |
| --- | ---: | ---: |
| Profile 完整 solve 秒 | 23.409 | 29.067 |
| Profile Aer 提交至 result 完成秒 | 23.217101 | 28.914796 |
| Profile 评分转译秒 | 0.267227 | 0.170513 |
| Profile 总墙钟秒 | 25.0273 | 30.3016 |
| Profile 采样进程树峰值 RSS MiB | 236.918 | 209.770 |
| 原始官方 Checker 的 solve 秒 | 23.739 | 20.577 |
| 官方验证采样进程树峰值 RSS MiB | 244.777 | 223.523 |

**没有证明模拟提速。** 此次配对 profile 中优化版更慢，官方未注入运行中更快；
都是单次观察，不能据此归因或选择性报告较好的一次。门数与深度的确定性改善、
RSS 的这次观测、运行时间的波动应分开解释，没有为追求较好时间反复运行。

Harness 每 20 ms 采样进程树 RSS 总和，可能漏掉短峰、重复计入共享页；不是精确
操作系统峰值。Profile 外部时限 120 秒、RSS 限额 1024 MiB；Aer 原限制仍为
512 MiB、两线程。原始官方求解和评分转译各限 120 秒，harness 的官方包装器
另给 370 秒外部总预算。全部在预算内，无超时或内存失败。

## 官方 Checker、改名目录和合规性

| 路径 | 真实执行电路 | 状态 | SHA-256 | 指标 | flags |
| --- | ---: | --- | --- | --- | --- |
| release 基线官方检查 | 1 | full | 匹配 | 有效、与 profile 一致 | 无 |
| 优化版官方检查 | 1 | full | 匹配 | 有效、与 profile 一致 | 无 |
| 优化版 `renamed-tier05-validation` | 1 | full | 匹配 | 同为 15,150／29,503／42,211／19 | 无 |

改名检查从相同不可变候选建立完整临时仓库，仅将 `tier05` 与
`toy_cipher_classical.py` 放入新团队目录，**删除该快照中的原 `team3`**，
再通过未改动的官方 CLI 检查；没有用同名目录或 symlink 掩盖固定路径依赖。
改名求解耗时 22.639 秒，CLI 墙钟 24.913700 秒。
原始 Checker 日志、临时电路和报告位于私有临时目录，退出时删除；
这里只保留安全白名单汇总，不输出密钥、原始 counts、密文、明文或原始错误消息。

本轮真实挑战共五次执行：双方 profile 各一次、双方官方检查各一次、候选改名一次；
基线 256 shots、候选 384 shots，均保持每次 128，未补采样或失败重试。
Checker 对 Tier 5 的 `oracle_calls` 字段为 `null`，不能把它解释成零查询；
25 次查询由未改动的构建器和新增结构测试验证，实际执行路径为真实 Grover 搜索。

官方允许按公开 Toy Cipher 构造可逆谓词；此次仅把已知目标通过公开双射逆映射，
仍以量子电路同时检查 QC、扩幅并测量。精确比较器、反计算和 Diffuser 均未更改，
无经典穷举、隐藏 Oracle 检查、答案硬编码或无关电路。
通过 Git 对象核对所有官方路径、其余九关和共享生产模块均与 release 一致，
因此未重复运行其他关卡。

## Harness 接受判定与剩余风险

保留 harness 原始 `INCONCLUSIVE` 和退出码 1。已逐项核对其余门槛：官方
full/hash、无 flags、资源预算、实际执行与仪表控制、两边编译设置、profile／官方
指标一致性、目标指标下降都成立；缺少的是其额外要求的双方至少十个配对种子
证据和 `reliability_reviewed` 标记。没有伪造、跳过或修改该门槛，也不把它误称
为 Checker 失败。本轮以严格相位等价证明、合成回归及请求的完整官方检查确认
这次局部优化；未追加二十次高成本真实求解来把统计标签改为 ACCEPT。

剩余限制：单次时间／内存观测并非稳定性能分布；有限样本不证明失败率为零；
理想 Aer 通过不代表噪声硬件表现。未实施 RCCX、减少迭代次数、修改 Diffuser、
增加缓冲或其他审计候选，避免混入改变测量分布的独立优化。

## 快照一致性与复现

Harness 不读取未提交修改。测试通过后，用临时 Git 索引建立不可变候选快照
`0b73a3bfc539624580ff6ea301d849b4e998bc04`；没有移动 release 或其他分支。
该快照包含唯一生产改动与两份测试文件，正式交付另加入本报告及 JSON。
JSON 的 `tested_source_sha256` 记录三份受测文件；提交前逐字节核对最终文件与
快照相同。Oracle SHA-256 为
`0bdff3317ddfe1e41e003795e13480e990a92728823c5c427ba030a2453b8b0c`。
复现时使用最终交付提交即可，不依赖临时快照引用长期存在。

从优化仓库根目录运行合成测试（会重新执行人工电路）：

```sh
python -B tests/test_tier05_constant_folding.py
python -B tests/test_tier05_integration.py
```

在原样获取上述 harness 的同仓库工作树中，以最终交付 SHA 替换 CANDIDATE_SHA：

```sh
PYTHONDONTWRITEBYTECODE=1 python -B benchmarks/circuit_benchmark.py \
  --baseline 868fb65e20c73a27bffc118f3617080df9cf2f8b \
  --candidate CANDIDATE_SHA --tier 5 --seed 2026 --official --rules-reviewed \
  --timeout 120 --memory-mb 1024 --output /private/path/tier05_comparison.json
```

这会再次执行四次真实求解，不能为刷新报告随意重跑。改名复现应按上节建立完整
临时快照、删原团队目录，再运行
`python -B tools/check_submission.py submissions/renamed-tier05-validation --out /private/path/checker`。
检查 JSON 中唯一被测 tier 为 5，且 `full`、`hash_ok=true`、指标有效、flags 为空。
