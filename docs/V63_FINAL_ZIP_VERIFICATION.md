# v6.3 最终 ZIP 独立核验 — Junqi Sheng

## 结论：INCONCLUSIVE

**原始归档、37个源码文件、缓存及十关功能验收全部通过；指定逐关复杂度基线未完全复现。** 本轮不签发“全部预期指标一致、可直接提交”的最终结论。批准ZIP保持原样，未重建、修复、归一化或重新压缩，也没有优化电路、提交比赛表单或修改发布分支。

新的官方 Checker 为 **10/10 FULL、10/10 SHA-256匹配、10/10有实际Aer电路记录、0 flags、0超时**。实测CX合计正确，但Tier 5、6、7的部分指标不同：实测深度和 **217,602**，预期217,625；实测总门数 **294,857**，预期294,982。差异已保留，没有用旧报告替换新结果。

本报告的INCONCLUSIVE仅指尚未满足此次指定的完整数值复现要求。当前没有ZIP损坏或功能错误的证据，不能据此重新生成批准ZIP。归档及功能通过与数值复现未完成须分别交接。

## 1. 固定来源与定位

- 私有仓库：`qsc032376-hash/quantum-cryptography-ten-locks`。
- 批准提交：`ce75c0721622d363e77912191a52a02c34f92472`。
- 既有独立审计：`5b86f71c058193ea0b94070d76524ecef2455fe7`，本轮使用新取得的归档和新执行结果独立核验。
- 本轮审计分支：`audit/v63-final-zip-verification`，仅增加审计报告、复现脚本与证据。
- 批准团队tree：`b965048fa4d7db33876b33c60e5a9e206085f1ee`。
- 批准ZIP Git blob：`723d19c562253b780d1ccd4586180b095d385707`。
- 仓库内精确位置：`drafts/ten-locks-team3-v6.3-rc.zip`。
- 实际核验的本地文件：`/workspace/work/v63-final-zip-audit/drafts/ten-locks-team3-v6.3-rc.zip`。
- 用户给出的Windows位置：`C:\Users\18658\Desktop\QH\v63-rc\drafts\ten-locks-team3-v6.3-rc.zip`。当前Linux执行器无法直接访问该Windows磁盘；本轮明确改从批准提交按文件名及指定SHA取得同一批准归档，不声称检查了Windows桌面目前的文件，也不声称该Windows路径可被Mac访问。

## 2. 原始字节与ZIP结构

| 检查 | 新核验结果 |
|---|---|
| 原始大小 | 101,354 bytes |
| 实际SHA-256 | `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94` |
| 与用户指定SHA一致 | 是 |
| 与批准提交中ZIP blob逐字节一致 | 是 |
| ZIP可打开 | 是 |
| `testzip()` | `None` |
| 预期成员数／实有成员数 | 37 / 37 |
| 与批准manifest的成员集合一致 | 是 |
| 重复条目、大小写冲突、危险路径、符号链接、加密条目 | 均无 |
| 37成员与批准源码blob逐字节一致 | 37 / 37 |
| 全十关入口、运行Python依赖及两份JSON缓存 | 完整 |
| Checker运行后原ZIP、解压成员、下载副本 | 原始字节仍一致 |

唯一归档根为 `team3/`。**应解压至官方仓库的 `submissions/`**，得到 `submissions/team3/`；不要再向 `submissions/team3/` 解压造成双重嵌套。批准交接文档对此指令正确，既有独立审计文字中另一处较含糊的目标路径没有被照搬。

逐成员完整名称、长度、原始SHA-256、批准Git blob及比较结果保存在 [archive-verification.json](v63-final-verification/archive-verification.json)。批准源码目录的39个文件中，归档按manifest仅省略两个开发验证文件：`tier01/test_solution.py`、`tier01/validate_quantum.py`；没有缺少运行模块。

## 3. Tier 9 / Tier 10缓存

| 成员 | 字节数 | 实际原始SHA-256 | 结果 |
|---|---:|---|---|
| `team3/tier09/public_operations.json` | 9,916 | `06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b` | 批准manifest匹配 |
| `team3/tier10/public_operations.json` | 156,086 | `b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6` | 指定canonical-LF哈希匹配 |

均直接读取ZIP成员原始bytes，CRLF序列数为0。没有重序列化JSON、转换行尾或改写缓存。此次门数差异不能归因于已经排除的缓存字节／换行差异。

## 4. 全新官方环境与执行

