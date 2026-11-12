# v6.3.1 Documentation Fix 独立发布审核

**结论：RELEASE_APPROVED。** 本签字批准下述确切 ZIP 进入团队提交流程。新归档、源文件、缓存及一次全新官方 Checker 均通过独立核验；文档主要算法与最终版本相符。三处非阻断的文字/引用问题完整披露，不将它们当成已核实事实，也不为修正文案擅自重打包。

审核时间：2026-11-11T20:58:24.095457-05:00（America/New_York）。工作分支：`audit/v631-independent-release-junqi`。

## 1. 批准对象和字节证据

- 新 ZIP 源提交：`2fe40b2d096d87875244d5ccbb8a76ef979ac499`。
- 路径：`drafts/ten-locks-team3-v6.3.1-docs.zip`，大小 **100,796 bytes**。
- 实测原始 SHA-256：`4f1b2de8c7b554bed75319ab7f965937bad85906aa11a26172f5573dc24dfb52`。
- ZIP Git blob：`0ca1f87911fe4bdcd6475c0d60502b64a494390e`。
- 对照原批准 v6.3：`ce75c0721622d363e77912191a52a02c34f92472`，ZIP SHA `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`。

新 ZIP 打开正常，`testzip()` 为 None，37 个唯一成员，成员集合/顺序与原版一致。没有危险路径、重复、symlink 或加密条目。归档根目录为 `team3/`，正确提取位置是官方仓库 `submissions/`。

只有 `team3/README.md` 和 `team3/WRITEUP.md` 的原始内容变化；**33 个 Python 文件和 2 个运行 JSON，共 35 个运行文件逐字节不变**。所有 37 个成员均与新提交对应 source blob 相同；37 行 manifest 也独立重算匹配。

| 缓存 | 原始字节数 | 实测 SHA-256 |
|---|---:|---|
| Tier 9 public_operations.json | 9,916 | `06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b` |
| Tier 10 public_operations.json | 156,086 | `b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6` |

Tier 10 缓存 CR=0、LF=15,484；没有 JSON 重序列化或换行归一化。完整逐成员 SHA、source blob OID、CRC 和路径结果见 [archive-comparison.json](v631-independent-audit/archive-comparison.json)。

## 2. Junrui 的完整证据及其来源边界

新 ZIP 提交本身不含新 Checker 报告。后续直接子提交
`24b3c53181e184050973528903fd31abcc7f36b1` 增加 `V631_FULL_CHECKER.md` 与 `V631_RELEASE_REVIEW.md`，ZIP blob 未变。我们只读获取并保存这两份证据的原始 Markdown 与 source hash。

逐项解析十行：均 FULL、hash match、实际电路执行 yes、metrics ok、flags 空，合计 **103,166 / 217,625 / 294,982**，与用户给出的结果吻合。此前记录中的“等待独立签字”是审核门槛未完成，不是执行失败。

但该提交没有新运行的原始 JSON、实际环境清单和资源日志，因此不能仅凭该 Markdown 独立证明全部历史进程细节。本轮补跑提供了该新 ZIP 的独立机器证据，并未重建 Junrui 当时的进程或环境细节。旧版 JSON 未冒充新版测试。

来源：[prior-checker-evidence-review.md](v631-independent-audit/prior-checker-evidence-review.md)、[结构化来源索引](v631-independent-audit/prior-checker-evidence.json)。

## 3. 本轮独立全新 Checker

从官方上游 `340e1ce18cafa69f4cea906f88f93741738dc0fa` 创建独立目录，将经过 SHA 验证的原 ZIP 直接解压。执行未修改的：

```text
python -I tools/check_submission.py submissions/team3 --out <audit>/checker
```

未调整官方 120 秒阶段上限、评分配置、求解器 seed 或代码；只计划并执行一次完整运行，没有重试/挑选成功结果。20 个实际 solve/scoring 子进程均观察到 Hash Seed=0、QISKIT_PARALLEL=FALSE、未使用父进程的 `-I`。

- Python **3.12.14**，Qiskit **2.6.1**，Aer **0.18.2**。
- NumPy 2.5.4、SciPy 1.18.1、rustworkx 0.18.1、PyYAML 6.0.3；完整包清单保留。
- OMP=2，OpenBLAS/MKL=1，Rayon 未设置。
- 官方评分：basis `rz,sx,x,cx`，level 1，seed_transpiler=12345，无 coupling map / initial layout。
- 完整 wall time **201.018 秒**；20 ms 采样进程树峰值 RSS **692.352 MiB**。该 RSS 可能重复计算共享页或漏瞬时峰值，不是精确独占内存峰值。
- **10/10 FULL、10/10 hash match、10/10 实际 Aer 执行、零 flags、零超时、退出码 0。**

