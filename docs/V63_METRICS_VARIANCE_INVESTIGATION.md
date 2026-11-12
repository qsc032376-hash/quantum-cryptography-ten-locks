# v6.3 最终 ZIP 编译指标差异调查

**最终结论：SAFE_WITH_VARIANCE。建议继续提交原批准 ZIP；无需为重现旧门数而重打包或更改算法。** 三次新的完整官方 Checker 均 10/10 FULL、10/10 哈希匹配、零 flags、零超时，全部十关指标逐项一致。Tier 5/6/7 的四阶段追踪、实际执行记录桥接和官方评分重放均通过。历史差异已部分定位，但具体跨环境触发机制未获可重复的因果证明，因此不使用 METRICS_RECONCILED。

更新时间：2026-11-11T20:21:36.227816-05:00（America/New_York）。本次没有上传比赛提交，也没有修改提交截止时间。

## 1. 固定输入与保护范围

- 批准集成：`ce75c0721622d363e77912191a52a02c34f92472`。
- 最终 ZIP 原审计：`a6eb6230000a91317911c917755f9549847a35e8`。
- 原始 ZIP：`drafts/ten-locks-team3-v6.3-rc.zip`。
- 实测原始字节 SHA-256：`64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`。
- 本分支：`audit/v63-metrics-variance-junqi`，基于上一轮补充审计 `e49ed058ed83b43866ffca4ca9b9785e3f9301ed`；旧报告和结果原样保留。

三次从官方上游 `340e1ce18cafa69f4cea906f88f93741738dc0fa` 创建新的文件树，直接解压同一批准 ZIP，复用固定的已安装解释器/依赖环境。这里的“新环境”是新的官方树、提取目录和工作进程，不声称安装了三个不同虚拟环境。37 个运行成员与批准清单逐字节一致；每份树的 76 个受保护官方文件亦保持一致。官方 Checker、评分配置、生产代码、Oracle、Helper、缓存、发布分支及 ZIP 未改变。

此前审计中针对“必须复现历史精确指标”的 INCONCLUSIVE 原样保留；本次按用户指定的三个新验收类别判定，并未改写前次结果。每轮原始官方报告和所有失败/异常字段都保留，没有替换或挑选结果。

## 2. 环境及 seed 的独立核对

| 项目 | 历史批准记录 | 本次实测 | 解释 |
|---|---|---|---|
| Python | 3.12.10 | 3.12.14，CPython/Clang 22.1.3 | 补丁不同；不能称历史和当前环境完全相同 |
| Qiskit / Aer | 2.6.1 / 0.18.2 | 2.6.1 / 0.18.2 | 版本号一致；历史原生构建指纹缺失 |
| 其他包 | 历史完整实际清单未保存 | NumPy 2.5.4、SciPy 1.18.1、rustworkx 0.18.1、PyYAML 6.0.3、dill 0.4.1、stevedore 5.9.1、psutil 7.2.2 | requirements 中的 pin 不当成历史实测版本 |
| solver 预转译 | level 2 / seed 12345 | 同左，`num_processes=1` | T5 指定 Aer backend 并随后做既有 GF(2) 简化；T6/7 使用既有通用目标 |
| 官方评分转译 | level 1 / seed 12345 | 同左 | basis 均为 `[rz,sx,x,cx]`，无 coupling map / initial layout |
| 实际 worker Hash Seed | 官方源码强制 0 | 实际评分子进程观察为 0；诊断子进程为 0 | 父 CLI 的 `-I` 不传播到官方启动的 worker |
| 线程配置 | 历史信息不完整 | OMP=2、OpenBLAS=1、MKL=1、QISKIT_PARALLEL=FALSE、Rayon 未设置 | 保留原生产线程/内存参数 |

本次全部 13 个已安装包、Python build、CPU、cgroup 限额、16 个实际导入原生扩展的文件 SHA 见 [full-environment.json](v63-metrics-evidence/full-environment.json)。主机为 Linux x86_64/glibc 2.41；cgroup 限额 16 GiB、相当于 4 CPU 时间配额。结尾再次核对解释器二进制、依赖版本和受保护源码，均未改变。Jupyter/绘图等可选环境未安装，不影响官方 CLI；不声称完整 requirements 的每个可选包均安装。

实际诊断观测到的 Aer 参数：

