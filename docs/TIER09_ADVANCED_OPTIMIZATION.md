# Tier 9：全局可逆置换与 clean 合成辅助位

Junqi Sheng；分支 `optimization/tier09-v2`。

**结论：`INCONCLUSIVE`，保留候选供独立复核，不替换冻结发布版。**
全局固定掩码消元加一条实际 clean 辅助线，使双比特门下降 **37.1328%**，
深度下降 **48.8436%**，总门数下降 **36.2233%**，评分活跃位 **21→22**。
九项廉价正确性测试通过，两版官方 Checker 均 full、SHA-256 匹配、无 flags。
候选十组真实 Aer 种子全通过，基线九组通过、一组超时；严格十组全成功配对条件
未满足，也未冒签人工可靠性复核。
完整安全证据见 [TIER09_ADVANCED_OPTIMIZATION.json](TIER09_ADVANCED_OPTIMIZATION.json)。

## 固定来源与修改边界

- 已验证基线：`release/ten-locks-v5-verified@41c7c6775b8fc499c2acdd878b4829bd17e1210d`。
- 不可变受测快照：`f9ded9fac59ebd8a2ed3e19232ffe2eaa88bac93`。它包含三份生产文件和
  三份测试／夹具，作为最终交付提交的父提交保留，确保推送后仍可检出复现。
  最终交付只再增加本报告与安全 JSON；源码 SHA-256 用于逐字节核对。
- 原样复用 Benchmark Harness `ab9676749e00da904d0b8076811a2407d3b7205f`。
- 环境：Python 3.12.14、Qiskit 2.6.1、Aer 0.18.2、NumPy 2.5.4；没有安装依赖。

生产改动仅为：

1. 新增 [global_permutation.py](../submissions/team3/tier09/global_permutation.py)，改变公开
   置换的全局行消元策略。
2. [shared_controls.py](../submissions/team3/tier09/shared_controls.py) 仅改变编译函数的导入；
   v5 已有的共享条件扇出实现原样复用，不把它再次计为新优化。
3. [solution.py](../submissions/team3/tier09/solution.py) 在实际电路中加入一条零初始化的
   `synthesis_work` 线路，并同步辅助位诊断。14 位计数、7 位模乘 work、底数、幂序列、
   shots、逆 QFT、测量映射及经典恢复／RSA 接口均保持不变。

保留旧 `tier09/modular.py`，因为 Tier 10 还会导入它。其他 Tier、官方工具／输入／
Helper／哈希、冻结引用及 `drafts/` 提交包均未修改。未合并 main、未建 PR、未创建 v6。

## 全局消元的数学证明

公开互素乘子 m 对完整 work 空间的置换为

\[
P_m(x)=\begin{cases}mx\bmod N,&x<N,\\x,&x\ge N.\end{cases}
\]

只使用公开 N 和 `pow(2, 2**j, N)` 构造门。没有计算置换循环长度、预先求阶、试除 N、
枚举隐藏答案或修改 Oracle；Tier 9 官方允许按公开模乘置换构造可逆电路。

令 \(G(C,t)\) 在正控制掩码 C 全为一时翻转 t，且 \(t\notin C\)。消元维护当前
置换 T，依次处理整数行 i；此前的所有较小行已经固定。设初始 \(y=T(i)\)。因 T
仍为置换，\(y<i\) 会与已固定行冲突，所以 \(y\ge i\)。

记 \(A=i\mathbin{\&}\neg y\)，\(B=y\mathbin{\&}\neg i\)。新行消元是：

\[
\prod_{t\in A}G(y,t),\qquad \prod_{t\in B}G(i,t).
\]

第一阶段**固定最初的 y 作为控制条件**，不把刚设成一的目标位追加为后续控制。
所有目标都在 y 之外，所以这些门可交换，使 y 变成 \(y\lor i\)；任何受影响状态
都包含 y，整数值至少为 y，因此不影响早先固定行。第二阶段以 i 为固定控制，
清掉多余位，使 \(y\lor i\to i\)；受影响状态至少为 i，同样不破坏早先行。
每一步都是可逆 X 门，最终 T 成为恒等置换。

