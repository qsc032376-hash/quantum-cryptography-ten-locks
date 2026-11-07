# Tier 2：BB84 数学模型与链路分析

## BB84 量子态与测量基

Alice 随机选择比特 $a\in\{0,1\}$ 和制备基 $b_A\in\{Z,X\}$，制备对应量子态：

$$
Z:\quad 0\mapsto|0\rangle,\quad 1\mapsto|1\rangle;\qquad
X:\quad 0\mapsto|+\rangle,\quad 1\mapsto|-\rangle,
$$

其中 $|\pm\rangle=(|0\rangle\pm|1\rangle)/\sqrt2$。Bob 不知道 Alice 的制备基，先选择测量基 $b_B$ 并测量；之后 Alice 公布制备基，双方筛选基相同的位置。题目以 `0` 表示 $Z$ 基，以 `1` 表示 $X$ 基。

## Born Rule 与测量概率

对制备态 $|\psi\rangle$ 和测量基中的态 $|m\rangle$，Born 规则给出

$$
P(m\mid\psi)=|\langle m|\psi\rangle|^2.
$$

理想无噪声情况下，同基态正交，不同基之间的重叠概率均为 $1/2$。因此

$$
P(B=a\mid b_B=b_A)=1,\qquad
P(B=0\mid b_B\ne b_A)=P(B=1\mid b_B\ne b_A)=\tfrac12.
$$

不匹配基的测量结果不能可靠地重建 Alice 的比特。

## Intercept-Resend Attack 与 QBER

题目中，Eve 截获其中一条链路的每个量子比特，随机选择 $Z$ 或 $X$ 基测量，再发送测量后的态。假设 Eve 独立、等概率选基，且不存在其他噪声，在 Alice 和 Bob **基匹配**的位置：

- Eve 的基与 Alice 相同的概率为 $1/2$，理想情况下不引入错误。
- Eve 的基不同的概率为 $1/2$；此时 Bob 的错误概率为 $1/2$。

因此，筛选后比特的理论量子比特错误率为

$$
\mathrm{QBER}=P(B\ne A\mid b_B=b_A)
=\tfrac12\cdot\tfrac12=\boxed{25\%}.
$$

## 有限样本估计与链路判别

对每条链路，设 $C$ 为 Alice 和 Bob 的基匹配且属于公开检查集的位置；当 $|C|>0$ 时，样本错误率为

$$
\widehat{\mathrm{QBER}}=
\frac{\sum_{i\in C}\mathbf 1[B_i\ne A_i]}{|C|}.
$$

比较两条链路的检查错误率，选择较低者作为未被窃听的链路。有限样本的结果不一定恰好为 $0\%$ 或 $25\%$；这两个数是上述理想模型下的参考，而非题目规定的固定判定阈值。若没有可用检查位置，则该估计无法计算。

## 公开接口与密钥重建

1. 对每条链路先盲选所有测量基，使用一个 `Channel(name)` 实例，并用 `receive_all(circuits)` 为每个位置测量一次。
2. 在接收完成后调用该链路的 `finish()`，获得 Alice 的基 `alice_bases`、公开检查比特 `check_bits` 和协调数据 `reconcile`。调用后不能再通过该实例接收。
3. 只用基匹配的公开检查位置比较两条链路的错误率，选择错误率较低者。
4. 对选中链路，保留**基匹配且不属于公开检查集**的测量结果，并用原始位置索引将其组织为 `{index: bit}`。
5. 将该映射及协调数据传给 `helper.reconcile(key_bits_by_index, reconcile_data)`。该接口利用题目提供的公开信息求解 $\mathbb F_2$ 上的线性方程组，返回密钥字节；独立方程不足时会报错。错误输入也可能产生错误密钥。
6. 使用恢复的密钥与密文逐字节异或，可得到明文。

## 理论协议与赛题实现的区别

上述 $25\%$ 是特定截获重发模型和理想条件下的期望，不是对所有攻击或实际噪声的通用结论。赛题的固定密钥和公开协调数据是为此练习设计的简化机制；该协调接口本身不构成完整的实际 BB84 安全协议，也不保证所选链路或输入正确。
