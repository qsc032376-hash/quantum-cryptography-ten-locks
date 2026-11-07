# Tier 7：量子相位估计的数学分析

## 题目模型与密钥编码

按 [Tier 7 题目说明](../tier07/README.md)，给定单量子比特酉算子 $U=V\operatorname{diag}(1,e^{2\pi i\phi})V^\dagger$ 和目标特征态 $\lvert u\rangle=V\lvert 1\rangle$。因此

$$
U\lvert u\rangle=e^{2\pi i\phi}\lvert u\rangle,\qquad
\phi=\frac{k}{2^{14}},\qquad k\in\{0,\ldots,2^{14}-1\}.
$$

$\phi$ 以一整圈为单位，按模 1 解释；对应弧度为 $2\pi\phi$。令 $m=14$、$N=2^m$，并写 $k=\sum_{j=0}^{m-1}k_j2^j$。则 $\phi=\sum_{\ell=1}^{m}k_{m-\ell}2^{-\ell}$，所以相位的小数点后 14 位正好是从最高位到最低位排列的密钥字符 $k_{13}\cdots k_0$。题目要求将测量整数 $k$ 以 `format(k, "014b")` 编码，保留前导零，再交给 `keystream(key_bits, length)` 生成等长的 SHA-256 密钥流。

## Hadamard、受控幂与相位回踢

用公开接口 `helper.build_eigenstate()` 制备目标位，对初始为零的 $m$ 个计数位施加 $H^{\otimes m}$，得到

$$
\lvert\Psi_0\rangle
=\frac1{\sqrt N}\sum_{x=0}^{N-1}\lvert x\rangle\lvert u\rangle,
\qquad x=\sum_{j=0}^{m-1}x_j2^j.
$$

令权重为 $2^j$ 的计数位 $j$ 控制 $U^{2^j}$。由特征值关系反复应用 $U$，在计算基的分支上有

$$
\operatorname{C}(U^{2^j})\lvert x_j\rangle\lvert u\rangle
=\lvert x_j\rangle U^{x_j2^j}\lvert u\rangle
=e^{2\pi i\phi x_j2^j}\lvert x_j\rangle\lvert u\rangle.
$$

目标位仍在 $\lvert u\rangle$，相位成为不同计数分支之间的相对相位。乘上所有控制位产生的因子，得到

$$
\lvert\Psi_1\rangle
=\frac1{\sqrt N}\sum_{x=0}^{N-1}e^{2\pi i\phi x}\lvert x\rangle\lvert u\rangle.
$$

## 逆量子傅里叶变换与精确测量

采用正号的傅里叶约定 $F_N\lvert k\rangle=N^{-1/2}\sum_x e^{2\pi i xk/N}\lvert x\rangle$。在计数寄存器上施加 $F_N^\dagger$ 后，结果 $y$ 的振幅为

$$
a_y=\frac1N\sum_{x=0}^{N-1}e^{2\pi i x(\phi-y/N)}.
$$

在 Tier 7 中 $\phi=k/N$。当 $y=k$ 时，和式的每一项都是 1，因此 $a_k=1$。当 $y\ne k$ 时，令 $z=e^{2\pi i(k-y)/N}$，则 $z\ne1$ 而 $z^N=1$，故 $\sum_{x=0}^{N-1}z^x=(1-z^N)/(1-z)=0$。因此输出态为 $\lvert k\rangle\lvert u\rangle$，**理想单次测量得到 $k$ 的概率为 1**。这一结论要求初态是题目给定的特征态，且受控幂、逆 QFT 和位序均正确。

## 非精确相位的分布与误差

一般情况下，若 $N\phi$ 不是整数，令 $\delta_y=\phi-y/N$。对振幅的等比数列取模平方：

$$
P(y)=\lvert a_y\rvert^2
=\frac{\sin^2(\pi N\delta_y)}{N^2\sin^2(\pi\delta_y)}.
$$

估计值为 $\widehat\phi=y/N$；误差用圆周距离 $\min_{t\in\mathbb Z}|\phi-\widehat\phi-t|$ 衡量，以处理相位在 0 与 1 之间的回绕。最接近相位的格点 $y_\star$ 满足 $\epsilon=\min_{t\in\mathbb Z}|\delta_{y_\star}-t|\le1/(2N)$。利用 $0\le\pi N\epsilon\le\pi/2$ 上的 $\sin(\pi N\epsilon)\ge2N\epsilon$，以及 $\sin(\pi\epsilon)\le\pi\epsilon$，可得

$$
P(y_\star)\ge\frac4{\pi^2}\approx40.5\%,\qquad
\min_{t\in\mathbb Z}|\phi-y_\star/N-t|\le 2^{-(m+1)}.
$$