| Tier / 实际调用 | shots | `seed_simulator` | 说明 |
|---|---:|---:|---|
| 5 Grover | 128 | 未指定，backend 默认也为 None | 按批准代码保留，未擅自注入固定 seed |
| 6 校准 | 2,048 | 606 | 真正测量后选择搜索轮数 |
| 6 搜索 | 640 | 607 | 本次无需补采样 |
| 7 QPE | 64 | 707 | 主评分对象 |
| 7 相位检查 | 32 | 708 | 依赖测量结果的实际第二条电路 |

这些是固定配置的重复执行，不是十组独立随机种子可靠性实验；Aer 采样随机性不等同于编译随机性。T5 的采样发生在其唯一待评分电路构造/预转译之后。

## 3. 三次完整官方 Checker：全部记录

固定执行未修改的 `python -I tools/check_submission.py submissions/team3 --out ...`。官方每阶段 120 秒限制及 60 秒启动宽限保持原样；外部只读观察器捕获实际评分输入并采样资源。

| 新运行 | FULL / hash | flags / 超时 | CX 合计 | 深度和 | 总门数 | 全部 Checker 秒 | 采样峰值 RSS MiB |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 10/10 / 10/10 | 0 / 0 | 103,166 | 217,602 | 294,857 | 162.514 | 694.684 |
| 2 | 10/10 / 10/10 | 0 / 0 | 103,166 | 217,602 | 294,857 | 196.533 | 694.598 |
| 3 | 10/10 / 10/10 | 0 / 0 | 103,166 | 217,602 | 294,857 | 173.120 | 694.801 |

合计 **30 个 FULL、30 个 hash 匹配**，没有资源中止、缺失指标或非零退出。三轮分别从全新官方树开始，实际 Aer 执行字段均为 true。原始报告：[第1轮](v63-metrics-evidence/run-1/checker/report.json)、[第2轮](v63-metrics-evidence/run-2/checker/report.json)、[第3轮](v63-metrics-evidence/run-3/checker/report.json)；完整环境、时间和资源采样见 [three-runs.json](v63-metrics-evidence/three-runs.json)。

RSS 为每 10 ms 采样的进程树 RSS 之和，可能漏瞬时峰值或重复计入共享页；不是精确独占内存峰值。不同轮次 wall time 有主机负载影响，不用来宣称加速。十关“深度和”是各选中电路深度的相加，不是一条联合电路。

## 4. 四阶段电路指纹与实际评分来源

三轮普通 Checker **没有安装任何额外 Python hook**。外部观察器仅从真正 `--_transpile` 子进程 argv 指向的完整 `.circuits` 流复制输入。随后增加三个独立的 Tier 5/6/7 诊断 solve、三个诊断 scoring worker，以 `sys.setprofile` 观察未修改函数的参数/返回值；不替换官方函数或改变电路。它们不是三轮完整 Checker 的替代品。

定义：A 为实际 solver 传给预转译的构造电路；B 为实际 `AerBackend.run` 收到的电路；C 为官方 recorder 去模拟器伪指令并规范化 name/metadata 后、按官方规则选中的评分输入；D 为该官方评分 worker 真正输出的转译电路。T5 的预转译和 B 之间还存在批准代码原有的 GF(2) 简化，已额外取证。

结构 SHA 使用 `v63-parameter-free-ordered-structure-v1`：包含有序公开操作类别、arity、qubit/clbit 索引、参数类型；排除数值参数、global phase、标签、metadata、自动生成名称和 opaque gate 内部定义。**结构哈希相同不是算符等价证明。** 另对原生门序列、数值参数及 global phase 做零容差临时比较，只发布布尔值。

下表为选中电路，指纹显示前 12 位；全文 SHA 在附录及 [four-stage-selected-summary.json](v63-metrics-evidence/four-stage-selected-summary.json)。A 的 opaque 复合门不展开，因此 A 的 top-level 成本不得当成最终评分成本；literal CX 与顶层 2Q 指令数分列。

