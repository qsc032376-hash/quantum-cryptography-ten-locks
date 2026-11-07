# Tier 6：Grover 多解搜索与校验和筛选

## 14 位搜索空间与官方标记条件

[Tier 6](../tier06/README.md) 的密钥空间为 $\{0,1\}^{14}$，大小 $N=16384$。设 $C_0$ 是第一个密文字节，$D_{k,0}$ 是密钥 $k$ 对该字节的解密变换。Oracle 的唯一条件是

$$
f(k)=[D_{k,0}(C_0)=\mathrm Q],\qquad
A=\{k:f(k)=1\},\quad M=|A|.
$$

题目只给出约 64 个候选，未给出精确 $M$。Tier 5 的双字节检查在这里不适用；已知行格式和公开 checksum 都不应加入量子标记条件。

位序沿用 Tier 5：第 $j$ 个密钥位权重为 $2^j$，即整数 $k=\sum_{j=0}^{13}k_j2^j$。这里固定使用 14 位，前导零不改变传给 Toy Cipher 的密钥宽度。

## 多解旋转与迭代次数

令 $\lvert g\rangle=M^{-1/2}\sum_{k\in A}\lvert k\rangle$，$\lvert b\rangle=(N-M)^{-1/2}\sum_{k\notin A}\lvert k\rangle$。对于 $0<M<N$，初始均匀叠加为

$$
\lvert u\rangle=\cos\theta\,\lvert b\rangle+\sin\theta\,\lvert g\rangle,
\qquad \theta=\arcsin\sqrt{M/N}.
$$

$O_f$ 翻转整个标记子空间的相位，所以在有序基 $(\lvert b\rangle,\lvert g\rangle)$ 中为 $\operatorname{diag}(1,-1)$。扩散 $D=2\lvert u\rangle\langle u\rvert-I$ 关于 $\lvert u\rangle$ 反射；乘积 $G=DO_f$ 仍是 [Tier 5](TIER05_THEORY.md) 中的 $2\theta$ 旋转，角度改由 $M/N$ 决定。因此

$$
\begin{aligned}
G^r\lvert u\rangle
&=\cos((2r+1)\theta)\lvert b\rangle+\sin((2r+1)\theta)\lvert g\rangle,\\
P_{\rm marked}(r,M)&=\sin^2((2r+1)\theta).
\end{aligned}
$$

