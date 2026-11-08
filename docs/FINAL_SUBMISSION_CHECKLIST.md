# 最终提交清单：v2 源码已验证，提交包尚未完成

**状态：BLOCKED。** 现有 ZIP 缺少官方要求的团队 README 和 `WRITEUP.md`，不能当作完整提交包。先完成下列材料并重建包；未获明确授权前不得上传。[就绪审计](V2_RELEASE_READINESS.md)说明已验证范围及非阻断风险。

官方来源：[仓库 README 的 Submission 与 Presentation](../README.md#submission)、[CHALLENGE 的交付与展示要求](../CHALLENGE.md#what-you-deliver)、[SCORING 的评分与平分规则](../SCORING.md)。已核对上游 `QuantumClub-OSU/Quantum-Cryptography-Challenge` 的 `main@340e1ce18cafa69f4cea906f88f93741738dc0fa`，与此处提交要求一致。下列打勾项表示现有证据，未勾项须由团队完成；建议性操作不冒充官方规则。

## 时间与责任

- [ ] **官方截止：2026 年 11 月 13 日中午 12:00（美国东部时间，America/New_York，EST / UTC−05:00）之前。** 表单时间是官方时间；不要把本地 Git 时间当作提交时间。
- [ ] **提交负责人：本任务未指定，待团队确认。** 负责人负责核对最终包、在获得用户明确授权后以 Google 账号打开官方[提交表单](https://docs.google.com/forms/d/e/1FAIpQLSeYZrd6v9SxdsHyUpgYfwjhpEHVlhk7JjN5nYaVMcpo3uj7FQ/viewform)并上传。现在尚未上传。
- [ ] 团队确认建议：负责人提交后核对表单实际显示的成功状态、所提交包版本和时间；如表单提供确认记录则保存到私有位置。官方未在仓库保证特定收据或邮件形式。
- [ ] 官方允许截止前重新提交，但只评分最新提交，重新提交会重置平分判定时间；决定重传前核对影响。

## 源码与 Checker 证据

- [x] 已验证源码提交：`integration/optimized-v2-candidate@0cd8adc025e89fa190836e9295f6b5ffa482e17a`。不能将审计分支的新文档提交误写成该源码提交。
- [x] 既有本地官方 Checker：Tier 1–10 全部 `full`、明文 SHA-256 全部匹配、评分指标完整、flags 为空；详见 [v2 集成报告](OPTIMIZED_V2_CANDIDATE.md)。原 Checker 报告未填写 commit 字段，后续已将实际检查团队副本中 27 个跟踪文件与该 commit 逐字节比较。
- [x] 当前草稿 ZIP 的十个 `tierNN/solution.py` 均包含 `solve()` 和 `build_circuit()`；正式提交仍须保持已验证代码及官方的实际 Aer 运行规则。
- [ ] Tier 10 历史独立验收报告：**EVIDENCE_NOT_ARCHIVED**。见 [证据说明](V2_RELEASE_READINESS.md#来源与既有验证)；这与上述后续 v2 全量 Checker 集成证据分开。

## 官方 ZIP 结构与材料

- [ ] 官方要求 ZIP 仅包含一个团队文件夹（当前为 `team3/`），其下有十关方案与所需团队共享模块；官方仓库的题目、`common/`、Helper 和 Checker 不要复制到团队包内。
- [ ] **补齐 `team3/README.md`，并链接 `team3/WRITEUP.md`。** 官方要求把方案和说明放在团队目录，并从团队 README 链接说明。
- [ ] **完成 `team3/WRITEUP.md`：每关一个章节及扩展性章节。** 按官方要求说明测量结果及频率、密钥提取、量子电路和经典后处理；不要在仓库中写入真实密钥、明文、凭据或私人日志。如所需证据可能泄密，应先由团队确认私密、经授权的呈现方式，不得编造结果。仅模板不等于完成的说明。
- [x] 现有源码草稿 `ten-locks-v2-team3-draft.zip`：25 个 Python 文件，结构与源码字节、隔离导入及常见凭据特征检查已通过；SHA-256：`9e4fb149f67898e737ebf88a197b2df22a0035cafa015ede3c86383e1f31f49a`。**该摘要只适用于现有不完整草稿。**
- [ ] 在不修改 `0cd8adc` 十关源码的前提下，把经过团队确认的 README 与 WRITEUP 加入独立最终包；重新检查包仅有 `team3/` 一个根目录、链接正确、源码与 `0cd8adc` 一致，并记录最终 ZIP 的新 SHA-256。任何不同源码必须另行验证，不能沿用现有 Checker 结论。
- [ ] 排除 `.venv`、`__pycache__`、`.ipynb_checkpoints`；不要加入凭据、隐藏密钥、真实明文、测量日志、无关开发文件或仓库其他目录。官方要求工作保密、不公开源码、不发 PR；此前对私有仓库的只读检查显示仓库为 private，正式提交前仍需确认访问范围。
- [x] v1 回退草稿 `ten-locks-v1-team3-draft.zip` 保留，SHA-256：`62351aca20d8fac24723aaf1418620e60b425db0d3c5f28a020da63d82bc3e3a`。它也是源码草稿，缺少团队说明材料，不能未经补齐就当作完整回退提交包。

## 展示与演示准备

- [ ] 官方要求短展示：每个已完成 Tier 说明锁隐藏的内容、方案选择与原理、带 qubit/门数的电路图、测量及密钥提取方式、经典成本；未完成的 Tier 说明尝试及阻塞点。
- [ ] 官方要求最后展示扩展性：从玩具规模到真实密钥规模的变化及所需硬件；分析还需包含真实硬件运行**或**噪声讨论。硬件本身为可选项。
- [ ] 团队内部准备建议：指定展示负责人，核对图表来自已验证版本，预演讲解并准备适当的演示或备选材料。仓库没有规定必须现场运行 demo、演示时长或单独上传演示文件，不将这些假设写成官方要求。当前展示材料及负责人状态待团队确认。
