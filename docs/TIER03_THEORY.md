# Tier 3：Deutsch–Jozsa 算法的数学分析

在题目的承诺下，每个 Oracle 只需调用一次。理想无噪声时，测量输入寄存器得到全零，当且仅当该 Oracle 对应常数函数。

## 常数与平衡 Boolean 函数

令 $n=6$，函数 $f:\{0,1\}^n\to\{0,1\}$ 满足以下两种情况之一：

- **常数（Constant）**：存在 $c\in\{0,1\}$，使得对所有输入 $x$ 均有 $f(x)=c$。
- **平衡（Balanced）**：恰有 $2^{n-1}$ 个输入使 $f(x)=0$，其余 $2^{n-1}$ 个输入使 $f(x)=1$。

## 量子 Oracle、初始叠加态与相位回踢

Oracle 作用在 $n$ 个输入位和一个辅助位上，其中 $\oplus$ 表示异或：

$$
U_f\lvert x,y\rangle=\lvert x,y\oplus f(x)\rangle.
$$

从 $\lvert 0^n\rangle\lvert 1\rangle$ 出发，对所有量子比特施加 Hadamard 门。输入位各自变为 $(\lvert 0\rangle+\lvert 1\rangle)/\sqrt{2}$，辅助位变为 $\lvert-\rangle=(\lvert 0\rangle-\lvert 1\rangle)/\sqrt{2}$。将输入位的张量积展开，得到均匀叠加：

$$
\lvert\psi_1\rangle=2^{-n/2}\sum_{x\in\{0,1\}^n}\lvert x\rangle\lvert-\rangle.
$$

因为 $X\lvert-\rangle=-\lvert-\rangle$，所以 $X^{f(x)}\lvert-\rangle=(-1)^{f(x)}\lvert-\rangle$。调用一次 Oracle 后，辅助位保持原状，函数值进入输入态的相位：

$$
\lvert\psi_2\rangle=2^{-n/2}\sum_x(-1)^{f(x)}\lvert x\rangle\lvert-\rangle.
$$

## 最终 Hadamard 变换与正确性

只对输入寄存器再施加 $H^{\otimes n}$。令 $x\cdot z=\sum_{j=0}^{n-1}x_jz_j\bmod 2$，则

$$
H^{\otimes n}\lvert x\rangle=2^{-n/2}\sum_z(-1)^{x\cdot z}\lvert z\rangle.
$$

代入并按输出 $z$ 合并振幅，得到

$$
\lvert\psi_3\rangle=\sum_{z\in\{0,1\}^n}
\left(2^{-n}\sum_x(-1)^{f(x)+x\cdot z}\right)
\lvert z\rangle\lvert-\rangle.
$$

当 $z=0^n$ 时，$x\cdot z=0$，因此全零态的振幅及测量概率为

$$
\alpha_{0^n}=2^{-n}\sum_x(-1)^{f(x)},\qquad
P(0^n)=\lvert\alpha_{0^n}\rvert^2.
$$

- 若 $f$ 为常数，所有项均为 $(-1)^c$，所以 $\alpha_{0^n}=(-1)^c$，全零概率为 $1$。
- 若 $f$ 平衡，求和中恰有一半 $+1$ 和一半 $-1$，所以 $\alpha_{0^n}=0$，所有概率落在非零结果上。

所以在承诺成立且无噪声时，单次测量就能确定分类。

## 经典与量子查询复杂度

量子算法对每个函数只调用一次 $U_f$。经典确定性算法最坏需要 $2^{n-1}+1$ 次查询：前 $2^{n-1}$ 个不同输入若返回同一值，这些回答仍同时符合常数函数和平衡函数。再查询一个不同输入，若结果仍相同，就超过平衡函数允许的同值数量；若出现两个不同的值，则函数必为平衡。Tier 3 中，每个 Oracle 的最坏查询次数为经典 **33 次**、量子 **1 次**。

## 24 个 Oracle 的分类与密钥格式

按 [Tier 3 题目说明](../tier03/README.md)，对 Oracle `00` 到 `23` 分别运行一条电路，每条调用对应 Oracle 一次。第 $i$ 条电路若测得全零，记密钥字符 `0`；若测得非零，记 `1`。按编号 $0,1,\ldots,23$ 拼接成 24 字符的二进制字符串 `key_bits`，保留前导零。单条电路内的测量位顺序不影响全零判定；密钥字符的位置由 Oracle 编号决定。

按[公共解密接口](../HELPERS.md)，将 `ciphertext_hex` 用 `bytes.fromhex` 转成密文字节。调用 `keystream(key_bits, len(ciphertext))` 生成等长的 SHA-256 密钥流，再用 `xor_bytes(ciphertext, stream)` 得到明文字节。将其解码为字符串，由 `solve()` 返回。

## Qubit 数量与电路简洁度评分

每条电路使用 6 个输入 qubit 和 1 个辅助 qubit，共 7 个；24 条电路共使用 24 次 Oracle。输入位上的两组 Hadamard 可各自并行，标准构造不在 Oracle 之外添加双比特门。实际深度和门数以转译结果为准。

按[评分规则](../SCORING.md)，简洁度取 `solve()` 在 Aer 上执行的电路中转译后双比特门最多的一条，数量相同时取深度较大的电路。双比特门数、深度、总门数、活跃 qubit 数的权重分别为 40%、30%、20%、10%；Oracle 内的门也计入。查询次数、执行次数和 shots 应单独报告，不直接计入简洁度公式。

## Implementation Notes

- 输入是 qubit 0–5，辅助位是 qubit 6。从默认全零态开始，对辅助位施加 X，再对全部 7 位施加 H。
- 通过 `helper.build_oracle(i)` 加入对应 Oracle，转译前用 `helper.count_oracle_calls(circuit)` 确认调用次数为 1。随后只对 0–5 号位施加 H，并只测量这 6 位。
- 在 `solve()` 中将每个 Oracle 的电路转译后交给 Aer 执行。根据测量结果分类，不检查 Oracle 的门分解或矩阵；按 Oracle 编号收集分类结果。