| Tier | 阶段 | 结构 SHA 前缀 | literal CX | 当前表示的 2Q | depth | gates | active qubits |
|---|---|---|---:|---:|---:|---:|---:|
| 5 | A 构造 | `c57e9feb4566` | 0 | 0 | 51 | 60 | 19 |
| 5 | B Aer实参 | `1ed2d4e6f9ff` | 11,000 | 11,000 | 19,703 | 28,413 | 19 |
| 5 | C 评分选中输入 | `1ed2d4e6f9ff` | 11,000 | 11,000 | 19,703 | 28,413 | 19 |
| 5 | D 官方转译输出 | `f17356f5e138` | 10,950 | 10,950 | 19,703 | 28,363 | 19 |
| 6 | A 构造 | `71634cc859bf` | 0 | 0 | 25 | 38 | 22 |
| 6 | B Aer实参 | `82c671d5f1f8` | 3,000 | 3,000 | 5,691 | 8,680 | 22 |
| 6 | C 评分选中输入 | `82c671d5f1f8` | 3,000 | 3,000 | 5,691 | 8,680 | 22 |
| 6 | D 官方转译输出 | `82c671d5f1f8` | 3,000 | 3,000 | 5,691 | 8,680 | 22 |
| 7 | A 构造 | `7cd02dfb3fc4` | 0 | 14 | 16 | 30 | 15 |
| 7 | B Aer实参 | `5da512e6707c` | 209 | 209 | 155 | 533 | 15 |
| 7 | C 评分选中输入 | `5da512e6707c` | 209 | 209 | 155 | 533 | 15 |
| 7 | D 官方转译输出 | `5da512e6707c` | 209 | 209 | 155 | 533 | 15 |

官方按最大 `(two_qubit_gates, depth)` 选记录，完全并列保留首条，而非只取 `build_circuit()`：

- T5：唯一记录，索引 0，25 轮 Grover；level-2 输出 11,800 CX / depth 20,778 / 29,213 gates，原有 GF(2) 简化后 B 为 11,000 / 19,703 / 28,413，官方 level-1 再到 10,950 / 19,703 / 28,363。没有把预转译总门数误当评分总门数。
- T6：实际记录两条，索引 0 为校准（436 CX / 819 / 1,206，23 个活跃 qubits），索引 1 为实测校准后选中的 12 轮搜索，后者被评分（22 个活跃 qubits）。没有用默认构造器替代真正测量选择。
- T7：实际记录两条，索引 0 是 QPE，被评分；索引 1 为测量后相位检查（27 CX / 68 / 161）。没有把检查电路误认为 QPE。

完整 instruction histogram、width、测量映射及所有未胜出电路在六份 `tierNN-{solve,score}-profile.json` 中保留。评分输出主要 histogram：

| Tier | CX / RZ / SX / X / measure |
|---|---|
| 5 | 10950 / 12301 / 4862 / 250 / 10 |
| 6 | 3000 / 4178 / 1502 / 0 / 14 |
| 7 | 209 / 267 / 31 / 26 / 14 |

所有 trace_complete 均 true、profile_errors 均空；B 与官方 recorder 的原生电路双向精确匹配，诊断记录与第一轮普通 Checker 记录逐项精确匹配。三轮 Tier 5/6/7 的所有评分输入的门序、数值参数、量子/经典位映射、global phase 均一致；所有 9 个 Tier/轮次组合的官方评分重放精确复现原始报告，C/D 结构摘要三轮一致。T5/6 都是输入 q[j]→c[j]；T7 的 14 位计数寄存器直接对应 c[0..13]，映射在原生输入和评分输出间保持。

六个额外诊断 worker 均成功，最长单 worker 68.948 秒；最大 50 ms 采样进程树 RSS 244,342,784 字节，均未触及 120 秒/2 GiB 诊断上限。诊断时间含 profiler 成本，不能冒充普通 Aer 性能。合成指纹自测曾因夹具未真正创建不同参数的电路而失败，重建独立合成夹具后通过；这是测试夹具修正，不是算法/Aer 失败，见 [方法记录](v63-metrics-evidence/four-stage-methodology.md)。

## 5. 根因定位及逐项假设检验

