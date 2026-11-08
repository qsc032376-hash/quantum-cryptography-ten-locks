# 最终提交清单 · v5 已冻结，最终材料待齐

**决定：代码候选通过；当前 ZIP 暂不可作为完整比赛作品上传。** 截至 2026-11-09，重建草案与冻结版完全一致。缺少团队 README 和 WRITEUP；展示交付与提交负责人仍待确认。本清单沿用[既有提交清单](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/f9ae3b4fa123b0f7f91bdc04babaae67019db544/docs/FINAL_SUBMISSION_CHECKLIST.md)，更新为 v5。提交与展示要求见[官方 README](../README.md#submission)、[CHALLENGE](../CHALLENGE.md#what-you-deliver) 和[评分规则](../SCORING.md)。

## 冻结依据与 ZIP

- [x] 远端 `release/ten-locks-v5-verified` 精确指向 **41c7c6775b8fc499c2acdd878b4829bd17e1210d**。与[整包受测源树](evidence/v5/resources.json) `d1010f9eca0a71564fe312dc40c4e6eee868bf2e` 的全部差异均为交付文档、证据及草案；算法、团队依赖、题目输入和 Checker 字节相同。审计文档单独保存在 integration/v5-release-audit。
- [x] 核对既有[官方十关报告](evidence/v5/report.json)：10/10 full，所有 hash_ok 和 circuit_executed 为真，四项指标有效，flags 全空。十个独立评分电路的双比特门合计 **241,211**、逐关深度之和 **621,301**、总门数 **711,705**。沿用原测试，没有重跑量子求解。
- [x] Tier 8 的种子 800–809，基线与候选各 10/10 PASS，每次实际转发对应种子并完成 64 shots，官方哈希均匹配。配对 JSON 和独立 ACCEPT 都保存在冻结提交。[独立验收](TIER08_INDEPENDENT_ACCEPTANCE.md) · [基线](evidence/v5/tier08-baseline-seeds.json) · [候选](evidence/v5/tier08-candidate-seeds.json)
- [x] [代码 ZIP 草稿](../drafts/ten-locks-v5-team3-draft.zip)：`drafts/ten-locks-v5-team3-draft.zip`；SHA-256 **`48e5023081ea14d6b26315895daa7c9e36ff88d4c29c2b09ccf697fba0f319bc`**。按冻结提交的 Git blob、固定 ZIP 元数据重建，压缩包逐字节一致。CRC、路径、逐项内容验证通过。单一 team3/ 根，5 个根级共享模块、10 个 tierNN/solution.py、12 个配套 Python 文件；未发现缓存、虚拟环境、验证器、官方数据或额外条目。
- [x] 官方 requirements 的八项固定版本均匹配，pip check 通过。在只有官方依赖、原样官方代码和解压团队包的临时根，改名后分十个独立进程导入；每关的 solve、build_circuit 都可调用。结合原全量 Checker 覆盖真实运行路径。静态扫描未发现常见凭据、私钥标记或匹配官方明文哈希的字符串常量；其范围限于这些检测规则。复验：在审计分支使用 Python 3.12 和官方依赖运行 `python docs/release-audit/verify_v5.py`，无需执行 solve。

## 主要优化及审查状态

各格按双比特门 / 深度 / 总门 / 活跃位排列，比较的是对应优化前后。

| Tier | 来源提交 | 官方实测变化 | 验收范围 |
|---|---|---|---|
| 5 | `804b9dd349a40edd834fd06dfb2ceb09c6658bfc` | 21,150 / 33,055 / 58,620 / 19 → 15,150 / 29,503 / 42,211 / 19 | 公开常量折叠；五组配对种子与人工独立 ACCEPT。[验收记录](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ab96767/docs/TIER05_INDEPENDENT_ACCEPTANCE.md) |
| 8 | `072adc8ce83e1e13f96812154b5b90d9a2915275` | 49,920 / 135,160 / 148,085 / 18 → 42,810 / 123,320 / 130,190 / 18 | 精确 M15 dirty MCX；十组配对种子、相位与借位复原复核，独立 ACCEPT。[证据](TIER08_INDEPENDENT_ACCEPTANCE.md) |
| 9 | `f86a4422c1a609da9b24079cc916d69437d67af7` | 117,739 / 316,820 / 349,949 / 21 → 89,075 / 235,048 / 263,601 / 21 | 无辅助位共享控制；开发侧十组配对和 ACCEPT。审计交接及复演已完成，所查记录中未见独立签核。[交接](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/85b5ced/docs/TIER09_INDEPENDENT_REVIEW_HANDOFF.md) |
| 10 | `7c9d03238835a8b02fbf489440440059cad4ee13` | 107,168 / 287,674 / 317,957 / 19 → 82,804 / 218,263 / 245,153 / 19 | 无辅助位扇出与 QFT 重接线；开发侧 ACCEPT，全包复核通过，未见单独的独立签核。经典鲁棒性来自 `44766baa3f9ba5859cc32f45fc53feaf8807af4b`，不计为电路降幅。[原实验](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/7c9d032/docs/TIER10_FULL_OPTIMIZATION_RESULT.md) |

这些是理想 Aer 的测量和固定基门下的评分结果。Tier 8 基线/候选不同试验的耗时方向不一，Tier 9、10 在已记录配对中求解变慢。门数下降不能证明硬件加速；有限种子不能保证零失败，最终相对简洁分取决于其他团队。Tier 3/6 的后续优化维持在各自开发分支，不改变冻结候选。

## 提交时间、平台与责任

- [ ] **截止时间**：必须在 **2026-11-13 12:00 美国东部时间**（纽约 EST，UTC−05:00）之前上传，即 **北京时间 2026-11-14 01:00**。以表单记录的时间为准。
- [ ] **提交负责人：TBD**。团队指派后核对最终文件和摘要，由负责人使用 Google 账号打开[官方提交表单](https://docs.google.com/forms/d/e/1FAIpQLSeYZrd6v9SxdsHyUpgYfwjhpEHVlhk7JjN5nYaVMcpo3uj7FQ/viewform)。官方 README 指定上传一个以团队文件夹为唯一根目录的 ZIP。本次未取得登录后的表单字段，实时文件限制、回执形式和入口可用性须由负责人确认。
- [ ] **材料阻断项**：补齐 team3/README.md 并链接 team3/WRITEUP.md；后者含十关说明、测量如何恢复答案、资源计数和扩展性分析。准备短展示，确认呈现方式与讲解人。已有数学分析和展示讲稿可作为撰写依据，仍需核对冻结版数字及实际附件。[团队分析与讲稿](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/tree/215cf43/docs)
- [ ] **上传前**：在独立最终包加入经确认的文档，保持 27 项源码与冻结版逐字节相同。核对唯一 team3/ 根、README 链接、完整材料、CRC、文件清单与秘密扫描；记录最终文件名和**新的 ZIP SHA-256**。如出现无法解释的差异，停止标记为可提交；代码若变更，另行验证。
- [ ] **提交后**：实际状态为未上传，无回执。负责人应在私有位置记录最终 SHA-256、文件名、提交人、实际表单时间和时区；保存成功页或收到的邮件/回执（如有）。若未显示成功，确认表单状态再决定是否重传。只评分最近一次提交，重传会重置平分判定时间。

## 回退

| 版本 | 保留的准确提交 | 代码草案 SHA-256 |
|---|---|---|
| v4（首选回退） | `release/ten-locks-v4-verified@73f4dbe330de3098acb368464d3f5606c30259f8` | `bf2ab288aae4ac92e942544a12fa97e299d9432908ed6b12465db00220ae8160` |
| v3 | `integration/optimized-v3-candidate@04feb70e52f5522aa2976ca9c7df2e48f27f3cce` | `ac21a9ebc6c804f558395680b86b3b49b88c14e92a5396d1ce7ef2e9cab289b0` |
| v2 | `integration/optimized-v2-candidate@0cd8adc025e89fa190836e9295f6b5ffa482e17a` | `9e4fb149f67898e737ebf88a197b2df22a0035cafa015ede3c86383e1f31f49a` |
| v1 | `release/ten-locks-v1@868fb65e20c73a27bffc118f3617080df9cf2f8b` | `62351aca20d8fac24723aaf1418620e60b425db0d3c5f28a020da63d82bc3e3a` |

若选回退，取[冻结 v4 草案](../drafts/ten-locks-v4-team3-draft.zip)，核对 v4 的摘要和 Checker 记录，使用与 v4 指标一致的说明材料重新组包。保留所有冻结历史；不要将回退代码草案未经补齐就上传。