若按消元顺序的门为 \(E_1,\ldots,E_L\)，则
\(E_L\cdots E_1P_m=I\)，故反序执行这些自逆门得到原 \(P_m\)。该推导覆盖
完整 work 空间，包含 x=0、全部 padding，而非只覆盖从 `|1⟩` 可达的轨道。

v5 的设一阶段会逐位扩大控制掩码。新方案在消元生成阶段改变整个门序列，形成
更低控制数的同条件门组，再由既有 emitter 合并；这不是再次实现 v5 的扇出技巧。

## 控制、相位与辅助位

给每个逻辑 X 门加外控制 c，得到

\[
C(P_m)=|0\rangle\langle0|\otimes I+|1\rangle\langle1|\otimes P_m.
\]

原 emitter 对同条件目标集合 S 选 pivot p，令
\(F=\prod_{t\in S\setminus\{p\}}CX(p,t)\)。\(F G(C,p) F\) 等于按条件 C
同时翻转 S。F 不触及控制位；外控制关闭时两侧 F 相消，不能因不受外控而遗漏它们。
所有源级 primitive 都是精确 CX/CCX/MCX，复矩阵的非零项均为 +1，因此相同基态
置换对应相同完整复酉矩阵，保留相对相位和与外部参考系统的纠缠。

新增加的 clean 线确实属于传入 Aer 并被官方记录的 **22-qubit 电路**，不是事后只
加到另一条评分电路。原生 MCX 执行时该线为恒等作用，因此源级电路为 \(U\otimes I\)。
官方 HLS 可以合法使用这条零初始化线并恢复它；完整 clean 模板满足

\[
V(|\psi\rangle\otimes|0\rangle_a)=(U|\psi\rangle)\otimes|0\rangle_a
\]

对任意数据态和外部纠缠都成立。**不声称 clean 辅助输入为一时也有完整算子等价**。
没有单独替换相对相位 Toffoli 或丢弃其修正；完整 KG24 构造的内部相位必须抵消。

正式布局为 count q0–13、work q14–20、clean q21、14 classical bits。
work q14 制备 `|1⟩`；仍有全部 14 个受控 \(U^{2^j}\) 和含 SWAP 的完整逆 QFT。
`q[j]→c[j]`，Qiskit 字符串直接按二进制转整数，不反转，不根据明文猜位序。

资源口径必须区分：**原生声明 22q，原生活跃 21q，官方分解活跃 22q**。
21→22 的完整 complex128 statevector 理论容量由 32→64 MiB；Aer 可以优化闲置线，
但这不把评分或硬件资源变回 21q，也不构成内存提速证据。

## 便宜测试先行

首次两套测试共 **9 个测试方法全部 PASS**，未为获取更好结果重跑。

- [全局置换测试](../tests/test_tier09_advanced_optimization.py)：7 项、12.577747 秒。
  包含所有 24 个 2-bit 置换及固定样本的较宽置换，共 66 例；24 例新旧消元序列不同，
  仍与解析参考、冻结 v5 的完整复矩阵一致。另有 5 个合成模乘的控制／padding／逆操作。
- 公开 N=77 的各个实际幂乘子，对原／新实际发出的门遍历全部 256 个控制＋work 基态，
  共 2560 次检查；另核验实际 native primitive 控制数 1–7 的精确复矩阵及总相位。
  这只验证公开门构造，不从这些表求阶或因子。
