# v5 验证结果 · Tier 8 M15 集成

**已验证 v5 候选。** [独立 Tier 8 验收](TIER08_INDEPENDENT_ACCEPTANCE.md)得到 ACCEPT 后，从 `072adc8ce83e1e13f96812154b5b90d9a2915275` 精确引入 `submissions/team3/tier08/modular.py`。继续既有 `222903c` 工作分支，未移动冻结引用。下方保留原准备记录供追溯，以本节的最新实测结论为准。

## 来源与边界

冻结 v4 `73f4dbe330de3098acb368464d3f5606c30259f8`。团队目录相对 v4 仅上述 Tier 8 blob 不同；Tier 5 Oracle、Tier 9 生成器、Tier 10 量子电路和经典后处理均逐字节相同。Tier 9/10 使用的公开 permutation_table 函数未改。源树（整包执行前的暂存快照）为 `d1010f9eca0a71564fe312dc40c4e6eee868bf2e`；官方 inputs/tools 和两份报告的配置及 hashes.txt 摘要均相同。

## 整包验证

从同一次生成的 ZIP 字节解压到干净临时官方根，team3 改名 team_v5_review，原目录不存在；先在十个独立进程导入入口，再运行原版 `python -I tools/check_submission.py submissions/team_v5_review --out <输出目录>`。十关均实际运行电路、full、SHA-256 匹配、指标有效且 flags=[]，未出现内存错误或超时。[官方完整报告](evidence/v5/report.json) · [资源记录](evidence/v5/resources.json)

| Tier | 状态/哈希/指标/flags | 双比特门 | 深度 | 总门数 | 活跃位 | 记录电路数 | solve 秒 | 进程树峰值 MiB |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | full / match / ok / [] | 151 | 44 | 298 | 25 | 1 | 5.979 | 688.3 |
| 2 | full / match / ok / [] | 0 | 3 | 3 | 1 | 2048 | 0.524 | 225.4 |
| 3 | full / match / ok / [] | 7,808 | 8,771 | 19,497 | 7 | 24 | 4.843 | 581.9 |
| 4 | full / match / ok / [] | 183 | 195 | 455 | 20 | 1 | 0.122 | 184.5 |
| 5 | full / match / ok / [] | 15,150 | 29,503 | 42,211 | 19 | 1 | 5.375 | 275.5 |
| 6 | full / match / ok / [] | 3,000 | 5,883 | 9,534 | 22 | 2 | 10.465 | 306.1 |
| 7 | full / match / ok / [] | 230 | 271 | 763 | 15 | 2 | 0.109 | 177.8 |
| 8 | full / match / ok / [] | 42,810 | 123,320 | 130,190 | 18 | 1 | 13.360 | 483.4 |
| 9 | full / match / ok / [] | 89,075 | 235,048 | 263,601 | 21 | 1 | 8.841 | 292.2 |
| 10 | full / match / ok / [] | 82,804 | 218,263 | 245,153 | 19 | 1 | 2.066 | 288.8 |

完整 Checker 墙钟 **71.328 秒**，进程树 RSS 峰值 **688.26 MiB**，按约 50 ms 采样。RSS 可能重复计共享页、漏掉瞬时峰值。环境 Windows 11、Python 3.12.10、Qiskit 2.6.1、Aer 0.18.2、OMP 两线程。

| 各关独立评分电路之和 | v4 | v5 实测 | 减少 |
|---|---:|---:|---:|
| 双比特门 | 248,321 | 241,211 | 7,110 |
| 逐关深度之和 | 633,141 | 621,301 | 11,840 |
| 总门数 | 729,600 | 711,705 | 17,895 |
| 逐关活跃位之和 | 167 | 167 | 0 |

其他九关的四项指标与 v4 实测逐项一致。以上是独立评分电路的汇总，不是单条电路的深度或同时所需的比特数。整包通过及单关的十个种子均不能保证其他种子、噪声环境或硬件上的表现；简洁分仍取决于参赛队伍的相对指标。

## 提交草案与回退

[v5 ZIP 草案](../drafts/ten-locks-v5-team3-draft.zip) SHA-256：`48e5023081ea14d6b26315895daa7c9e36ff88d4c29c2b09ccf697fba0f319bc`。CRC、单一 team3/ 根、27 个 Python 文件、各文件与 Git blob 字节一致；与 v4 草案相比，条目清单相同且仅 Tier 8 modular.py 内容不同。已检查常见凭据/私钥标志和匹配官方明文哈希的字符串常量；此静态检查有范围限制。未上传比赛平台。v4 冻结引用及 v4 ZIP 原样保留。

---

## 历史档案：222903c 时点的准备方案（已由上述验收更新）

### v5 准备状态 · Tier 8

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