已知 $M$ 时，取最接近 $\pi/(4\theta)-1/2$ 的整数，可接近第一个概率峰。当 $M\ll N$，该步数约为 $(\pi/4)\sqrt{N/M}-1/2$。若 $M=64$，$r=12$，理想候选命中率约为 99.995%；这是用估计值推得的例子。实际 $M$ 较大时同一步数可能越过峰值，较小时可能尚未到峰值；增加迭代并不保证提高成功率。可按约 64 的估计从 12 步开始，并用不同迭代次数分批采样降低偏差风险；缺乏可信估计时，可在逐步扩大的有界区间内随机选择迭代次数。参见 [IBM Quantum：多解与未知解数](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/number-of-iterations#unknown-number-of-solutions)。

## 校验和筛选与正确密钥命中率

用测得的密钥 $k$ 作为候选。经典检查首字节是否为 `Q`，再用[公开 Helper 接口](../HELPERS.md)中的 `ToyCipher` 解密整段密文，计算

$$
\operatorname{checksum}(P)=\left(\sum_{i=0}^{L-1}P_i\right)\bmod 256,
$$

其中 $P_i$ 是明文的第 $i$ 个字节，$L$ 是字节数。只接受首字节及公开 checksum 都匹配的候选；题目保证标记集合内只有一个通过 checksum。该 checksum 用于赛题筛选，不是密码学认证。

Grover 对集合 $A$ 内的每个基态赋予相同振幅。设 $k_\star$ 是唯一通过筛选的密钥，则单次命中任一候选的概率为 $P_{\rm marked}$，命中 $k_\star$ 的概率为 $P_{\rm marked}/M$。理想情况下，同一迭代次数下独立采样 $S$ 个 shots，至少命中一次的概率为

$$
P_{\rm recover}(S)=1-\left(1-\frac{P_{\rm marked}}{M}\right)^S.
$$

如果每次使用不同的步数 $r_j$，未命中概率改为 $\prod_{j=1}^{S}(1-P_{\rm marked}(r_j,M)/M)$。以 $M=64,r=12$ 为例，正确密钥单次命中率约为 1.56%；191 个独立 shots 达到至少 95%，293 个达到至少 99%。这些都是理想模型的示例，不保证本题实际成功率。保留不同候选并避免重复解密可降低后处理成本；不应只检查频数最高的候选。

## 查询复杂度与可逆电路成本

在无结构黑盒模型下，找到任一标记候选，经典随机搜索需 $\Theta(N/M)$ 次首字节检查，Grover 需 $\Theta(\sqrt{N/M})$ 次相位查询。找出唯一通过 checksum 的密钥是另一项任务：当每个 shot 的标记命中概率为常数量级、且迭代步数接近首峰时，此“采样后做经典筛选”方案达到固定恢复概率需 $\Theta(M)$ 个 shots，总计 $\Theta(\sqrt{NM})$ 次相位查询，最多对 $O(M)$ 个不同的标记候选做完整解密与校验，每个候选需处理 $L$ 字节。直接经典黑盒搜索唯一正确密钥需 $\Theta(N)$ 次首字节检查，可只对通过者做完整解密与校验。这些比较不排除利用 Toy Cipher 公开结构的其他经典方法。

实际 Oracle 在 8 个工作位上制备 $C_0$，用 `mask_gates(14)` 写入首字节掩码异或，再将 `SBOX_GATES` 应用于两个半字节，并通过 `PERM` 重映射比较线路。对匹配 `Q` 的工作态施加相位 $-1$，再把解密与制备逆向执行。每次迭代包含正向和逆向的字节计算、一次多控比较相位及 14 位密钥扩散；每个 shot 的 Oracle 查询数等于迭代次数，所有 shots 的查询数相加。

若用 $g_{\rm byte}$ 和 $d_{\rm byte}$ 表示字节制备及可逆计算的逻辑门数与深度，直接串接时单次迭代的逻辑门数为 $2g_{\rm byte}+g_{\rm phase}+g_{\rm diff}$，深度上界为 $2d_{\rm byte}+d_{\rm phase}+d_{\rm diff}$，不含初始叠加与测量。这是结构估计；多控门分解、工作位选择及转译会改变实际双比特门数、总门数与深度。生成可逆电路、转译以及经典后处理的成本应分别记录。

根据公开门表，首字节正向计算用 16 个 CX、8 个 CCX 的掩码和 12 个半字节替换门。加上逆向计算，每次迭代的掩码和替换共 72 个逻辑门，另计密文字节制备及清零、比较相位和扩散。这里不需要第二字节的密钥旋转或位置常量。

## Implementation Notes

- Junqi 可从 14 个密钥位和 8 个字节工作位的逻辑布局开始；直接在工作位上做比较相位时无需 Tier 5 的跨字节标志位。22 位是基础布局，分解多控门时可能需要额外辅助位，资源尚未验证。
- 只标记首字节 `Q`，每次 Oracle 结束后清零工作位；扩散仅作用于密钥位。在 `solve()` 中用 Aer 执行，将完整解密与 checksum 留在经典后处理。
- 只测量 14 个密钥位，令密钥位 $j$ 对应单一经典寄存器的第 $j$ 位。按 [Qiskit 的计数字符串位序](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering)，左侧是第 13 位、右侧是第 0 位。将字符串直接按二进制读成整数 $k$，去重后以 `ToyCipher(k, 14)` 验证首字节并解密整段；对明文原始字节调用 `helper.checksum(data)`，与公开值比较。若本批没有通过者，可在预定预算内继续采样。
- 记录每批迭代次数与 shots、候选数、去重后的校验次数，以及转译后的活跃 qubit 数、门数和深度。不要把测得的不同候选数直接当作精确的 $M$。