| 假设 | 实际证据 | 可以得出的结论 |
|---|---|---|
| 原 ZIP、源文件或评分配置改变 | 原始 ZIP SHA、37 成员及每份官方树 76 文件保持，配置 SHA 不变 | 排除本轮输入被改的解释 |
| Python dict/set / Hash Seed | 复用 e49 的 T5/名义 T6 Hash Seed 0/1/42 及同进程三次探针；本轮真实 worker Hash Seed=0、原生有序记录三轮相同 | 已测范围未复现；不能证明全部库遍历永远无影响 |
| 随机 routing / transpiler | 当前 level 1/2 pass 类及配置树已保存；没有 layout/routing/SABRE/StochasticSwap；seed=12345 | 未发现该路由随机性来源；不等于所有 native pass 都跨平台确定 |
| 无 seed 的前处理/操作构造顺序 | T5 GF(2) wire 排序及消元路径确定；T5/名义 T6 两个新进程的构造/编译结构相同；实际执行原生电路三轮精确相同 | 当前未复现构造顺序差异；历史有序构造记录缺失 |
| Python/数值库/原生扩展补丁差异 | Python 3.12.10 与 3.12.14 不同；旧完整 wheel/依赖/CPU/线程快照缺失 | 仍是未隔离因素，不能认定 Python 补丁就是根因 |
| 共享进程状态 | 每个官方 solve/scoring 是新进程；此前同进程重复探针也稳定 | 当前实验不支持该解释 |
| native 与 scored 口径混淆 | 四阶段来自真实调用，选中索引 0/1/0；实际官方输出重放逐项吻合 | 本轮没有统计错对象；不能从数字巧合反推旧报告口径错误 |
| QPY 序列化顺序 | 新四个 worker 比较直接构造与预转译前 QPY 往返：native/scored 门序、参数、映射、global phase 精确相同 | 在 T5/名义 T6 探针未引发变化；真实567另有全链路记录桥接 |
| Aer 采样随机性 | 实测 seed/shot 如上；三轮记录及赢家相同 | 本轮评分差异不是把不同实际执行电路混比；不声称任意 seed 都成功 |

新低成本编译实验总计 19.482 秒、没有 Aer 执行；pass-manager 清单与直接/QPY对照见 [pass-manager-probe.json](v63-metrics-evidence/pass-manager-probe.json)。Hash Seed 探针明确复用 [前次证据](v63-metrics-reconciliation/mechanism-probe.json)，不伪装为本轮新增执行。

**Tier 5 能定位到的层级：** 批准提交 `docs/v63-evidence/compiler-replay.json` 的“compiled”由历史 `compile_actual()` 返回，实际是经过 GF(2) 后、官方评分前的 native 电路；这由固定研究提交 `97fcc0c7d6dec3b7385dc237d47d89d4d6ffd15c` 的返回语义确认。历史 native histogram 为 CX=11,000、RZ=12,301、SX=4,862、X=300；当前 B/C 前三项相同而 X=250。差异在进入 Aer/官方评分前已存在。历史 native 总门数 28,463→评分 28,413；当前 native 28,413→评分 28,363。两边评分都减少 50 CX，历史/当前额外 50 X 的触发原因尚未知。当前 native 与历史 scored 恰好同为 28,413 不是“旧报告统计错阶段”的证据。

历史 compiler replay 本身没有执行 Aer；未保存历史真实有序电路，故不能指认哪一对 X 被消去，也不能跨历史环境证明最终酉算符相等。T6/7 缺少同等历史中间电路记录，无法可靠定位到某个 pass。具体浮点阈值、原生库行为等仍属假设，不作根因结论。来源与文件 SHA 见 [stage-localization-historical.json](v63-metrics-evidence/stage-localization-historical.json)。

## 6. 实际观察范围及 Simplicity 影响

这里的范围只包括指定的两组报告和本次三轮，并非所有机器/seed 的数学界限。

| Tier | 固定 CX | 历史 depth / gates | 新第1轮 | 新第2轮 | 新第3轮 | 观察范围 depth / gates |
|---|---:|---|---|---|---|---|
| 5 | 10,950 | 19,703 / 28,413 | 19,703 / 28,363 | 19,703 / 28,363 | 19,703 / 28,363 | 19,703–19,703 / 28,363–28,413 |
| 6 | 3,000 | 5,715 / 8,752 | 5,691 / 8,680 | 5,691 / 8,680 | 5,691 / 8,680 | 5,691–5,715 / 8,680–8,752 |
| 7 | 209 | 154 / 536 | 155 / 533 | 155 / 533 | 155 / 533 | 154–155 / 533–536 |

活跃 qubits 分别固定为 19、22、15。新旧差值：T5 gates −50（−0.175976%）；T6 depth −24（−0.419948%）、gates −72（−0.822669%）；T7 depth +1（+0.649351%）、gates −3（−0.559701%）。其他七关四项指标与历史及新三轮一致。

总计观察范围：CX **103,166 不变**；深度和 **217,602–217,625**，新值较参考 −23；门数 **294,857–294,982**，新值 −125。没有实际竞争队伍数据，不能据此给出比赛实际得分或名次。

