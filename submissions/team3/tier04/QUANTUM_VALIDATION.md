# Tier 4 Simon：量子采样与 GF(2) 验证

作者：Junqi Sheng；分支：`feature/quantum-circuits`。
测试基准提交：`c4d2a1046b0c8308e7831545b2bf010959a0b967`。
环境：Python 3.12.14、Qiskit 2.6.1、Aer 0.18.2。

## 当前结论

**量子执行与 GF(2) 恢复 PASS；完整 `solve()` 尚待经典模块集成。**

先通过 29 项合成方程/人工数据/mock 测试，再实际运行官方 Simon Oracle。
一次 Aer 执行、32 shots 得到 29 个不同方程，矩阵秩为 9，零空间维数为 1。
通过消元得到唯一非零 10-bit 整数，并验证其满足全部已观测方程。
没有进行真实明文解密或哈希校验，不将量子部分通过表述为完整提交通过。
原始测量、方程行、主元位置、隐藏周期、密钥、明文均未保存或输出。

机器记录见 [quantum_validation.json](quantum_validation.json)。

## 量子电路与位序

- 20 个量子位：q0–q9 输入，q10–q19 输出；10 个经典位。
- 全零初态，仅输入执行 H；输出寄存器保持 |0>，满足官方 Oracle 的输入约束。
- 一次官方 Oracle → 输入再次 H → qj 测量到 cj。
- 输出寄存器不测量。忽略输出与“测量输出但忽略结果”给出同一输入边缘分布，
  所以测量 y 仍满足 y·s=0（mod 2）。
- counts 显示 c9…c0；直接按二进制转整数，不反转。
  整数 bit j 对应 GF(2) 第 j 列，与官方 s 的 qubit j 约定一致。
- `helper.build_oracle()` 只用于加载并作为整体接入。未检查其内部 Gate Definition、
  Decomposition 或矩阵来推断隐藏周期。

Tier 4 没有官方调用计数函数。本实现为新建的外层 Gate 包装命名，并且只统计该外层
命名块，不递归读取定义。每条采样电路含 1 个 Oracle 块，每 shot 计一次查询。
修改的只是新包装的名字，不是官方 Oracle 文件或其定义。

## GF(2) 恢复

`gf2.row_reduce(rows, n_bits=10)` 采用异或行操作执行完整高斯消元，返回非零 RREF 行
和按列号递增的主元；输入行是整数位掩码。它不按整数数值排序来猜测主元，也不修改
调用方数据。零行、重复行、乱序和生成器输入均受支持。

`gf2.recover_unique_nonzero(rows, n_bits=10)` 根据秩判断：

- rank < 9：自由变量不止一个，不能返回唯一非零候选。
- rank = 9：唯一自由变量设为 1，从 RREF 求其余位；设为 0 时只得零向量。
  因而非零候选唯一。返回前再次检查所有原始方程。
- rank = 10：只存在零解，与非零 Simon 周期承诺冲突，明确拒绝。

整个恢复只做 GF(2) 消元和代入验证，没有枚举候选、暴力搜索或硬编码真实周期。
在题目承诺及理想模拟条件下，这唯一非零核向量就是隐藏周期；独立明文哈希验真仍待集成。

## 采样预算与实测结果

默认每批 32 shots，硬上限 128；每批成功测量后计算累计方程秩，达到 9 立即停止。
只有成功采样但秩不足才请求下一批。异常测量、Aer 失败或满秩直接报错，不重试。
预算用完仍未唯一确定时抛出 `SamplingLimitError`，仅附带秩和 shots 等非秘密诊断。
真实验证另外设置 120 秒期限；模拟器限制 512 MiB 内存、2 个线程。

| 采样指标 | 本次观测 |
|---|---:|
| Aer 执行次数 | 1 |
| 实际 shots / 上限 | 32 / 128 |
| 每条电路 Oracle 块 | 1 |
| 按 shots 计的 Oracle 查询数 | 32 |
| 不同方程数 | 29 |
| 矩阵秩 / 零空间维数 | 9 / 1 |
| 唯一非零候选 | 是 |
| 满足全部已观测方程 | 是 |

秩检查在整批测量完成后进行，不声称 32 shots 是达到秩 9 的最少采样数。
Aer 可以共享状态演化计算来生成多个 shots；查询数按官方每 shot 一次的口径记录。

## 电路资源指标

转译采用官方 `rz, sx, x, cx` 基门、优化级别 1、种子 12345，全连接且无指定布局。
资源统计只聚合实际执行电路的门数/深度，不记录逐门连接或用这些指标恢复周期。

| 指标 | 逻辑电路（Oracle 为整体） | 实际执行基门电路 |
|---|---:|---:|
| Qubits / Classical Bits | 20 / 10 | 20 / 10 |
| Gate Count，不含测量 | 21 | 455 |
| Gate Depth，不含测量 | 3 | 195 |
| Two-Qubit Gate Count | 0（未展开 Oracle） | 183 |
| 总操作数，含测量 | 31 | 465 |
| Circuit Depth，含测量 | 4 | 195 |
| 参与量子门的 qubits | 20 | 20 |

逻辑双比特门数 0 不表示 Oracle 内没有双比特门。转译后的含测量深度与门深相同，
因为末端测量不延长该电路的最长路径。只有一个实际执行电路，因此表中基门电路就是
按官方资源指标选择的电路；这不是已完成的官方提交评分。

构造、转译、模拟、消元与验证合计约 0.207438 秒；进程峰值 RSS 为 108.227 MiB。
20 位双精度状态向量的振幅数组理论约 16 MiB，进程另含库与编译开销。
本轮无内存不足或超时。backend/basis 警告涉及硬件时长/误差参数；此处为理想无噪声模拟。

## 团队接口与后续集成

只读参考 Sicheng 的 `feature/mathematical-modeling:docs/TIER04_THEORY.md`，
blob `1e2308cd36e7ba38dea0965f3aba1532f013a283`；没有合并该分支。

Youyang 的共享模块位于另一分支的 `submissions/team3/classical_keystream.py`，
读取的 blob 为 `d0a2eea93dabffb6c5b0d9b485a17f6e6f746a0b`。
已核实接口 `decrypt_tier4(s, ciphertext_hex) -> str`，接受非零 10-bit 整数 s，
内部以 `format(s, "010b")` 保留前导零。

`solve()` 已预留对此接口的委托，缺少共享模块时在运行量子电路前抛出
`NotImplementedError`。本轮没有复制或重新编写经典解密模块。
集成后还需运行完整 `solve()` 并通过官方明文哈希校验。

## 复现

仓库根目录、官方版本环境下运行：

```bash
python -B -m unittest submissions.team3.tier04.test_gf2 submissions.team3.tier04.test_solution
python -B -m submissions.team3.tier04.validate_quantum
```

第一条命令全部使用合成数据/mock，覆盖 RREF、非对称周期、位序、零/重复/乱序方程、
rank 9 唯一性、欠定与满秩、输出初态约束、跨批次积累、末批裁剪、128 shots 上限、
异常不重试及待集成接口。第二条为 Linux 验证入口，先执行这些测试，再进行有界实测，
只保存安全汇总 JSON。不要为刷新报告而无意义地重测真实 Oracle。

本提交仅新增 Tier 4 文件，Tier 1–3、官方数据及工具均保持不变。
