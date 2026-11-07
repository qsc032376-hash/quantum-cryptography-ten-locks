# Tier 6：多解 Grover 实现与测量记录

Junqi Sheng，`feature/quantum-circuits`。测试基准提交
`a84fde85279e269a456a6280c6876cb543ea66d4`。
Python 3.12.14 / Qiskit 2.6.1 / Aer 0.18.2。

**量子搜索与公开 Q 前缀验证 PASS；完整 solve、checksum 和明文哈希验证待经典模块集成。**
仅新增本目录文件，Tier 1–5、官方数据/Helper/评分工具均未修改。
机器汇总见 [quantum_validation.json](quantum_validation.json)。

## 公开谓词与布局

搜索空间 N=2^14。官方只保证约 64 个候选，未提供精确标记数 M。
Oracle 仅判断首字节 `Q`，不使用完整 `QC-06: `、checksum 或明文哈希标记。
官方没有提供已完成 Oracle，本实现从公开 `mask_gates(14)` 构造。

首字节的旋转与轮常量均为零。设 C0 为公开密文首字节，则
`decrypt_byte(C0,0)==Q` 等价于
`mask(k,0)==C0 XOR inverse_sbox_layer(inverse_permute(ord('Q')))`。
因此只对公开常量做逆变换，再量子计算 mask、比较、反计算。
这省去量子 S-box 的开销，不在经典端求解密钥，也不遍历密钥空间。

主电路为 **22q：key q0–13、work q14–21**；work[7] 兼作相位目标，
并非另加独立标志位。比较常量后，以 H→精确 MCX7→H 实现八位 MCZ，
借用 5 个 key 位作为 dirty 辅助。比较与 mask 随后完整反计算。
校准电路额外使用 q22 作为测量标志，共 **23q**；精确 MCX8 借 6 个 dirty key。
Qiskit dirty 合成设 `relative_phase=False, action_only=False`，恢复借位相干性。

Diffuser 为 `2|+><+|−I`，在 key 上执行 H/X、全 14 位受控 Z、逆 X/H，
并设全局 pi 相位。MCX13 借 6 个已归零 work 位；辅助数取自实际合成宽度。
主搜索只测量 qj→cj（j=0…13）；结果串 c13…c0 直接 `int(bits,2)`，不反转。

## 用实际量子校准选择迭代数

先执行一次 Grover，再额外计算 Q 谓词至初始零 flag，测量该 flag。
相位 Oracle 已清空的 work 不能直接用来估计标记概率。
令 theta=asin(sqrt(M/N))，校准概率 p1=sin²(3 theta)。在官方“小 M”
承诺支持的 `0<M/N<1/4` 分支，theta_hat=asin(sqrt(p_hat))/3。
迭代数取最接近 `pi/(4 theta_hat)-1/2` 的整数；不是沿用 Tier 5 的 25 轮。

实际校准 **2048 shots，72 次 flag=1**，p_hat=0.03515625。
估计 M=**64.6791**，Wilson 95% 区间经单调变换后为 **[51.4203,81.2486]**。
据此选择 **12 轮**，估计成功率约 0.999999；这是估计值，不是已知真实概率。
区间给出的保守预测下限约 0.963897。

条件于 M 不超过统计上界，用优惠券收集的联合上界
`P(遗漏某个标记候选) <= M exp(-marked_draws/M)` 规划采样。
本次目标为 608 个成功测量，计划 640 shots。此界依赖理想均匀标记分布与
统计上界有效；Wilson 95% 区间加条件遗漏 5% **不等于整体 95% 覆盖保证**。
测得 64 个候选也不能据此证明 M 恰为 64 或所有候选已覆盖。

本地上限为 24 轮、一次校准、最多两批搜索、累计最多 1024 搜索 shots。
只有成功测量数不足时才允许一次补测；预估剩余时间不够时停止补测并报告。
零/全校准命中、估计不稳定、资源超限或模拟异常均不盲目重试。
这些是本地预算；官方未另设本 Tier 的 shots/查询硬上限。

## 实际结果、查询数与资源

| 指标 | 实测 |
|---|---:|
| Aer 调用 | 2：1 次校准 + 1 次搜索；无补测 |
| 搜索测量 | 640 shots |
| 不同实测 / Q 合格候选 | 64 / 64 |
| Q 合格测量 | 640 / 640，100% |
| 经典首字节检查 | 仅 64 个实际测得候选，各检查一次 |
| 校准 / 搜索耗时 | 8.089679 / 38.591682 秒 |
| 完整量子恢复耗时 | 46.688446 秒 |
| 评分转译耗时 | 0.156108 秒 |
| 验证进程峰值 RSS | 231.574 MiB |

