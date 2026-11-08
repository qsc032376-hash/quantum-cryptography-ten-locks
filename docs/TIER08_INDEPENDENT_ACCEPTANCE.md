# Tier 8 独立验收 · Junrui Yu

**结论：ACCEPT。** 对冻结 v4 和 Junqi 的准确候选各运行十个种子，另独立运行两端的 profile 与原版官方 Checker。两端均有十项真实 Aer 运行、十次哈希匹配及一致的配对资源预算，Harness 的最终建议为 ACCEPT。本结论只适用于以下源码和理想 Aer 环境。

| 对象 | 提交或值 |
|---|---|
| v4 基线 | `73f4dbe330de3098acb368464d3f5606c30259f8` |
| Junqi 候选 | `072adc8ce83e1e13f96812154b5b90d9a2915275` |
| Harness | `ab9676749e00da904d0b8076811a2407d3b7205f`，未改代码，按提交导出临时隔离树 |
| 官方配置 Git blob | `4f502a2b80ba79134f70db490997b4f959a6cf0c` |
| 环境 | Windows-11-10.0.26200-SP0，Python 3.12.10，Qiskit 2.6.1，Aer 0.18.2 |
| 预算 | 每个回归 worker 120 秒、1,536 MiB、每侧总限 1,250 秒；OMP 两线程；每次相同的 64 shots |

## 配对和随机种子

两侧均以相同次序使用预先选定的 800–809。仅在测试进程内，Harness 包装 AerBackend.run，把 seed_simulator 传给原 Aer 方法，记录实际传入值和完成的 job。逐项核对每次 requested=forwarded、单次电路、完成一个 job、64 shots，并以官方 hash_line 与 load_hashes 比对；生产源码和默认种子未改。两侧的官方输入、Checker、评分配置、requirements、Tier 8 solve/order 及相关解密依赖一致。记录的 RSS 是约 20 ms 采样进程树之和，可能重复计共享页、漏掉瞬时峰值。

| 实际注入种子（两侧） | 状态（v4 / 候选） | 官方哈希 | solve 秒 | 采样峰值 MiB | 异常 |
|---:|---|---|---|---|---|
| 800 | PASS / PASS | match / match | 13.384 / 13.303 | 422.8 / 406.6 | 无 / 无 |
| 801 | PASS / PASS | match / match | 13.295 / 13.329 | 434.1 / 401.4 | 无 / 无 |
| 802 | PASS / PASS | match / match | 13.339 / 13.282 | 436.3 / 399.9 | 无 / 无 |
| 803 | PASS / PASS | match / match | 13.347 / 13.236 | 435.3 / 400.2 | 无 / 无 |
| 804 | PASS / PASS | match / match | 13.372 / 13.168 | 434.4 / 401.5 | 无 / 无 |
| 805 | PASS / PASS | match / match | 13.211 / 13.253 | 434.1 / 400.8 | 无 / 无 |
| 806 | PASS / PASS | match / match | 13.235 / 13.757 | 431.7 / 400.4 | 无 / 无 |
| 807 | PASS / PASS | match / match | 13.210 / 13.513 | 435.9 / 398.8 | 无 / 无 |
| 808 | PASS / PASS | match / match | 13.237 / 13.777 | 436.6 / 397.4 | 无 / 无 |
| 809 | PASS / PASS | match / match | 13.218 / 13.239 | 433.8 / 401.1 | 无 / 无 |

原始逐次记录：[v4](evidence/v5/tier08-baseline-seeds.json) · [候选](evidence/v5/tier08-candidate-seeds.json)。实际回归命令为 `python benchmarks/cross_seed_regression.py --ref REF --tiers 8 --seeds 800 801 802 803 804 805 806 807 808 809 --timeout 120 --total-seconds 1250 --memory-mb 1536 --output OUT`，REF 为上表任一提交；Harness 脚本来自指定工作树。额外比较使用同一 Harness 的 circuit_benchmark.py、相同两端、--tier 8 --seed 808 --official、相同 worker 限制，并传入两个 regression 文件和人工审查标记。

## 等价性与比赛规则

四控制及以上由完整精确 Iten 改用完整精确 Maslov dirty MCX；更小模板和公开模乘表保持原样。六控制构造从四条借位降至两条，仍为 12 个计数位、6 个 work 位。对任何控制、目标和借位的叠加，目标翻转由相同谓词决定，借位及其相干性均复原；没有 clean 初态假设。未进入新模板的两条线保持恒等。

- 独立重跑候选的 8 项合成测试。逐元素复矩阵、逆映射和 padding；人工 Shor 复振幅及边际概率；12 个指数块、q[j] → c[j]、逆 QFT、初态、采样设置与基线一致。冻结测试夹具的 Git blob 与 v4 的 modular.py 相同。
- 另对真实六控制 M15 模板（9 个局部量子位，512 列）构造完整复算子。对每列：低六控制全 1 时只翻转第 6 位，两个高借位原样；目标元素应为 +1，其他元素应为 0。没有拟合全局相位。最大复数误差 3.77e-15，低于 1e−9。这也验证了任意叠加、非零/纠缠借位的恢复；没有构造整关稠密算子。[测试记录](evidence/v5/tier08-equivalence.json)
- 源码审查确认仍构造完整公开受控 Gray 模乘、真实 Aer 相位估计，以测量后的连分数及有界处理取得经检验的阶，再作 gcd、RSA 和官方哈希检验。公开置换循环仅用于综合；没有从周期裁剪电路、硬编码结果、试除或经典分解替代。

## 官方比较

两侧均为 full、哈希 match、实际执行电路、metrics_status=ok、flags=[]；评分转译使用相同官方配置。实测双比特门 **49,920 → 42,810**，深度 **135,160 → 123,320**，总门 **148,085 → 130,190**，活跃位 **18 → 18**。[本轮独立官方与 profile 比较](evidence/v5/tier08-comparison.json)

十组成功是有限样本，不能证明零统计失败率；模拟器时间与内存依赖主机，不能据此推断硬件加速。这里的 ACCEPT 是 Tier 8 单关结论，整包以单独的 v5 Checker 结果为准。
