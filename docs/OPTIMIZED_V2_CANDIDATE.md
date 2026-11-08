# Optimized v2 候选集成与验收

**建议作为下一版提交候选，尚不是正式 release。** 从冻结版 `release/ten-locks-v1@868fb65e20c73a27bffc118f3617080df9cf2f8b` 出发，仅引入以下两个文件，并逐字节核对各自来源：

- Tier 5：`submissions/team3/tier05/oracle.py`，来自 [`optimization/tier05-oracle@804b9dd`](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/commit/804b9dd349a40edd834fd06dfb2ceb09c6658bfc)。公开常量折叠减少可逆 Oracle 的门；密钥相关运算仍在量子电路中。独立复核及五组种子证据见 [Tier 5 独立验收记录](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ab9676749e00da904d0b8076811a2407d3b7205f/docs/TIER05_INDEPENDENT_ACCEPTANCE.md)。
- Tier 10：`submissions/team3/dh_classical.py`，来自 [`optimization/tier10-classical-robustness@44766ba`](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/commit/44766baa3f9ba5859cc32f45fc53feaf8807af4b)。增加公开参数检验和有界噪声方程处理。任务指定该提交已经独立验收；提供的源码提交中没有单独的验收报告，因此此处引用来源提交，不将本次集成测试称为那份独立验收记录。

没有整体合并开发分支。Tier 1–4、6–9 核心实现、Tier 10 的量子电路及 `solve()`、官方题目与 Checker 均与 v1 逐字节相同。Tier 5 合成构造检查得到 25 个 Oracle 块。Tier 10 `solve()` 仍运行双寄存器量子电路，并只把经过公开关系验证的完整模数见证传入共享接口；通用经典模块对部分方程允许有界候选处理，不能把它当作对任意参数无枚举的保证。

## 十关官方 Checker 与评分对照

在隔离的改名团队目录 `team_v2_review`，使用未修改的 `tools/check_submission.py` 完整运行一次。十关均为 `full`、SHA-256 匹配、实际运行电路、`metrics_status=ok`，flags 全空；无超时或内存错误。v1 列复用 [Tier 1–7](SUBMISSION_STATUS.md)、[Tier 8–9](TIER08_TIER09_INTEGRATION.md) 和 [Tier 10](TIER10_INTEGRATION.md) 的既有官方证据；v2 列是本次实测。格式：双比特门 / 深度 / 总门数 / 活跃 qubits。

| Tier | v1 官方指标 | v2 官方指标 | v2 求解秒数 |
| --- | --- | --- | ---: |
| 1 | 151 / 44 / 298 / 25 | 151 / 44 / 298 / 25 | 10.210 |
| 2 | 0 / 3 / 3 / 1 | 0 / 3 / 3 / 1 | 0.355 |
| 3 | 7,808 / 8,771 / 19,497 / 7 | 7,808 / 8,771 / 19,497 / 7 | 4.539 |
| 4 | 183 / 195 / 455 / 20 | 183 / 195 / 455 / 20 | 0.104 |
| 5 | 21,150 / 33,055 / 58,620 / 19 | 15,150 / 29,503 / 42,211 / 19 | 13.920 |
| 6 | 3,000 / 5,883 / 9,534 / 22 | 3,000 / 5,883 / 9,534 / 22 | 28.800 |
| 7 | 230 / 271 / 760 / 15 | 230 / 271 / 760 / 15 | 0.048 |
| 8 | 49,920 / 135,160 / 148,085 / 18 | 49,920 / 135,160 / 148,085 / 18 | 32.907 |
| 9 | 117,739 / 316,820 / 349,949 / 21 | 117,739 / 316,820 / 349,949 / 21 | 5.882 |
| 10 | 107,168 / 287,674 / 317,957 / 19 | 107,168 / 287,674 / 317,957 / 19 | 1.554 |

Tier 10 本次正式运行记录 1 条电路；另做一次定向 `worker_solve`，与此前保存的 v1 实际运行电路记录对比，规范化后的 QPY 文件字节完全相同。完整 Checker 总墙钟 110.350 秒；进程树 RSS 以 50 ms 采样的最大总和约 643.22 MiB（不保证捕捉瞬时峰值，且共享内存可能重复计算）。环境为 macOS arm64、Python 3.13.9、Qiskit 2.6.1、Aer 0.18.2，CPU 两线程，外部进程树上限 2048 MiB。

## 依赖、打包和边界

Tier 5 / Tier 10 合成集成测试共 4/4 通过；额外人工参数测试覆盖离峰错误方程、非最小阶和子群外参数。改名团队副本中，十关分别以共享 DH 模块先/后导入检查，共 20/20 通过，确认本次进程中的 `classical_keystream` 与 `rsa_classical` 来自该副本。由于新 DH 模块使用顶层模块名，此检查不保证已被其他团队同名模块污染的长期进程也无冲突。

复用 v1 打包脚本，对已验证的 v2 Git 树生成本地 `ten-locks-v2-team3-draft.zip`：仅一个 `team3/` 根目录、25 个必要 Python 文件，无缓存、虚拟环境、报告、官方数据或测试验证脚本。隔离解压后校验 CRC、路径及 25 个文件与候选树字节相同，改名后十关和共享模块导入 10/10 通过。ZIP SHA-256：`9e4fb149f67898e737ebf88a197b2df22a0035cafa015ede3c86383e1f31f49a`。v1 回退 ZIP 保留且 SHA-256 仍为 `62351aca20d8fac24723aaf1418620e60b425db0d3c5f28a020da63d82bc3e3a`。ZIP 未上传；结构和导入预检不等于对解压 ZIP 重新跑全量 Checker。

一次理想 Aer Checker 和有限合成/跨种子测试不证明零失败率，也不代表噪声硬件的可靠性；现有 v1 和 Tier 5 的跨种子证据不能直接推出此 v2 在所有种子下的表现。正式提交前应在资源预算内继续独立跨种子回归，并保留 v1 回退。