官方 Simplicity 权重：2Q 40%、depth 30%、gates 20%、qubits 10%。固定其他合格队伍指标，按官方每项最优值归一化规则及零最优值特殊分支，Team 3 自身新旧分数变化的保守包络为：

| 分数差 | 下界 | 上界 |
|---|---:|---:|
| Tier 5 | 0 | +0.000527927357 |
| Tier 6 | 0 | +0.004357771092 |
| Tier 7 | −0.003629032258 | +0.002098880597 |
| 合计 | **−0.003629032258** | **+0.006984579046** |

详细分段公式、精确分数和 77,513 个竞争基线整数检查复用 [scoring-impact.md](v63-metrics-reconciliation/scoring-impact.md) 与 [JSON](v63-metrics-reconciliation/scoring-impact.json)。该界只适用于这两组观测向量、且固定对手指标，不是排名不变保证；其他队伍归一化分数也可能随最优值变化。最大绝对变化上界虽小于 0.01，极接近的排名/平局边界仍可能跨越，不能宣称“分数完全无影响”。

## 7. 验收判断与交接

SAFE_WITH_VARIANCE 的依据是批准字节不变、三次完整真实执行全部合格、四阶段评分来源可追踪、固定本地环境重现稳定、指标变化小且规则允许按实际指标计分。未发现正确性、包装、合规、缺失依赖、超时或内存问题；官方没有要求跨环境逐门匹配某次历史门数。FULL/hash 结果不单独证明酉等价，结构指纹亦不作这种证明。

剩余风险是历史环境的具体触发机制未隔离、跨平台门数可能继续有小幅变化、未来任意采样种子没有穷尽测试，以及微小的最终评分/排名敏感性。以上不构成当前证据下必须延迟提交或修改批准文件的理由。主办方最终应采用其官方环境的真实评分结果。

交接继续使用[批准提交中的原 ZIP](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ce75c0721622d363e77912191a52a02c34f92472/drafts/ten-locks-team3-v6.3-rc.zip)，登录有权限的 GitHub 账号下载原始文件并核对上文 SHA。没有生成替代归档、修改生产/发布分支或代为提交。

机器验收入口：[investigation.json](v63-metrics-evidence/investigation.json)。复现方式、全部证据入口和隐私处理：[README](v63-metrics-evidence/README.md)。所有私有 QPY/临时运行树在完成比对及保全检查后清理；仓库只保存安全摘要、诊断源码、官方报告和公开统计。

## 附录：选中电路的完整结构 SHA-256

| Tier | 阶段 | SHA-256（结构，不包含数值参数/global phase） |
|---|---|---|
| 5 | A 构造 | `c57e9feb4566048612ca8e6d5bbbc961398954802fe2c698595cf0cc8ee13366` |
| 5 | B Aer实参 | `1ed2d4e6f9ff1de2efec9ce6a0fe913e212fa9bdfd2298471f93e1e9008a7995` |
| 5 | C 评分选中输入 | `1ed2d4e6f9ff1de2efec9ce6a0fe913e212fa9bdfd2298471f93e1e9008a7995` |
| 5 | D 官方转译输出 | `f17356f5e13863cc189930ad9e441400a240a9b21e076643015d4dc7e6bfe29d` |
| 6 | A 构造 | `71634cc859bf733e22ce4b3fbf8d64d87254aee914be5f69b66b00addc3b87e3` |
| 6 | B Aer实参 | `82c671d5f1f8364388e36b22be12f4a9836347fbfc8e2ddf08c706ae99d7b221` |
| 6 | C 评分选中输入 | `82c671d5f1f8364388e36b22be12f4a9836347fbfc8e2ddf08c706ae99d7b221` |
| 6 | D 官方转译输出 | `82c671d5f1f8364388e36b22be12f4a9836347fbfc8e2ddf08c706ae99d7b221` |
| 7 | A 构造 | `7cd02dfb3fc47773ea06055cfbc8eee44bbf23ca2bc76e100f7c5e2763b65c89` |
| 7 | B Aer实参 | `5da512e6707cf12cfeb25c55ae64d1588e96e7a7abd66580d6b95063bcdd91b5` |
| 7 | C 评分选中输入 | `5da512e6707cf12cfeb25c55ae64d1588e96e7a7abd66580d6b95063bcdd91b5` |
| 7 | D 官方转译输出 | `5da512e6707cf12cfeb25c55ae64d1588e96e7a7abd66580d6b95063bcdd91b5` |