这给出最近格点的理想概率下界和对应误差，并不保证每次测量都落在该格点。对距真实相位 $d=N\min_{t\in\mathbb Z}|\delta_y-t|$ 个格点间隔的结果，由 $\sin(\pi d/N)\ge 2d/N$ 可得 $P(y)\le 1/(4d^2)$，说明较远结果的概率随距离衰减。增加计数位可细化格点，重复独立实验可用来检验分布。Tier 7 承诺相位可精确表示，测到多个结果时不能直接归因于非精确相位。参见 [IBM Quantum：相位估计推导](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/phase-estimation-procedure)。

## 查询模型、门数与深度

- **寄存器。** 标准并行读出的 QPE 使用 14 个计数 qubit 和 1 个目标 qubit，共 15 个逻辑 qubit，不含任何额外的分解或路由开销；另用 14 个经典位读取计数寄存器。
- **受控幂。** 若 $U$ 只以可控黑盒提供，用重复的受控 $U$ 合成各幂，每个 shot 的基本查询数为 $\sum_{j=0}^{m-1}2^j=2^m-1=16383$。14 个受控幂只是电路块的数量。在 [官方允许的矩阵构造](../tier07/README.md#rules-for-this-tier) 中，可对给定的 $2\times2$ 酉矩阵逐次平方，生成 $m$ 个幂，再将每个受控幂合成为双量子比特门块。固定矩阵维度下这用 $O(m)$ 次矩阵乘法，不含精度、门综合与转译成本。它也不是黑盒中的免费幂查询。
- **逆 QFT。** 精确的标准分解含 $m$ 个 H、$m(m-1)/2$ 个受控相位和 $\lfloor m/2\rfloor$ 个位反转 SWAP。这里是 14 个 H、91 个受控相位、7 个 SWAP，另有初始叠加的 14 个 H。逆 QFT 的逻辑门数为 $\Theta(m^2)$。在全连接、允许不相交门并行的模型中，受控相位可按两端位编号之和分层，并将 H 放在相应相位层之间，深度为 $\Theta(m)$。受控幂块共用目标位，直接串接时深度相加。受控相位、SWAP、受控幂在转译后均可能分解成多道门，硬件路由也会增加双比特门数与深度；上述门数只是理论分解。

## 经典比较与实验局限

若完整矩阵可读，经典线性代数适用于小矩阵的相位分析，但直接取特征值作为本题答案违反规则。若只能使用相干受控黑盒和对应特征态，QPE 可用相位回踢做傅里叶读出；在基本受控 $U$ 查询模型中，标准电路达到格点分辨率 $\varepsilon=2^{-m}$ 时使用 $\Theta(1/\varepsilon)$ 次查询。作为对照，若每次实验只使用一次受控 $U$，分别测计数位的 $X$ 和 $Y$ 来估计 $\cos(2\pi\phi)$ 和 $\sin(2\pi\phi)$，再用经典样本均值估相位，以固定置信度达到 $O(\varepsilon)$ 误差通常需要 $O(1/\varepsilon^2)$ 个样本。这是单步干涉与经典统计的基线，仍使用量子实验。把受控幂当成可直接构造的块则是另一种成本模型，不能据此断言量子运行时间更短。

理想 Aer 模拟可以检验算法与位序；有限精度的矩阵求幂和门综合可能造成小误差。真实硬件还会受特征态制备误差、受控门误差、退相干和读出噪声影响。多 shots 有助于估计输出分布，不能修复错误的全局相位、傅里叶符号或位映射。本节没有模拟或实测数据。

## Implementation Notes

- Junqi 可用[公开 Helper](../HELPERS.md#tier07helperpy) 的 `build_eigenstate()` 制备目标位，用 `build_unitary()` 获取给定的 $U$。以计数位 $j$ 控制 $U^{2^j}$，逆 QFT 只作用于计数位。
- 保留 $U$ 的全局相位。若误用 $e^{i\alpha}U$，在非受控场景是全局相位，但受控后仅作用于控制位为 1 的分支，估得的相位将变为 $\phi+\alpha/(2\pi)\pmod1$。若用公开矩阵构造幂，只做保留相位的矩阵乘法与门综合，不从矩阵求出隐藏特征值。
- 明确采用完整的 $F_N^\dagger$ 位序。若计数 qubit $j$ 测到单一经典寄存器的第 $j$ 位，按 [Qiskit 位序](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering)，计数字符串为 $k_{13}\cdots k_0$，可直接按二进制读成整数。若使用省略 SWAP 的实现，先核对置换在逆 QFT 的输入端还是输出端，再补偿相应的控制映射或测量映射。
- 后续在 `solve()` 中用 Aer 执行并记录测量结果、shots、受控幂构造方式和转译后的资源。解密时使用官方的 14 位编码；本轮只验证理论公式和文档格式。
