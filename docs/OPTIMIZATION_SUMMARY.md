# Ten Locks · v3 发布证据

**建议将 v3 交独立复核。** 开发侧十关的改名整包 Checker 均为 full、SHA-256 匹配、实际执行电路、metrics_status=ok、无 flags。门指标的可归因改善集中在 Tier 5 与 Tier 9。Tier 10 改善的是经典处理的健壮性。候选尚未上传，Tier 9 独立意见待回填。[复核交接](TIER09_INDEPENDENT_REVIEW_HANDOFF.md)

## 源码边界

| 版本 / 改动 | 精确提交 | 已核对的范围 |
|---|---|---|
| v1 冻结回退 | `868fb65e20c73a27bffc118f3617080df9cf2f8b` | 第一版十关实现 |
| v2 候选回退 | `0cd8adc025e89fa190836e9295f6b5ffa482e17a` | 相对 v1，团队目录仅改 Tier 5 oracle.py 与团队根 dh_classical.py |
| Tier 5 Grover | `804b9dd349a40edd834fd06dfb2ceb09c6658bfc` | 公开常量折叠；v3 oracle.py 与该来源的 Git blob 同为 c5ef0d8b6e9a32477910b612ba757c1084deca2f |
| Tier 10 经典处理 | `44766baa3f9ba5859cc32f45fc53feaf8807af4b` | 参数校验、有界噪声方程处理；v3 dh_classical.py 与来源 blob 同为 c9cc0571ac3be89002e6807f6dc68e653108aee5 |
| Tier 9 受控模乘 | `f86a4422c1a609da9b24079cc916d69437d67af7` | 合并相邻同控制翻转；开发侧实验记录提交 `17df36d1c31cd441cd3bd840157caadd3062cada` |
| v3 验证候选 | `04feb70e52f5522aa2976ca9c7df2e48f27f3cce` | 相对 v2，运行代码只改 tier09/solution.py 和新增 tier09/shared_controls.py；其余两项差异为 v3 报告和 ZIP |

v3 整个团队子树与 f86a442 一致；其余层（含 Tier 10 复用的 tier09/modular.py）、requirements.txt、common、题目输入、hashes.txt 和官方工具均与 v2 一致。复查命令：`git diff --name-status 0cd8adc 04feb70`、`git diff --exit-code f86a442 04feb70 -- submissions/team3`。此次审计只增加证据和复验文档。

## 十关官方实测

各格按 **双比特门 / 深度 / 总门数 / 活跃位** 排列。v1 为冻结版历史官方证据（本次不重跑）；v2、v3 取自上次集成在同一 Windows 主机、同一配置下分别执行的两份完整 Checker JSON。Tier 7 的历史总门数 760 与同机的 763 有差异，v2/v3 同机一致，不能将该差异归因于算法。v1 来源：[Tier 1–7](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/868fb65/docs/SUBMISSION_STATUS.md) · [Tier 8–9](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/868fb65/docs/TIER08_TIER09_INTEGRATION.md) · [Tier 10](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/868fb65/docs/TIER10_INTEGRATION.md)。同机原件：[v2](release-audit/evidence/v2-control.json) · [v3](release-audit/evidence/v3-checker.json)。

| Tier | v1 历史实测 | v2 同机实测 | v3 同机实测 |
|---|---|---|---|
| 1 | 151 / 44 / 298 / 25 | 151 / 44 / 298 / 25 | 151 / 44 / 298 / 25 |
| 2 | 0 / 3 / 3 / 1 | 0 / 3 / 3 / 1 | 0 / 3 / 3 / 1 |
| 3 | 7,808 / 8,771 / 19,497 / 7 | 7,808 / 8,771 / 19,497 / 7 | 7,808 / 8,771 / 19,497 / 7 |
| 4 | 183 / 195 / 455 / 20 | 183 / 195 / 455 / 20 | 183 / 195 / 455 / 20 |
| 5 | 21,150 / 33,055 / 58,620 / 19 | 15,150 / 29,503 / 42,211 / 19 | 15,150 / 29,503 / 42,211 / 19 |
| 6 | 3,000 / 5,883 / 9,534 / 22 | 3,000 / 5,883 / 9,534 / 22 | 3,000 / 5,883 / 9,534 / 22 |
| 7 | 230 / 271 / 760 / 15 | 230 / 271 / 763 / 15 | 230 / 271 / 763 / 15 |
| 8 | 49,920 / 135,160 / 148,085 / 18 | 49,920 / 135,160 / 148,085 / 18 | 49,920 / 135,160 / 148,085 / 18 |
| 9 | 117,739 / 316,820 / 349,949 / 21 | 117,739 / 316,820 / 349,949 / 21 | 89,075 / 235,048 / 263,601 / 21 |
| 10 | 107,168 / 287,674 / 317,957 / 19 | 107,168 / 287,674 / 317,957 / 19 | 107,168 / 287,674 / 317,957 / 19 |