新克隆官方上游 `https://github.com/QuantumClub-OSU/Quantum-Cryptography-Challenge`，固定原始官方提交 `340e1ce18cafa69f4cea906f88f93741738dc0fa`。批准交接文档中的 `fce7c3950d06bb4d23e3c057b4625f901c396de4` 是团队文档合并提交，与该原始官方提交仅差 `docs/TIER01_THEORY.md`。本轮核对了 **76个官方工具／Helper／题目数据／配置等文件**，与批准提交相同。

- 全新官方工作目录：`/workspace/work/v63-fresh-official`；初始Git工作区干净，原先没有 `submissions/team3/`。
- 将原ZIP直接解压到上述目录的 `submissions/`，37成员再次逐字节验证。
- 未修改官方Checker、scoring config、Oracle、Helper、密文或提交代码；未改变模拟种子或评分级别。
- Python **3.12.14**，Qiskit **2.6.1**，Aer **0.18.2**，NumPy **2.5.4**，PyYAML **6.0.3**。
- 核心运行依赖匹配指定版本；matplotlib、pylatexenc、notebook、ipykernel未安装。静态导入预检及实际十关运行均表明这些可选绘图／Notebook组件不在本次运行路径中，未声称完整安装了所有requirements条目。
- Linux x86_64；OMP线程2、OpenBLAS/MKL线程1、Qiskit并行关闭。原评分basis、level 1、seed 12345及每阶段120秒限制保持不变；官方额外60秒启动宽限也未修改。
- 开始：2026-11-11T18:36:49.704918-05:00；结束：2026-11-11T18:40:22.331676-05:00（America/New_York）。
- 一次完整Checker墙钟 **212.627秒**，退出码0；20ms采样进程树峰值RSS **694.406 MiB**。采样可能漏峰值或重复计算共享页，不能视为精确物理内存峰值。

原样执行命令（报告在提交目录之外）：

```text
/workspace/work/tier01-venv/bin/python -I tools/check_submission.py submissions/team3 --out /workspace/work/v63-final-zip-audit/docs/v63-final-verification/checker
```

[官方原始JSON](v63-final-verification/checker/report.json)、[官方原始Markdown](v63-final-verification/checker/report.md)、[运行记录](v63-final-verification/execution.json)均保留。原始Checker命令未传`--sha`，因此其metadata显示commit未给定；批准提交、ZIP原始哈希和运行前后37成员摘要由外层独立证据绑定，没有修改Checker报告补填信息。实际Aer是经典模拟器执行量子电路，不是量子硬件实验。

## 5. 本轮实际十关指标

所有行均FULL、hash匹配、actual circuit execution=true、metrics=ok、flags=[]。

| Tier | CX | Depth | Total gates | 评分活跃qubits | solve秒 |
|---:|---:|---:|---:|---:|---:|
| 1 | 151 | 44 | 298 | 25 | 20.583 |
| 2 | 0 | 3 | 3 | 1 | 3.747 |
| 3 | 7,808 | 8,771 | 19,497 | 7 | 11.467 |
| 4 | 183 | 195 | 455 | 20 | 0.201 |
| 5 | 10,950 | 19,703 | 28,363 | 19 | 25.151 |
| 6 | 3,000 | 5,691 | 8,680 | 22 | 63.948 |
| 7 | 209 | 155 | 533 | 15 | 0.132 |
| 8 | 7,856 | 18,804 | 22,861 | 18 | 6.052 |
| 9 | 34,186 | 71,632 | 102,830 | 22 | 38.316 |
| 10 | 38,823 | 92,604 | 111,337 | 19 | 10.077 |
| 合计 | **103,166** | **217,602** | **294,857** | 不合计 | — |

Depth合计是十条被评分电路深度之和，不是一条联合电路深度。活跃qubits属于每关被评分的电路，不能把这些值相加当作设备规模。评分仍依官方规则选取solve实际送入模拟器的最大双比特门电路。

| 差异项 | 批准预期 | 本轮实际 | 实际−预期 |
|---|---:|---:|---:|
| Tier 5 total gates | 28,413 | 28,363 | −50 |
| Tier 6 depth | 5,715 | 5,691 | −24 |
| Tier 6 total gates | 8,752 | 8,680 | −72 |
| Tier 7 depth | 154 | 155 | +1 |
| Tier 7 total gates | 536 | 533 | −3 |
| Depth sum | 217,625 | 217,602 | −23 |
| Total gates sum | 294,982 | 294,857 | −125 |

全部十关的CX及评分活跃qubits匹配；其余七关四项指标均匹配。逐项比较、运行后字节复查及判定保存在 [comparison.json](v63-final-verification/comparison.json)。比较脚本对未完全匹配返回非零，未放宽严格数值匹配条件。

## 6. 差异调查与证据边界

没有重新运行整套Checker挑选结果。首次新Checker结果始终保留为本轮验收依据。

