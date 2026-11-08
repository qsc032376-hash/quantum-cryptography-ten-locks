# Tier 9 · N=77 受控模乘综合实验

| 对象 | Git 提交 |
|---|---|
| v2 基线 | `0cd8adc025e89fa190836e9295f6b5ffa482e17a` |
| 被测候选 | `f86a4422c1a609da9b24079cc916d69437d67af7` |
| 电路审计 | `5390daffd586e60c8c48f7808c1e276284899a49` |
| Benchmark Harness | `ab9676749e00da904d0b8076811a2407d3b7205f` |

## 变更与等价性

基线按公开模乘表逐行消元，将置换编译为正控制 X 门。Tier 9 的 14 个相位位分别控制公开幂次，7 个 work 位保存模乘结果。原方案没有专用干净辅助位。Tier 10 也依赖旧生成器，因此只在 Tier 9 的 solution 中接入新生成器，旧 modular.py 原样保留。

在消元序列内仅合并**相邻且控制掩码完全相同**的翻转。相同目标出现偶数次相消。其余目标任选一个枢轴 p，令 F 为从 p 到其余目标的 CNOT 扇出。以 F、受控 X(p)、F 的逆替代对每个目标重复的 MCX。控制条件没有使用任何目标线。条件为零时扇出完全抵消；为一时 p 反转，第二次扇出使其他目标也各反转一次。门均是正实置换矩阵，各输入列的相位都是 +1。任意相干叠加、与其他寄存器的纠缠均保持。枢轴可处于任意输入态，不需要干净初态或复原额外工作位。单控制组保留直接 CX。

- **全域检查**：14 个实际控制块各验证 256 列，包括控制关闭、所有合法 work 输入和 77–127 的 padding 恒等。逐门检查原语类型、正控制和零全局相位，然后将列映射与公开模乘公式比对。未构造完整 21 位电路的稠密算子。
- **相干检查**：N=15、两个公开底数、4 个相位位和 4 个 work 位。基线和候选的完整复振幅及相位寄存器边际测量分布逐项相同（绝对容差 1e−12），实测映射保持 q[j] → c[j]。另通过原有 Tier 9 合成数据 Aer → RSA → 哈希集成测试。
- **合成变化**：计入外部相位控制，原 2–7 控制 MCX 数量为 234/658/1125/1266/924/357；新数量为 145/299/630/844/805/357，新增 2,968 个单控制 CX。相位制备、IQFT、实际测量、采样预算、基于测量恢复阶和 RSA 处理沿用同一基线。
- **辅助位对照**：局部试验比较 Qiskit 原生 MCX 和 `synth_mcx_1_clean_kg24`。在 4/5/6/7 控制时，孤立原语转译后的 CX 分别为 36/82/122/170 和 18/24/30/36。在 clean=0 的所有输入列上比较完整复振幅，并检查 clean=1 子空间泄漏，最大误差 <6e−15。该局部试验未执行整关，无法按模板乘法预测整关分数；审计的 100,709 CX 亦是估算。此次保留实测改善且不增加位数的方案。

## 同配置实测

Windows 11 build 26200；Python 3.12.10、Qiskit 2.6.1、Aer 0.18.2。两次快照使用同一官方配置 blob `4f502a2b80ba79134f70db490997b4f959a6cf0c`：rz/sx/x/cx，全连接，优化级 1，transpiler seed 12345。Harness 记录 solve 实际送往 Aer 的电路，再按官方函数转译。两端 profiling 使用 simulator seed 909。每次 profiling 边界为 120 秒、2,600 MiB。

| 指标 | v2 | 候选 | 改变 |
|---|---:|---:|---:|
| 双比特门 | 117,739 | 89,075 | −28,664（−24.35%） |
| 深度 | 316,820 | 235,048 | −81,772（−25.81%） |
| 总门数 | 349,949 | 263,601 | −86,348（−24.67%） |
| 活跃位 | 21 | 21 | 0 |
| 评分转译时间（秒，首轮 profile） | 1.132 | 0.836 | −0.296 |
| 进程树采样峰值 RSS（字节，首轮 profile） | 289,296,384 | 237,047,808 | −52,248,576 |
| Aer 作业耗时（秒，首轮 profile） | 4.752 | 8.258 | +3.506 |

计时和内存为本机一次配对观测；内存按约 20 ms 间隔采样。固定基门评分改善，但状态向量模拟原生门的用时增加。公开置换表仍随 work 位数指数增长，本实验针对题目的小模数。

## 复验入口

在候选工作树根运行：

```text
python -m unittest discover -s tests -p test_tier09_shared_controls.py -v
python -m unittest tests.test_tier08_tier09_integration.ShorIntegrationTests.test_tier09_aer_to_rsa_and_hash
```

将 Harness 提交检出到同仓库的另一工作树。从候选根分别用其 `benchmarks/cross_seed_regression.py` 跑两个 SHA，参数 `--tiers 9 --seeds 900 901 902 903 904 905 906 907 908 909 --timeout 120 --total-seconds 230 --memory-mb 2600`，分别指定 `--ref`、`--output`。再运行其 `benchmarks/circuit_benchmark.py`，指定上表两 SHA 为 baseline/candidate，`--tier 9 --official --seed 909 --timeout 120 --memory-mb 2600`，传入两个 regression JSON 及审查标记。该工具调用原版 check_tier，仅评 Tier 9。

## 正确性、隔离与风险

两版本均对 900–909 这十个种子逐一完成一次 64-shot Aer 采样、阶恢复、非平凡互补因子验证、RSA 解包和官方明文哈希比对；每组 10/10 PASS。基线 solve 为 4.823–5.102 秒，候选为 8.245–9.005 秒。样本没有覆盖所有可能种子，原方案的有限采样失败风险仍存在。

另在临时干净目录放入官方 common、tools、tier09、hashes.txt，将团队文件只放入 submissions/renamed_team，未放 team3。提交内容为 tier09 的 solution、两个模乘模块，以及相对导入所需的 classical_keystream、rsa_classical、tier07/qpe 和 tier08 的 order、modular。运行官方 tools/check_submission.py 后仅有 Tier 9 被发现，得到 full、hash_ok=true、一次实际电路、metrics_status=ok、flags=[]，四项门指标与表中候选一致。无密钥、因子、阶或明文写入本报告。

其他层采用源码与导入关系核对：从基线到被测候选的改动仅涉及 Tier 9 的一个导入、一份新生成器和一份独立测试。Tier 10 引用的 tier09/modular.py 逐字节不变；其他 Tier 的提交文件、官方评分器、配置和挑战数据也相同。此次未重新执行其他九层。

## Decision · ACCEPT

两套未改动的官方 check_tier 均返回 full、SHA-256 match、一次 Aer 电路、有效指标且无 flags。带官方检查的第二轮 profiling 重现全部门数；基线/候选评分转译用时 1.167/0.828 秒，采样峰值 RSS 为 292,327,424/252,026,880 字节。原团队名、改名打包、配对多种子和等价测试共同支持采用此 Tier 9 候选。Harness 综合结论为 ACCEPT；最终比赛简洁分仍取决于其他队伍。