- 同一次人工 Aer 批次运行 5 条小电路：旧／新两个人工 Shor 实例及一个经官方基门
  合成的候选。后者为 13q，2937 个基门操作实际触及 clean 位；完整复振幅、计数边缘
  概率及 clean 恢复通过。最大振幅差 `8.04e-14`、概率差 `1.10e-14`、clean 泄漏
  `2.29e-29`。该套最大矩阵 8q，峰值 RSS 140.13 MiB，人工 Aer 两线程／512 MiB。
- [clean 模板测试](../tests/test_tier09_clean_workspace.py)：2 项、3.103 秒。
  1-clean／2-clean KG24 各取 3、5、7 控制，穷尽所有 clean=0 输入列，逐元素比较
  复矩阵，不拟合全局相位。最大矩阵 10q／16 MiB，最大误差 `3.77e-15`，非零辅助
  振幅最大 `3.33e-16`。不调用 Aer，不把承诺子空间检查冒称任意辅助输入等价。

夹具 [tier09_v5_shared_controls.py](../tests/fixtures/tier09_v5_shared_controls.py) 与 v5
原文件逐字节一致，且其相对导入仍绑定未改的旧编译器，避免用新实现和自身比较。

## 静态筛选与未采用实验

以下有效表项均保留测量通过两次转译：先按实际 Aer native target、opt1、seed12345
编译，再用官方 `rz,sx,x,cx`、opt1、seed12345、全连接、无 initial layout 评分。
门数和深度由原版 `compute_metrics` 统计，不含测量／barrier。

| 方案 | 双比特门 | 深度 | 总门数 | 活跃位 | 决策 |
| --- | ---: | ---: | ---: | ---: | --- |
| v5 基线，已含共享控制扇出 | 89,075 | 235,048 | 263,601 | 21 | 对照 |
| 精确可交换门抵消 | 89,019 | 234,976 | 263,559 | 21 | 小收益，未选 |
| Pivot 动态规划＋抵消 | 88,945 | 234,952 | 263,485 | 21 | 小收益，未选 |
| 原始门序列 XOR cube 合并 | 89,571 | 237,507 | 266,197 | 21 | 复杂度倒退，拒绝 |
| 扇出后 XOR cube 合并 | 88,359 | 233,449 | 261,968 | 21 | 小收益，未选 |
| Canonical 固定掩码消元 | 69,693 | 178,514 | 202,214 | 21 | 有效的无增位备选 |
| 固定掩码＋实际 clean 线 | **55,999** | **120,242** | **168,116** | **22** | 本轮选择 |

Canonical 21q 与最终 22q 均由最终代码的独立静态检查确认；不是按删掉多少 CCX
推算 CX。既有 dirty 资源足够时，Qiskit 默认 HLS 已选择较优精确 M15，显式重做该
替换没有固有新收益。仅延迟各计数 H 的尝试被 native 转译重新前置，实测仍与 v5
四指标完全相同，没有把该零收益方案计为优化。

未采用方案的等价依据：

- 两个条件 X 的目标都不在对方控制集合时可交换；只跨越满足此条件的门移动相同门，
  再用 \(G^2=I\) 抵消。Pivot 选择仍应用上节精确 \(F G F\) 恒等式。
- 同目标门的条件按 XOR 合并。对不含 t、b 的条件 r，三个条件
  \(r,rb,r(1\oplus b)\) 的任意两个 XOR 等于第三个；负控制用 X 共轭精确实现。
  该恒等式保留所有分支及相位，但提前合并会破坏后续扇出机会，所以可能更贵。
- 另筛选有限的位重标记／逆置换变体。若 R 是位排列，编译 \(RPR^{-1}\) 后反共轭
  仍为 P；编译 \(P^{-1}\) 再逆执行也为 P。二十候选选择器取得 66,933 个双比特门
  （21q、仅保留可靠的双比特统计，不引用含测量的原始 depth/size），但增加编译启发式
  和来源审计复杂度；不如本轮简单 22q 方案，不投产。
