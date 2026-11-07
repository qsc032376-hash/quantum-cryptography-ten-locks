# Tier 5：Grover 唯一解搜索的数学分析

## 搜索空间与目标

[Tier 5](../tier05/README.md) 的密钥空间为 $\{0,1\}^{10}$，大小 $N=1024$。记 $C_0,C_1$ 为前两个密文字节，$D_{k,i}$ 为密钥 $k$ 对第 $i$ 个字节的解密变换。标记函数为

$$
f(k)=[D_{k,0}(C_0)=\mathrm{Q}]\land[D_{k,1}(C_1)=\mathrm{C}].
$$

题目保证只有一个 $k_\star$ 通过两项检查。只检查第一个字节会标记多个候选。

## 相位标记、扩散与二维旋转

令 $\lvert t\rangle=\lvert k_\star\rangle$，$\lvert b\rangle$ 为其余 $N-1$ 个密钥基态的归一化均匀叠加。用 10 个 Hadamard 门制备初态：

$$
\lvert u\rangle=N^{-1/2}\sum_k\lvert k\rangle
=\cos\theta\,\lvert b\rangle+\sin\theta\,\lvert t\rangle,
\qquad \sin\theta=N^{-1/2}.
$$

相位 Oracle $O_f\lvert k\rangle=(-1)^{f(k)}\lvert k\rangle$ 只翻转目标的符号。扩散算子 $D=2\lvert u\rangle\langle u\rvert-I$ 关于初态方向反射。两者均保持这两个基向量张成的平面。在有序基 $(\lvert b\rangle,\lvert t\rangle)$ 中，$O_f=\operatorname{diag}(1,-1)$，且

$$
\begin{aligned}
D&=\begin{pmatrix}\cos 2\theta&\sin 2\theta\\\sin 2\theta&-\cos 2\theta\end{pmatrix},\\
G=DO_f&=\begin{pmatrix}\cos 2\theta&-\sin 2\theta\\\sin 2\theta&\cos 2\theta\end{pmatrix}.
\end{aligned}
$$

所以每次迭代旋转 $2\theta$，从初始角 $\theta$ 出发，执行 $r$ 次后的目标测量概率为

$$
P_r=\sin^2\bigl((2r+1)\theta\bigr).
$$

取最接近 $\pi/(4\theta)-1/2$ 的整数，在第一个概率峰附近得到最佳整数步数。本题取 $r=25$，理想单次命中率约为 99.95%。继续迭代会越过目标方向，概率下降并随迭代次数振荡。参见 [IBM Quantum：Grover 迭代次数](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/grover-algorithm/number-of-iterations)。

## 可逆 Toy Cipher Oracle

实际 Oracle 必须从公开密文字节及密钥寄存器可逆地计算上述谓词。根据[公开 Helper 接口](../HELPERS.md)，用 `mask_gates` 实现掩码异或、用 `SBOX_GATES` 对两个半字节分别做替换，最终按 `PERM` 解释线路。第二个字节的密钥左旋可用线路重映射表示，位置常量用固定异或实现。两个比较同时成立时施加相位 $-1$，然后反计算，使任意密钥基态满足

$$
\lvert k\rangle\lvert 0_{\rm work}\rangle
\longmapsto (-1)^{f(k)}\lvert k\rangle\lvert 0_{\rm work}\rangle.
$$

工作位回到零后，扩散只作用于密钥寄存器。该构造通过可逆字节检查标记候选，无需预先枚举通过检查的密钥。

## 经典与量子复杂度

对唯一解的无结构黑盒搜索，在固定成功率下经典需要 $\Theta(N)$ 次检查，Grover 需要 $\Theta(\sqrt N)$ 次相位查询。本题每个 shot 执行 25 次相位 Oracle 和 25 次扩散；一次抽象查询对应多道门，实际开销包含可逆解密、比较及反计算。还要分别记录从公开参数生成电路、转译、执行及测量后验证的经典开销。黑盒查询优势并不直接给出该实例的运行时间优势。

## Implementation Notes

- Junqi 可复用 8 个字节工作位：计算第一字节的比较标志并清空字节工作位，再计算第二字节，用其匹配条件和第一标志共同控制相位；随后清空第二字节并逆向执行第一项检查，清零标志。
- 直接实现受控相位时，基础逻辑布局为 10 个密钥位、8 个字节工作位和 1 个比较标志，共 19 位。分解多控门可能增加辅助位；这不是经过转译验证的资源结果。
- 在 `solve()` 中实际用 Aer 执行电路。区分 shots、Oracle 查询次数与转译后的双比特门数、深度、总门数及活跃 qubit 数。