1. 批准提交中的 `docs/V63_INTEGRATION_REPORT.md` 已记载Tier 5历史28,363总门与集成环境28,413的差别；本轮与前者一致。其编译重放在当时环境中返回28,413，跨环境原因当时也未隔离。
2. `docs/V61_INTEGRATION_REPORT.md`、对应full-checker及baseline-diagnostics已记录Tier 6同源码得到5,691深度／8,680总门，与本轮完全相同；v6.2记录变回5,715／8,752。
3. Tier 7相同运行源码的历史指标已有209／153／527与209／154／536两种，本轮209／155／533未与批准值完全重现。
4. 上述历史报告的scoring-config/hash-file SHA、Qiskit/Aer版本一致。Python补丁版本和平台记录有所不同；不能因此宣称已证明Python、平台、浮点、线程或某个缺失可选包是原因。历史证据见 [historical-metric-context.json](v63-final-verification/historical-metric-context.json)。
5. 追加了有界的两次全新进程、相同配置、**仅构建／转译、不运行Aer**诊断。Tier 5完整单电路流程、Tier 6公开默认12轮构建、Tier 7第一条实际QPE构建都在两次中复现本轮数值。两次指标及count_ops稳定，未证明同环境随机漂移。Tier 6未重做测量校准，Tier 7未重建依赖私有测量值的第二条验证电路，故后二者明确是部分流程诊断。
6. 诊断中QPY输入序列化字节并不全部一致；没有检查或规范化opaque Oracle内部标识。因此不能声称相同序列化输入或据此证明编译器非确定性。未保存私有输入摘要、量子状态、测量字符串、密钥或明文。见 [compile-replay.json](v63-final-verification/compile-replay.json)。

**剩余事项：须独立确认这三关的编译环境／指标基线差异，才能将本次“预期逐关指标完全复现”判定改为通过。** 目前归档和十关解密已经验证成功；严格数值签核仍未完成。原因未定位时，不调整预期数字来制造通过，也不修改或重建批准ZIP。

## 7. Sicheng的获取方式

GitHub中已经存在这个精确ZIP，当前已授权连接账号实际重新下载了101,354字节，所得SHA与批准文件完全相同。使用固定提交链接：

- [下载页面：登录GitHub后点击Download raw](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ce75c0721622d363e77912191a52a02c34f92472/drafts/ten-locks-team3-v6.3-rc.zip)。
- [固定提交raw链接](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/raw/ce75c0721622d363e77912191a52a02c34f92472/drafts/ten-locks-team3-v6.3-rc.zip)（仍需私有仓库访问权限）。

Sicheng在Mac上可使用有该仓库访问权限的GitHub账号通过该页面下载，不依赖Windows磁盘路径。本轮验证的是当前连接账号的实际下载能力，**没有代登录或验证Sicheng本人账号权限**，也没有公开仓库、创建公开外链或发送文件给他。

额外保留的字节相同下载副本位于 `/workspace/outputs/v63-final-verification/ten-locks-team3-v6.3-rc.zip`，其SHA仍是 `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`。这是当前执行器中的副本，不把本地绝对路径冒称为Mac共享地址；真正跨平台交接入口是上面的私有GitHub链接。下载过程只解码API传输的base64，不解压重压、不重写归档。[下载证据](v63-final-verification/download-verification.json)。

Mac下载后可自行执行：

```text
shasum -a 256 ten-locks-team3-v6.3-rc.zip
```

应得到本文完整SHA；在新的官方仓库中将其解压至 `submissions/` 后复核。此次报告没有提交比赛表单。

## 8. 复现与交接

- `verify_archive.py`：先验证ZIP原始SHA；不符立即RELEASE_BLOCKED且不解压、不运行。匹配后逐成员对Git blob及manifest比较，并可向干净官方仓库安全解压。
- `run_checker.py`：仅调用未经修改的官方CLI一次，保留外部资源观测；不变更提交代码、评分参数或种子。
- `compare_results.py`：比较全部十关四项指标、功能字段及运行后原始字节。核心完整性／功能失败为RELEASE_BLOCKED；仅指定预期数值未复现为INCONCLUSIVE；全部一致才为ZIP_VERIFIED。
- `compile_replay.py`：范围受限的差异诊断，不是新量子成功记录或电路优化。
- [来源记录](v63-final-verification/reference-provenance.json)区分真正官方上游、批准集成提交及旧独立审计。新证据保存在独立审计分支；批准提交、ZIP、缓存、发布分支和其他Tier均不改动。

**精确文件已可获取，归档与功能已通过；按本次列出的全部预期指标，最终提交就绪结论仍为INCONCLUSIVE。**