- 显式借未来计数位的 clean 分解有完整 clean=0 数学契约，H 可在逻辑上延迟到自己的
  幂块前。但一次研究进程从正在修改的工作树导入，未固定源码；其数值保留为
  `UNPINNED` 观察，**排除在正式基线对比和接受证据外**，不宣称运行成功或速度收益。

未选的可交换／XOR 方案仍是精确变换；“拒绝”指实测复杂度倒退，不指数学错误。
没有穷举秘密密钥来选择这些编译策略。

## 真实 Aer、官方 Checker 与配对种子

运行源码固定在上述快照，先完成便宜测试，再各跑十个不同 Aer seed，最后用原版
Harness 对两个隔离 Git archive 分别执行 profile 和官方 `check_tier`。
未修改 Checker 或放宽比较条件。每次 native Aer 使用 statevector、两线程、
512 MiB；Harness 外部预算每次 120 秒／1024 MiB，每版 cross 总预算 1800 秒。
官方 wrapper 总预算 370 秒，其中官方 solve 与评分转译仍各自限时 120 秒。
Profile 注入相同 Aer seed2026，官方运行不注入，保留 solution 的 seed909。

两版官方 Checker 均为 **full**、**SHA-256 匹配**、metrics status **ok**、
**flags=[]**、resource state **ok**。各记录一次实际执行、一次 unique circuit。
两版 profile 也均哈希匹配、instrumentation_verified=true；native 转译配置相同。
下面四指标在静态检查、真实 profile 与官方 Checker 三者间一致：

| 官方评分 | v5 | 候选 | 减少比例 |
| --- | ---: | ---: | ---: |
| 双比特门 | 89,075 | 55,999 | 37.1328% |
| 深度 | 235,048 | 120,242 | 48.8436% |
| 总门数 | 263,601 | 168,116 | 36.2233% |
| 活跃 qubits | 21 | 22 | **增加 4.7619%** |

| 测量项 | v5 | 候选 |
| --- | ---: | ---: |
| Profile solve（秒） | 28.460 | 30.783 |
| Profile Aer job elapsed（秒） | 28.211 | 30.560 |
| Profile 评分转译（秒） | 1.874 | 2.169 |
| Profile 进程树峰值 RSS（MiB） | 226.926 | 204.559 |
| 官方 solve（秒） | 24.466 | 57.115 |
| 官方进程树峰值 RSS（MiB） | 213.004 | 220.652 |

时间是单次观测；Aer job elapsed 从提交到 result 完成，包含等待和 Aer 内部编译，
不是纯状态向量 kernel 时间。表中评分转译时间来自 profile；官方 safe entry 未单列
转译秒数，不能用总墙钟差伪造。RSS 每 20ms 采样整个进程树合计，可能重复计入共享页，
也可能漏过短峰值，不当成精确分配器最大值。已完成运行没有内存限制异常。

十组原始结果如下；PASS 均表示真实执行后 solve 完成且官方明文哈希匹配，
不保存因子、周期、密钥、明文或原始 counts：

| Aer seed | v5 状态／solve秒 | 候选状态／solve秒 | 已知 shots（v5／候选） |
| ---: | --- | --- | --- |
| 1000 | TIMEOUT／未知 | PASS／59.674 | 未知／64 |
| 2000 | PASS／32.275 | PASS／111.225 | 64／64 |
| 3000 | PASS／30.011 | PASS／41.276 | 64／64 |
| 4000 | PASS／27.359 | PASS／36.661 | 64／64 |
| 5000 | PASS／32.934 | PASS／37.053 | 64／64 |
| 6000 | PASS／32.232 | PASS／40.478 | 64／64 |
| 7000 | PASS／33.496 | PASS／62.338 | 64／64 |
| 8000 | PASS／27.977 | PASS／38.595 | 64／64 |
| 9000 | PASS／47.439 | PASS／47.939 | 64／64 |
| 10000 | PASS／27.653 | PASS／55.837 | 64／64 |

