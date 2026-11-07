# Tier 1：Bernstein–Vazirani 算法的数学证明

## Hidden String 与 Boolean Function

令 $n=24$，位运算均在有限域 $\mathbb F_2=\{0,1\}$ 上进行。设隐藏字符串与输入分别为

$$
s=(s_0,s_1,\ldots,s_{23}),\quad x=(x_0,x_1,\ldots,x_{23})\in\mathbb F_2^{24}.
$$

题目定义的 Boolean 函数是

$$
f_s(x)=s\cdot x=\bigoplus_{j=0}^{23}s_jx_j
=\sum_{j=0}^{23}s_jx_j\pmod 2.
$$

## Oracle Definition

量子 Oracle 作用于输入寄存器和一个辅助量子比特：

$$
U_f|x\rangle|y\rangle=|x\rangle|y\oplus f_s(x)\rangle.
$$

## Initial Quantum State

输入寄存器有 24 个量子比特，辅助量子比特初始化为 $|1\rangle$：

$$
|\psi_0\rangle=|0\rangle^{\otimes 24}|1\rangle.
$$

## Hadamard Transformation

对所有量子比特施加 Hadamard 门。由

$$
H|0\rangle=\frac{|0\rangle+|1\rangle}{\sqrt2},\qquad
H|1\rangle=\frac{|0\rangle-|1\rangle}{\sqrt2}=|-\rangle,
$$

得到输入均匀叠加态及辅助态：

$$
|\psi_1\rangle=\frac{1}{\sqrt{2^{24}}}
\sum_{x\in\mathbb F_2^{24}}|x\rangle|-\rangle.
$$

## Phase Kickback

对任意 $b\in\{0,1\}$，有 $X^b|-\rangle=(-1)^b|-\rangle$。因此

$$
\begin{aligned}
U_f\bigl(|x\rangle|-\rangle\bigr)
&=|x\rangle X^{f_s(x)}|-\rangle\\
&=(-1)^{f_s(x)}|x\rangle|-\rangle\\
&=(-1)^{s\cdot x}|x\rangle|-\rangle.
\end{aligned}
$$

由线性性，一次 Oracle 查询后，状态为

$$
|\psi_2\rangle=\frac{1}{\sqrt{2^{24}}}
\sum_x(-1)^{s\cdot x}|x\rangle|-\rangle.
$$

## Final Hadamard Transformation

对输入寄存器再次施加 Hadamard。对任意 $x$，

$$
H^{\otimes 24}|x\rangle=\frac{1}{\sqrt{2^{24}}}
\sum_{z\in\mathbb F_2^{24}}(-1)^{x\cdot z}|z\rangle.
$$

代入得

$$
\begin{aligned}
|\psi_3\rangle
&=\frac{1}{2^{24}}\sum_z
\left(\sum_x(-1)^{s\cdot x+x\cdot z}\right)|z\rangle|-\rangle\\
&=\frac{1}{2^{24}}\sum_z
\left(\sum_x(-1)^{x\cdot(s\oplus z)}\right)|z\rangle|-\rangle.
\end{aligned}
$$

## Correctness Proof

内层求和按位分解：

$$
\sum_x(-1)^{x\cdot(s\oplus z)}
=\prod_{j=0}^{23}\left(1+(-1)^{s_j\oplus z_j}\right).
$$

当 $z=s$ 时，所有因子均为 $2$，乘积为 $2^{24}$；当 $z\ne s$ 时，至少一个因子为 $0$。因此

$$
\frac{1}{2^{24}}\sum_x(-1)^{x\cdot(s\oplus z)}
=\begin{cases}1,&z=s,\\0,&z\ne s.\end{cases}
$$

故最终状态为

$$
\boxed{|\psi_3\rangle=|s\rangle|-\rangle}.
$$

在理想、无噪声模型中，测量输入寄存器得到 $s$ 的概率为 $1$。

## Classical vs. Quantum Query Complexity

量子算法只调用一次 $U_f$；其余步骤是与 $s$ 无关的 Hadamard 门和测量。经典确定性算法的每次查询只给出一个关于 $s$ 的模 2 线性方程。少于 24 次查询时，方程组的秩最多为 23，至少两个不同的隐藏串与回答一致，因而无法保证区分。分别查询 24 个单位向量即可确定各个 $s_j$，所以经典确定性算法在最坏情况下恰需 24 次查询。

这是黑盒查询复杂度的比较；实际 Qiskit 运行还需考虑门数、编译、采样和噪声等开销。

## Qubit Ordering and Big-Endian Key Conversion

题目规定输入 qubit $j$ 对应整数 $s$ 的第 $j$ 位，权重为 $2^j$：

$$
s_{\mathrm{int}}=\sum_{j=0}^{23}s_j2^j.
$$

通常的二进制字符串从左到右写为 $s_{23}\cdots s_1s_0$。若 qubit $j$ 测量到 classical bit $j$，Qiskit 的计数字符串通常以高位在左的顺序显示，即 `c23...c0`；映射变化时，须按实际经典寄存器映射检查。

题目使用 `s.to_bytes(3, "big")`，故三个字节依次包含

$$
(s_{23}\cdots s_{16}),\quad(s_{15}\cdots s_8),\quad(s_7\cdots s_0).
$$

qubit 0 对应整数最低位，第一个密钥字节则包含最高的 8 位。

## Circuit Requirements for Junqi

- 使用 24 个输入量子比特和第 24 号辅助量子比特；辅助位从 $|1\rangle$ 经 Hadamard 制备为 $|-\rangle$。
- 对所有输入位施加 Hadamard，调用题目提供的 Oracle 恰好一次，再对输入位施加 Hadamard 并测量。
- 明确量子比特到经典位的映射，核对输出位序与 big-endian 三字节转换。
- 理想结果确定；实际模拟或硬件环境的误差应与理想证明分开说明。

## Implementation Notes

测量结果的字符串顺序取决于经典寄存器布局和测量映射；若 qubit $j$ 对应 classical bit $j$，单个 24 位寄存器显示为 `c23...c0`。Oracle 必须恰好调用一次，并按题目要求在转译前使用 `helper.count_oracle_calls(circuit)` 检查。
