# Tier 5 Grover 集成验证

基线：`integration/tier01-tier04-stable@8622fe9`。可逆 Oracle 和量子搜索来自 `a84fde8`，Toy Cipher 经典模块原样取自 `d4f561d`。量子算法保持不变；集成仅修复了固定团队目录名的导入，并在 `solve()` 返回前补上完整的 `QC-05: ` 前缀检查（包含空格）。

| 官方 Checker | SHA-256 | 双比特门 | 深度 | 总门数 | 活跃 qubit |
| --- | --- | ---: | ---: | ---: | ---: |
| full | 匹配 | 21150 | 33055 | 58620 | 19 |

官方 Checker 在临时改名的团队目录中真实执行一次 Tier 5，录得 1 条实际运行的电路。该路径只提交 1 个 Aer 批次，固定 128 shots，并在成功返回前核对测量频数之和为 128；转译前构建器要求恰好 25 个外层相位 Oracle 块。因此每 shot 25 次逻辑查询，整批 3200 次。Checker 的 `oracle_calls` 对 Tier 5 为 `null`，查询计数来自构建与执行路径的检查。官方 Tier 5 无一次调用上限。

本地 Python 3.13.9、Qiskit 2.6.1、Aer 0.18.2。`solve()` 用时 16.854 秒；整条 Checker 命令墙钟时间 18.53 秒，macOS `/usr/bin/time -l` 报告峰值 RSS 约 252.8 MiB。评分指标有效，无超时、内存错误、`no metrics` 或复核标记。

只测量 10 个密钥位，`q[j] → c[j]`，直接把高位在左的 `c9…c0` 转为整数；完整解密由 `decrypt_tier5(k, ciphertext_hex)` 执行。运行中未打印或持久化密钥、counts 或明文。

Junqi 的 23 个合成预检通过；仅在内存中将旧接口测试的模拟明文补上新要求的前缀。另有 2 个集成回归用例通过，覆盖改名导入、前导零位序和缺空格或错误前缀。Tier 1–4 的实现、共用密钥流模块和官方输入均与稳定基线一致，复用四关 `full` 的验证证据。

目前无需 OSC。剩余风险是评分电路较深，理想 Aer 成功和本机耗时不能代表噪声硬件表现；本轮只进行一次真实验证。

复现：将 `submissions/team3/tier05/{solution.py,oracle.py}` 和 `submissions/team3/toy_cipher_classical.py` 按原层级复制到临时改名团队目录，再运行 `python -B tools/check_submission.py <renamed-team-dir> --out <private-report-dir>`；合成回归为 `python -B tests/test_tier05_integration.py`。
