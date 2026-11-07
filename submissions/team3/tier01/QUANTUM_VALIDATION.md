# Tier 1 量子电路实现与验证

作者：Junqi Sheng；分支：`feature/quantum-circuits`。
基准提交：`1623cf945dff3044580012d43b060521f14efd7c`。

## 当前结论

**量子部分 PASS；完整 `solve()` 尚待经典模块集成。**

在 Python 3.12.14、Qiskit 2.6.1、Aer 0.18.2 下，9 项人工数据单元测试通过，
随后执行真实 Tier 1 Oracle 的 BV 电路。Aer 实际执行 1 次、1 shot，
转译前官方 Oracle 计数为 1；从实际测量恢复了范围正确的 24-bit 整数。
本轮不保存或输出测量位串、密钥、密钥摘要、明文、状态向量或展开电路。

本分支没有 Youyang 的 `classical.py`。因此没有完成真实解密或明文哈希校验，
没有运行完整官方提交评分，也没有宣称 `solve()` 已通过。
“量子恢复通过”指电路执行及测量解码通过，并结合人工位序和电路结构测试验证；
它不等于已经完成对隐藏值的独立明文哈希验证。

## 电路与接口

- 25 个量子位：q0–q23 为输入，q24 为辅助位；一个 24 位经典寄存器。
- 输入全零起始，辅助位依次施加 X、H，制备为 |−⟩。
- 输入 H → 一次官方 Oracle → 输入 H → qj 测量到 cj；辅助位不测量。
- `helper.build_oracle()` 返回的电路作为整体转换并接入，不读取其门定义。
  按官方要求，在转译前调用 `helper.count_oracle_calls()`，结果必须为 1。
- 相位回踢编码奇偶函数；最终 counts 为 c23…c0，直接 `int(bitstring, 2)`，不反转。
  `measurement_to_key()` 严格接受单寄存器的 24 个二进制字符。
- `recover_key()` 使用 Aer statevector；先转译后测量，只返回内存中的整数。
  无暴力搜索、真实密钥常量或自动重试。模拟器内存上限 2048 MiB，最多 2 个线程。
- `build_circuit()` 提供同一主电路供展示；真正执行入口是 `recover_key()`。
  完成经典模块集成后，`solve()` 会调用该恢复函数，并把整数和密文交给
  `decrypt_tier1(key, ciphertext_hex)`，最终返回字符串。

## 团队接口与待集成项

只读参考，未合并其他分支：

- Sicheng：`feature/mathematical-modeling` 的 `docs/TIER01_THEORY.md`，
  blob `3bc36ff527ccd0001bf9b6427a6b8e04a7e59044`。
- Youyang：`feature/classical-implementation` 的
  `submissions/team3/tier01/classical.py`，
  blob `f163e0675d6352c0a777e805d3cf2613baa12410`。

经典模块负责整数到固定 3 字节大端序转换和重复 XOR 解密。本提交没有复制、
覆盖或重写该模块。缺少模块时，`solve()` 在启动 Aer 之前明确抛出
`NotImplementedError`；集成后仍需进行一次完整 `solve()` 与官方明文哈希校验。
人工 mock 委托测试仅验证参数与返回类型约定，不代表真实解密通过。

## 运行记录

完整、无秘密值的机器记录见 [quantum_validation.json](quantum_validation.json)。

| 指标 | 逻辑电路，Oracle 为整体 | 实际执行的基门电路 |
|---|---:|---:|
| 量子位 / 经典位 | 25 / 24 | 25 / 24 |
| Gate Count，不含测量 | 51 | 298 |
| Gate Depth，不含测量 | 4 | 44 |
| Two-Qubit Gate Count | 0（不展开 Oracle） | 151 |
| 总操作数，含测量 | 75 | 322 |
| Circuit Depth，含测量 | 5 | 45 |

逻辑电路的“双比特门 0”仅表示最外层没有独立双比特门，并非 Oracle 内没有双比特门。
执行基门为官方 `rz, sx, x, cx`；优化级别 1，转译种子 12345，全连接、无硬件布局。
统计只读取总数及深度，不查看真实 Oracle 的逐门连接或通过分解提取隐藏信息。
上述为本次执行电路的资源指标，不是完整官方评分结果。

本次构造、转译和运行合计 18.796839 秒；Linux 进程峰值 RSS 为 620.809 MiB。
25 位双精度状态向量的振幅数组理论约 512 MiB，实际进程另有库和编译开销。
Qiskit 提示同时指定 backend 与 basis 会忽略 backend 的时长/误差参数；这里使用无噪声
理想模拟和公开评分基门，不依赖硬件时长或误差参数。

## 复现

在仓库根目录、使用官方指定版本的 Python 虚拟环境运行：

```bash
python -B -m unittest submissions.team3.tier01.test_solution -v
python -B -m submissions.team3.tier01.validate_quantum
```

第一条命令全部使用人工数据和 mock，不加载真实 Oracle，也不执行 Aer。
覆盖前导零、最低/最高位、非对称位串、非法输入、电路顺序和线序、一次 Oracle、
模拟失败、异常 counts、经典模块缺失及接口委托。第二条先执行这些测试，
通过后才实际运行一次真实量子电路，并写入汇总 JSON。
发生错误即停止、不自动重试；若内存不足，应先调整资源而非重复运行。

环境安装和虚拟环境位于仓库外；官方 Oracle、Helper、hashes 和评分工具均未修改。
没有处理其他 Tier，也没有合并 main 或其他成员分支。