| Tier | status / hash / circuit / flags | CX | depth | gates | active qubits |
|---|---|---:|---:|---:|---:|
| 1 | FULL / match / yes / 0 | 151 | 44 | 298 | 25 |
| 2 | FULL / match / yes / 0 | 0 | 3 | 3 | 1 |
| 3 | FULL / match / yes / 0 | 7,808 | 8,771 | 19,497 | 7 |
| 4 | FULL / match / yes / 0 | 183 | 195 | 455 | 20 |
| 5 | FULL / match / yes / 0 | 10,950 | 19,703 | 28,363 | 19 |
| 6 | FULL / match / yes / 0 | 3,000 | 5,691 | 8,680 | 22 |
| 7 | FULL / match / yes / 0 | 209 | 155 | 533 | 15 |
| 8 | FULL / match / yes / 0 | 7,856 | 18,804 | 22,861 | 18 |
| 9 | FULL / match / yes / 0 | 34,186 | 71,632 | 102,830 | 22 |
| 10 | FULL / match / yes / 0 | 38,823 | 92,604 | 111,337 | 19 |
| 十关分别汇总 | 全部通过 | **103,166** | **217,602** | **294,857** | — |

该深度合计是十条评分电路深度之和，不是一条联合电路。完整官方输出：[report.json](v631-independent-audit/checker/report.json)、[report.md](v631-independent-audit/checker/report.md)；环境、进程、资源、命令及保全结果：[independent-checker.json](v631-independent-audit/independent-checker.json)。全部 96 个官方源树文件和 37 个提取成员运行前后逐字节不变；原 ZIP SHA 也未变。临时官方树及非公开执行日志已在保全检查后清理。

## 4. 与 Junrui 指标的差异

本轮十关四项指标与前次独立审计 `be105035dee6cdbbf30f1dc06a95100f4c9e49f5` 的本地三轮逐项一致。与 Junrui 参考值只存在已披露的以下差异：

| Tier | Junrui depth / gates | 本轮独立 depth / gates | CX 是否改变 |
|---|---|---|---|
| 5 | 19,703 / 28,413 | 19,703 / 28,363 | 否 |
| 6 | 5,715 / 8,752 | 5,691 / 8,680 | 否 |
| 7 | 154 / 536 | 155 / 533 | 否 |

其他七关及所有 active qubits 不变。运行源码逐字节相同，新文档也主动披露两组指标；没有新出现的执行或包装异常。先前定向取证已核对实际执行/评分来源与本地确定性，跨历史环境的具体触发机制仍未完全隔离。不能声称本轮精确复现了 Junrui 的深度/总门数，也不应为匹配旧数字修改归档或配置。

先前针对这两组向量的评分分析仍适用：固定其他队伍指标时，Team 3 自身 Simplicity 变化的保守范围约为 −0.003629 至 +0.006985 分；不保证极接近的排名或裁判分析分不变。该已披露差异不影响本轮 FULL、哈希、实际量子执行或提交文件完整性。

## 5. 文档准确性及三个非阻断备注

直接从 ZIP 阅读两份文档，核对了实际最终算法、测量参与密钥恢复的路径、最终 T8=7,856 / T9=34,186 / T10=38,823 CX、测试的有效范围和公开预处理成本。文档区分模拟/硬件、toy 规模/可扩展算法、SHA/酉等价、门数/运行时间、深度和/单电路深度。T9 后续 v6.2 五组配对中位时间 13.275→10.616 秒有原始记录，不能因此改写更早 v2 OSC 的 INCONCLUSIVE 结论；本文件也不作这种改写。

以下内容仍需准确转述，**没有在 ZIP 中被本审计悄悄修正**：

1. **WRITEUP:231 的“所有结果均 statevector”过宽。** Tier 2 官方 Channel 使用自动 Aer method，不能保证固定 statevector。准确说法为“理想 Qiskit Aer 模拟；主要 solver 指定 statevector”。这不改变“没有使用物理量子硬件”的事实。
2. **README:88–89 将评分电路等同于 exact Aer 输入不够精确。** 官方先记录/规范化，再按评分配置转译；Tier 2 另按官方 Channel.log 规则取电路。WRITEUP 前段已说明再转译，实际评分符合规则，但展示时应明确该转换。
3. **WRITEUP:184–185 的单独 `6.5e-15` 数字未找到可追溯引用。** 不将它认作独立核实结果。已追溯的 accepted-cache 研究证据记录了两个限定输入的全状态误差 0.0 及十二个受控模块检查；其范围必须分别说明，不能外推为完整 19-qubit 酉矩阵证明。若演示中需引用数值，应引用已找到的证据或补充准确原始出处。

这些是模拟方法标签、评分表述和单独数值引用的限制，不涉及新的运行逻辑、隐藏答案、成员缺失、错误电路或哈希失败。发布判断依赖完整运行、源/字节对比及可追溯算法证据，不依赖第3条未核实数字。因此不阻断当前确切文件的提交，但并不担保文档能获得满额裁判分析分。

详细逐段引用及审阅边界：[documentation-review.md](v631-independent-audit/documentation-review.md)。

## 6. 最终交接

批准团队使用此确切新 ZIP，继续由团队负责人决定并执行平台提交。下载地址（需要仓库权限）：

[2fe40b2 中的原始 v6.3.1 ZIP](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/2fe40b2d096d87875244d5ccbb8a76ef979ac499/drafts/ten-locks-team3-v6.3.1-docs.zip)

下载后核对上文完整 SHA-256；本次没有重建 ZIP、修改生产/官方代码、修改发布分支、创建 PR 或上传比赛平台。只在独立审核分支增加证据。

机器签字：[release-decision.json](v631-independent-audit/release-decision.json)。复现脚本、原始官方结果及 source bindings 均保存在 `docs/v631-independent-audit/`。本签字仅覆盖固定提交和摘要，不替代后续不同字节归档的独立审核。