| 各层评分电路之和 | v1 | v2 | v3 |
|---|---:|---:|---:|
| 双比特门 | 307,349 | 301,349 | 272,685 |
| 逐层深度之和 | 787,876 | 784,324 | 702,552 |

这些是十个单独评分电路的汇总，不是一条可执行联合电路或最终比赛分数。Tier 5 比 v1 少 6,000 个双比特门（28.37%）、3,552 层深度、16,409 个总门，活跃位不变。Tier 9 比 v2 少 28,664 个双比特门（24.35%）、81,772 层深度、86,348 个总门，活跃位不变。Tier 5 有五组配对种子和人工独立 ACCEPT；Tier 9 有十组开发侧配对种子、完整测量到哈希验证和等价测试。[Tier 5 独立证据](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ab96767/docs/TIER05_INDEPENDENT_ACCEPTANCE.md) · [Tier 9 证据及其独立复核入口](TIER09_INDEPENDENT_REVIEW_HANDOFF.md)

## 时间、统计与完整性

- Tier 9 v2/v3 同机 solve 为 **4.881 / 8.618 秒**，实验首轮 Aer 作业为 **4.752 / 8.258 秒**。计分依据固定基门转译，Aer 运行的是原生门表示；评分电路变简单与理想模拟变慢同时发生。整包 v3 墙钟 70.218 秒，50 ms 采样进程树 RSS 峰值约 688.34 MiB，可能漏峰或重复计共享页。[资源和文件清单](release-audit/evidence/v3-run.json)
- 有限种子来自理想模拟器，不能外推所有种子、真实噪声、零失败率或硬件加速。比赛简洁分还取决于其他队伍。Tier 5 独立人工验收与 Tier 9 开发侧验收是不同状态；本次交接演练不是 Youyang 的独立结论。
- [原十关 Checker JSON](release-audit/evidence/v3-checker.json) SHA-256 为 `e97a27a21ff12cf446797c4d3539d94031a970e5aff3d3081e5d32b7d4ba5d7c`；[原 Markdown 表](release-audit/evidence/v3-checker.md) 为 `c30bdd399592df4a803b87c2333d7ac5702919dc9ee2b6ec57f2c2b90460d6c7`。原调用未传 --sha，因此原件的 sha 字段为空；不改写原件。用同期 run.json 的源树 `73e1e3fc71372a4edd2e72bbcffd6560d66b8bec`、26 个文件摘要与候选 Git 内容建立对应。Checker 记录的配置 SHA-256 为 `25b15b1e42852fd10d41cb1cccb5e25f4063382924ecdb41b15130df80f4915a`，官方 hashes.txt 文件 SHA-256 为 `46b4e257799432591738f7b62dd4e35b096beef8cd07c56c612fb9e2187cf48f`。十关 hash_ok 均为 true，无需暴露任何解密结果。

## 提交包与回退

[v3 ZIP](../drafts/ten-locks-v3-team3-draft.zip) 的 SHA-256 为 `ac21a9ebc6c804f558395680b86b3b49b88c14e92a5396d1ce7ef2e9cab289b0`。从准确提交的 Git blob 复用[既有打包器](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/2ebf7a1f64bf5450ca862d2e6dba2eaf7718e1d0/tools/package_release_draft.py)，仅在临时副本设定候选 SHA、预期数量、源码根和 Unix ZIP 头。运行 `python docs/release-audit/verify_zip.py` 已重建字节完全相同的 ZIP，校验了 CRC、全部相对路径和每项源码字节。

包仅一个 `team3/` 根，含 5 个共享 .py 文件（classical_keystream、dh_classical、rsa_classical、tier07_classical、toy_cipher_classical），以及 tier01/ 至 tier10/ 的 10 个 solution.py 和 11 个配套模块。共 26 个 Python 文件，无测试、验证器、缓存、环境、报告或官方输入。此前已做静态凭据及明文字面值检查，并从 ZIP 改名导入十关；本次按字节验证同一内容。[整包集成记录](OPTIMIZED_V3_CANDIDATE.md)

本次未上传。v1/v2 的冻结提交与历史 ZIP SHA-256 均保留，分别为 `62351aca20d8fac24723aaf1418620e60b425db0d3c5f28a020da63d82bc3e3a` 和 `9e4fb149f67898e737ebf88a197b2df22a0035cafa015ede3c86383e1f31f49a`。当前草案是运行代码包；正式提交仍需团队补齐 README、write-up 和演示材料，并复核最终交付物。
