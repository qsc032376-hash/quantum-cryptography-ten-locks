# v5 准备状态 · Tier 8

**建议：保留 v4 作为已验证提交候选；Tier 8 独立验收 PENDING。** v5 工作分支从准确的 v4 创建，本提交仅添加准备记录，运行源码与 v4 相同。没有 v5 整包 Checker 结果、实测汇总或新 ZIP。继承的 drafts/ten-locks-v4-team3-draft.zip 仍是 v4 草案。

## v4 冻结与回退

新远端引用 `release/ten-locks-v4-verified` 指向 `73f4dbe330de3098acb368464d3f5606c30259f8`。本次核对 v4 资源记录的 Git 源树 `7d80eb9e4c451040387e0fbbdc8b42a0fb739607` 与该提交：差异仅为结果文档、两份证据文件和 ZIP；所有运行源码、锁定输入及评分工具相同。核对原版十关记录，每关均为 full、实际执行电路、哈希匹配、指标有效、flags=[]。ZIP 的 SHA-256 与原记录一致，CRC、单一 team3/ 根、27 项清单及每个文件的源码字节均通过核验。本次未重复执行昂贵的量子求解。[Checker](evidence/v4/report.json) · [受测树与 ZIP 摘要](evidence/v4/resources.json) · [冻结草案](../drafts/ten-locks-v4-team3-draft.zip)

| 回退版本 | 保留的远端引用 / SHA | ZIP SHA-256 |
|---|---|---|
| v1 | release/ten-locks-v1 · 868fb65e20c73a27bffc118f3617080df9cf2f8b | 62351aca20d8fac24723aaf1418620e60b425db0d3c5f28a020da63d82bc3e3a |
| v2 | integration/optimized-v2-candidate · 0cd8adc025e89fa190836e9295f6b5ffa482e17a | 9e4fb149f67898e737ebf88a197b2df22a0035cafa015ede3c86383e1f31f49a |
| v3 | integration/optimized-v3-candidate · 04feb70e52f5522aa2976ca9c7df2e48f27f3cce | ac21a9ebc6c804f558395680b86b3b49b88c14e92a5396d1ce7ef2e9cab289b0 |
| v4 | release/ten-locks-v4-verified · 73f4dbe330de3098acb368464d3f5606c30259f8 | bf2ab288aae4ac92e942544a12fa97e299d9432908ed6b12465db00220ae8160 |

v1–v3 摘要沿用原审计记录，本次核实远端指针保持原提交；未重建或覆盖历史草案。

## Tier 8 开发侧证据

候选 `optimization/tier08-mcx@072adc8ce83e1e13f96812154b5b90d9a2915275`。相对 v4 的 Tier 8 唯一差异是 `submissions/team3/tier08/modular.py`：至少四控制时以完整精确 Maslov dirty MCX 替换 Iten 分解，六控制所借的 dirty 位从四条降为两条；公开置换表、幂次和位序保持原样。已用 Git blob 的 SHA-256 重算候选 JSON 中的全部 tested_source_sha256；生产模块摘要为 `e8df9fa1f17be2be06ce1706407c5c50da13ec7d3a6068dfc53cda9ded8aab7f`，与实际受测快照记录一致。[原实验报告](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/072adc8/docs/TIER08_OPTIMIZATION_RESULT.md) · [结构化证据](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/072adc8/docs/TIER08_OPTIMIZATION_RESULT.json)

| 官方 Tier 8 指标 | 基线（亦与 v4 的 Tier 8 一致） | 候选 |
|---|---:|---:|
| 双比特门 | 49,920 | 42,810 |
| 深度 | 135,160 | 123,320 |
| 总门数 | 148,085 | 130,190 |
| 活跃位 | 18 | 18 |

本次读取并断言了三份已有官方结果：基线、候选及改名候选均为单关 full、hash_ok=true、metrics_status=ok、flags=[]，各记录一次实际电路。原作者的八项合成测试已通过；六控制纠缠输入的抽样振幅检查不等价于穷尽全算子。两种计时观测呈相反方向，无法证明稳定模拟提速。

## 接受条件与后续步骤

截至 2026-11-09，已 fetch 并检查远端分支、回归/验收提交及绑定候选或受测快照的报告。能核实的是 Junqi 的开发侧记录：Harness 给出 INCONCLUSIVE，明确缺少至少十组配对种子及 reliability_reviewed。未找到对应独立回归或签核；不能用单个种子 profile、改名 full 或其他 Tier 的验收替代。状态 **PENDING**，不代表 Checker 失败。

1. 收到针对该准确实现的独立报告后，核对基线与候选源码身份、至少十个相同种子、实际送入 Aer 的种子、每次哈希/状态、失败或超时、资源预算和人工验收结论。
2. 只有证据满意后，才从 072adc8 取上述 modular.py 一项。核对 v4 的 Tier 5、9、10 改进保持原样，特别核实 Tier 9/10 复用的 permutation_table 接口和行为。
3. 在真正集成后，从独立 v5 ZIP 解压到改名团队目录，执行完整官方 Checker，核对十关 full、hash_ok、有效指标、空 flags 和实际资源；检查 ZIP 清单、导入、安全及 SHA-256。
4. 如果其他九关不变，双比特门合计的**规划值**为 248,321 − 7,110 = 241,211。此值不能登记成 v5 实测成绩；只有上一步通过，才推荐新的整包候选。
