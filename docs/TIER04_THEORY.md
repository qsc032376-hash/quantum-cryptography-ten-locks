# Tier 4：Simon 算法的数学模型与正确性证明

Simon 算法每次采样得到一条关于隐藏串的模 2 方程。Tier 4 的隐藏串有 10 位，收集到 9 条线性独立的方程即可唯一确定它。

## 二对一函数与隐藏 XOR 周期

令 $n=10$，隐藏串 $s\in\mathbb F_2^n\setminus\{0\}$，函数 $f:\mathbb F_2^n\to\mathbb F_2^n$ 满足

$$
f(x)=f(x')\iff x'=x\ \text{或}\ x'=x\oplus s.
$$

这里 $\oplus$ 是逐位异或。$f(x)=f(x\oplus s)$ 是题目给定的周期性质；由于 $s\ne 0$，$x$ 与 $x\oplus s$ 不同，所以每个可达输出恰好对应两个输入。

## Oracle 与量子态演化

题目提供的 Oracle 在输出寄存器初始化为全零时满足 $U_f\lvert x,0^n\rangle=\lvert x,f(x)\rangle$。从 $\lvert 0^n,0^n\rangle$ 开始，只对输入寄存器施加 $H^{\otimes n}$，再调用一次 Oracle：

$$
\lvert 0^n,0^n\rangle
\xrightarrow{H^{\otimes n}\otimes I}
2^{-n/2}\sum_x\lvert x,0^n\rangle
\xrightarrow{U_f}
2^{-n/2}\sum_x\lvert x,f(x)\rangle.
$$

如果此时测量输出寄存器并得到 $f(a)$，仅有两个输入分量保留。归一化后，输入寄存器的条件态为

$$
\lvert\psi_a\rangle=\frac{\lvert a\rangle+\lvert a\oplus s\rangle}{\sqrt 2}.
$$

## 最终 Hadamard 变换与测量概率

记 $x\cdot y=\sum_{j=0}^{n-1}x_jy_j$，其中求和在 $\mathbb F_2$ 上进行。利用 $H^{\otimes n}\lvert x\rangle=2^{-n/2}\sum_y(-1)^{x\cdot y}\lvert y\rangle$，对输入态 $\lvert\psi_a\rangle$ 再施加一次 $H^{\otimes n}$ 后，测量结果 $y$ 的振幅为

$$
\begin{aligned}
\alpha_y
&=2^{-(n+1)/2}\left[(-1)^{a\cdot y}+(-1)^{(a\oplus s)\cdot y}\right]\\
&=2^{-(n+1)/2}(-1)^{a\cdot y}\left[1+(-1)^{s\cdot y}\right].
\end{aligned}
$$

若 $s\cdot y=1$，两项相消；若 $s\cdot y=0$，括号等于 2。因此

$$
P(y\mid f(a))=\lvert\alpha_y\rvert^2=
\begin{cases}
2^{-(n-1)}, & y\cdot s=0\pmod 2,\\
0, & y\cdot s=1\pmod 2.
\end{cases}
$$

由于 $s\ne0$，$s^\perp=\{y:y\cdot s=0\}$ 的维数为 $n-1$，故测量在该子空间上均匀分布。这一分布与 $f(a)$ 无关；忽略输出寄存器等同于对所有输出结果的条件分布取平均，所以实际电路可以省略输出寄存器的测量。

## GF(2) 高斯消元与采样成功率

将每次采样得到的 $y$ 作为矩阵 $Y$ 的一行，求解 $Ys=0$。在 $\mathbb F_2$ 上，用交换行和逐位异或进行高斯消元。若 $\operatorname{rank}Y=r$，零空间维数为 $n-r$，共有 $2^{n-r}-1$ 个非零候选。达到 $r=n-1=9$ 时，零空间只包含 $0$ 和真实的 $s$。零行、重复行及其他线性相关行都不增加秩。

理想无噪声时，令 $m$ 个 shots 彼此独立。在 $s^\perp$ 的任一组基下，$Y$ 的行等价于均匀采样的 9 位坐标。其 $m\times 9$ 坐标矩阵的列均匀独立；已有 $j$ 个独立列时，下一列落入它们张成空间的概率为 $2^{j-m}$。因此对 $m\ge9$，

$$
P(\operatorname{rank}Y=9)=\prod_{j=0}^{8}(1-2^{j-m}).
$$

9 个 shots 不保证得到 9 条独立方程；16 个 shots 达到秩 9 的概率超过 99%。若秩不足，可继续采样直至达到 9。

## 查询次数与实际运行成本

标准电路每个 shot 调用一次 Oracle。将同一条电路一次交给 Aer 执行 $m$ 个 shots，在查询模型中仍是 $m$ 次 Oracle 查询，得到 $m$ 条方程记录，但独立方程数只有 $\operatorname{rank}Y$。若当前秩为 $r<n-1$，下一次采样增加秩的概率为 $1-2^{r-(n-1)}\ge1/2$，所以达到目标秩平均需要 $O(n)$ 次查询。

在相同的黑盒模型下，经典随机算法要达到固定的成功率，需要 $\Theta(2^{n/2})$ 次查询，量级来自寻找一对输出相同的输入。查询复杂度不计 Oracle 的门数、转译后的深度、Aer 模拟耗时或经典消元开销。参见 [IBM Quantum：Simon 算法](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/simon-algorithm)。

## Tier 4 电路布局与密钥编码

按 [Tier 4 题目说明](../tier04/README.md)与 [Helper 接口](../HELPERS.md#tier04helperpy)，电路共使用 20 个 qubit：0–9 是输入位，10–19 是必须初始化为全零的输出位。题目要求从 Oracle 电路的测量结果恢复 $s$，并在 `solve()` 中实际使用 Aer；整关没有一次调用的上限。

消元矩阵的第 $j$ 列对应输入 qubit $j$。将恢复的向量解释为整数 $s_{\mathrm{int}}=\sum_{j=0}^9s_j2^j$，按 `format(s_int, "010b")` 生成高位在左且保留前导零的 10 位字符串。该字符串是 `keystream` 的输入。

## Implementation Notes

- 使用公开的 `helper.build_oracle()`。仅在输入位上施加两组 Hadamard，组间加入一次 Oracle，最后只测量输入位。
- 明确 qubit 到经典位的映射。若 qubit $j$ 测到单一经典寄存器的第 $j$ 位，结果字符串从左到右为 $y_9\cdots y_0$；将其按对应的列顺序送入消元。
- 在 `solve()` 中转译并用 Aer 采样。仅在秩达到 9 时取零空间的唯一非零向量；分别记录 shots 数、实际得到的秩及按 shots 计的 Oracle 查询次数。