候选每组完成一次 Aer job／64 shots，共 640 shots；九个完成的基线组共 576 shots。
基线 seed1000 在 worker 总墙钟 120.0387 秒触发 TimeoutError；报告没有返回其实际
forwarded seed、完成 shots、solve 或 hash，因此保持未知，不能确定超时发生于 Aer
的哪一阶段，也不能把请求 seed 当成已确认进入 Aer。没有重试、换种子、剔除失败
或改成 PASS。其余十九个完成 trial 均记录了与请求相同的 forwarded seed；
每版内部 seed 不重复，两版使用相同配对值，不能称十九个全球不同 seed。

执行顺序是先基线十组、再候选十组，不是随机交错试验。仅作描述统计，九对共同完成
组的平均 solve 为 **32.375→52.378 秒**，候选约 **1.618 倍**。
不能忽略基线超时来宣称总体可靠性改善，也不能把机器负载未受控的计时差异解释为
确定因果。候选十组范围 36.661–111.225 秒，接近预算；本轮**没有 Aer 提速结论**。
native 不含测量门数从 6103 增至 6677，说明官方 CX 收益不等同于模拟器 native
指令更少。必须分别看评分、qubit 代价和执行成本。

原 Harness 建议 **`INCONCLUSIVE`**：严格配对十组全成功证据不足；此外
`--reliability-reviewed` 代表人工签署，本轮省略。规则和源码由代理审查，
不冒充 Junrui 人工验收。候选未取得完整 ACCEPT，不替换 v5；下一轮若希望提升
结论，应事先制定可解释的资源／抽样计划，保留本轮失败，再由独立审查者决定。
无需为了改变结论反复跑到通过。

完整 22-qubit 复算子未物化；正确性依据为全域解析证明、穷尽局部门测试、合成复振幅
及相位测试、真实因数恢复和明文哈希。编译阶段枚举的是公开 toy 模乘置换，
不是隐藏答案，也不把该指数规模构造宣称为可扩展的 Shor 算术实现。


## 集成交接和复现

只需移交本轮三个 Tier 9 生产文件。**打包清单须加入 `tier09/global_permutation.py`**；
不能只复制一行 import 改动，否则独立包会缺模块。保留原 `modular.py`、RSA、
Tier 8 的公开表及测量后处理、Tier 7 QFT 等现有依赖。测试、夹具和报告不放入提交包。
本轮没有生成／覆盖 ZIP、更新任何发布或集成引用，也没有创建 v6。

无需新依赖。先在选定的集成工作区检查源码指纹，再运行：

```sh
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  python -B tests/test_tier09_advanced_optimization.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  python -B tests/test_tier09_clean_workspace.py
```

原样获取指定 Harness 到同仓库的独立工作树。用受测快照或**运行源码完全相同**的
最终交付提交作为 CANDIDATE_SHA，分别执行两边的 `cross_seed_regression.py --tiers 9`
（种子和预算见安全 JSON），再运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python -B benchmarks/circuit_benchmark.py \
  --baseline 41c7c6775b8fc499c2acdd878b4829bd17e1210d \
  --candidate CANDIDATE_SHA --tier 9 --seed 2026 --official \
  --rules-reviewed \
  --baseline-regression /private/path/baseline.json \
  --candidate-regression /private/path/candidate.json \
  --timeout 120 --memory-mb 1024 --output /private/path/comparison.json
```

两份 cross 报告必须与该命令的精确 SHA 相同；不能把快照的记录改标签冒充另一个
提交。最终文档与快照的差异、运行文件 SHA-256 在安全 JSON 中明确保存。
Harness 的 `--reliability-reviewed` 明确表示人工复核。本轮未传入，不以代理检查
冒充 Junrui 的人工签署；未来人工实际完成抽样可靠性及回归复核后才能显式添加。
完整复现会重新执行真实量子求解，应保留失败记录、遵守预算，不循环到成功。