有限样本 100% 命中不代表真实概率为 100%。本次达到成功测量数目标，
没有用经典枚举、密钥硬编码、隐藏 Oracle 结构或真实状态向量恢复候选。

校准每 shot 包含 **1 次相位 Oracle + 1 次 bit 谓词**；搜索每 shot 为
**12 次相位 Oracle**。按 shots 加权，相位查询总数为
2048+12×640=**9728**，额外 bit 谓词查询 **2048**，总谓词查询 **11776**。
按两条不同电路各执行一次的逻辑块口径为 13 个相位块、1 个 bit 块；
Aer 可复用末端状态采样，但不改变上述算法查询口径。反计算门计入门成本。

## 实际执行电路的评分指标

按官方基门 `rz,sx,x,cx`、优化级别 1、种子 12345 转译，再对实际执行电路
做评分转译。无额外量子执行。依据最大双比特门数、再按深度，选中主搜索电路。

| 指标 | 校准电路 | 单条评分主电路 |
|---|---:|---:|
| 总 / 活跃 qubits | 23 / 23 | 22 / 22 |
| Classical bits | 1 | 14 |
| Two-Qubit Gate Count | 436 | **3000** |
| Gate Count，不含测量 | 1326 | **9534** |
| Gate Depth，不含测量 | 846 | **5883** |
| Circuit Depth，含测量 | 846 | 5884 |
| 总操作数，含测量 | 1327 | 9548 |

这是单条电路指标，不乘 shots。Simulator 使用 statevector、2 线程、512 MiB
状态内存预算；22/23q 的裸双精度状态向量约 64/128 MiB。
验证器为执行和评分转译分别设置 120 秒 SIGALRM；原生库调用可能延迟处理信号，
不是操作系统硬隔离。本次两阶段均在预算内，无超时或内存不足。

## 测试与复现

**28 项测试 PASS**：25 项人工/mock 接口测试（0.024 秒），3 项人工 Aer 测试
（7 条 22/23q 电路，20.147 秒）。没有为刷新报告重复真实搜索。

- 人工公开 mask 碰撞验证多个 Q 状态同时被标记；非匹配态验证相对相位。
- 人工相干态的选定振幅验证 dirty 借位、key 与工作位恢复；bit Oracle XOR/反计算。
- Diffuser 在计算基态和均匀态的符号与辅助清理。
- 14-bit 位序、测量频数、去重、跨批仅检查一次、查询统计与只检查已测候选。
- 校准反演、置信区间、迭代选择、shots/批次/时间上限及异常不重试。
- 经典接口返回类型、多 checksum 命中交哈希确认，以及缺模块时明确失败。

人工测试只用合成数据，不读取实际锁文件。其选定振幅检查没有用于真实搜索。
仓库根目录复现命令（第二条会执行真实搜索并更新汇总，不应无故重复运行）：

```bash
python -B -m unittest submissions.team3.tier06.test_oracle submissions.team3.tier06.test_solution
python -B -m submissions.team3.tier06.validate_quantum --private-output-directory /path/outside/repo/tier06-private
```

原始主搜索 counts、候选整数与统计已保存在仓库外 `tier06-private` 目录中，
目录权限 0700、独占新文件权限 0600。仓库和聊天只包含汇总，不包含实际位串、
候选密钥、完整明文或真实状态向量。验证器拒绝把私有记录写进仓库。

## 交接与剩余事项

`recover_candidates() -> list[int]` 执行真实量子流程，返回去重后的 14-bit 整数。
`recover_candidates_with_diagnostics()` 额外返回私有 counts 与安全汇总；调用方不得
把候选或 counts 写入公开日志。`build_circuit()` 默认 12 轮仅供图示，真实运行
始终传入校准选定的次数。

只读参考 Sicheng 的 `docs/TIER06_THEORY.md`，blob
`988a3b0a93ea464379456b8dd7861c6cc2582fda`，未合并数学分支。
参考已验证 Tier 5 设计，但没有修改 Tier 5 文件。
Youyang 的 `toy_cipher_classical.py` blob 为
`21727250e81dfd98ffb745e192904a3d5a9afec8`，本分支仍未包含它，也未复制或重写。

已核实 `filter_candidates(6,candidates,ciphertext_hex,expected_checksum)` 返回
`list[str]` 明文，不带密钥、不去重、不检查 Q，也不判唯一性。本量子接口已检查 Q。
`solve()` 预留调用上述模块，再对所有返回明文调用官方 `is_correct(6,text)`，
只有唯一哈希确认明文才返回。缺模块时抛 `NotImplementedError`，不会伪造通过。
实际 checksum、完整明文和官方哈希尚未验证；需要 Junrui 集成后实测完整 `solve()`。
按照本轮要求，不采纳 README/理论中“checksum 必定唯一”的简化说法。
