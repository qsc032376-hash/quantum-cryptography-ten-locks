# Tier 10 经典后处理接口（Junqi / Junrui 交接）

本文件对应 `submissions/team3/dh_classical.py`。只描述经典侧接口；量子电路与 `solve()` 由各自负责人实现。

## 1. 测量布局

官方群参数来自 `tier10/locked.json["public_parameters"]`：`p`、`g`、`order`、`A`、`B`、`key_width_bits`。

| 寄存器 | 全局量子位 | 经典位 |
|---|---|---|
| `X_j` | `j` (0–5) | `c_j` |
| `Z_j` | `6+j` (6–11) | `c_(6+j)` |

单个 12 位经典寄存器，Qiskit counts 字符串为 `c11…c0`（左端最高位）。
左 6 位为 **Z**，右 6 位为 **X**。两组逆 QFT 保留 SWAP，**不要**再做额外位反转。

```
T   = int(counts, 2)
y_x = T & 0b111111          # 右 6 位
y_z = T >> 6                # 左 6 位
```

若电路省略 SWAP 或交换了两组接线，用 `layout="zx"`；也可先自行重排字符串。

## 2. 频率换算（不能直接用原始读数）

`L = 64` 点 QFT 对应 `order = 41`，读数只是格子点：

```python
u = ((82 * y_x + 64) // 128) % 41      # 等价于 frequency_from_register(y_x, 41, 6)
v = ((82 * y_z + 64) // 128) % 41
k2, k1 = u, (-v) % 41                  # 满足 k1 + a*k2 ≡ 0 (mod 41)
```

`measurement_from_counts(text, order)` 一次完成上述步骤并返回 `(k1, k2)`；
`measurement_from_readout(y_x, y_z, order)` 供你自己解析时使用。

## 3. 多批测量

每次 Aer 运行得到一批 counts（`dict[str, int]`）。把样本展开成字符串列表即可：

```python
from submissions.team3.dh_classical import decrypt_from_counts

shots = []
for bitstring, n in counts.items():
    shots.extend([bitstring] * n)     # 或按需要抽样，不必全部保留
plaintext = decrypt_from_counts(shots, public_parameters, locked["ciphertext_hex"])
```

接口接受单个字符串或字符串列表；也会接受已经换算好的 `(k1, k2)` 对（`decrypt(pairs, params, hex)`）。

## 4. 候选与容错规则

`recover_exponent(measurements, params)` 的行为：

1. 逐条样本转方程：`(0,0)` 视为无信息并跳过；`k2=0, k1≠0` 或 `k1 % gcd(k2,41) != 0` 视为坏样本并跳过。
2. 优先用单条方程直接给候选（41 为素数时，非零频率即唯一候选），并用 `pow(g, a, p) == A` 验证。
3. 单条都不成立时，才做有限的两两 CRT 组合（上限 `MAX_PAIRWISE_COMBINATIONS=64`）。
4. 每条方程候选数超过 `MAX_CANDIDATES_PER_EQUATION=64` 时跳过，避免退化为穷举；
   总验证次数上限 `MAX_VERIFICATIONS=512`。
5. 全部样本都无效 → `NoSolutionError`（明确信号：**补采样**）。
6. 出现多个都通过 `g**a == A` 的候选 → `AmbiguousError`（正常参数下不会发生，因为已校验 `order` 是 `g` 的最小阶）。

**容忍度**：少量错误舍入样本不会否决正确候选——坏方程只产生验证失败的候选，被自动丢弃。实测「3 条错误 + 1 条正确」与「1 条正确 + 3 条错误」两种顺序都能解出。

## 5. 公共参数校验

`validate_parameters()` 会用公开群论拒绝：非整数/布尔/浮点、`p<3`、`g` 越界、
`g**order != 1`、`order` 不是 `g` 的最小阶（检查每个素因子的 `order/ℓ`）、
`A`/`B` 不在 `<g>` 内、`key_width_bits <= 0`。它**不**计算任何离散对数。

## 6. 建议的 `solve()` 连接方式

```python
from tier10_quantum import build_circuit          # Junqi 提供
from submissions.team3.dh_classical import decrypt_from_counts

def solve():
    circuit = build_circuit()
    counts = run_on_aer(circuit)                  # 真实测量，不伪造
    shots = [bitstring for bitstring, n in counts.items() for _ in range(n)]
    return decrypt_from_counts(shots, locked["public_parameters"], locked["ciphertext_hex"])
```

`NoSolutionError` 时应重新采样（增加 shots 或重跑），不要改用经典穷举；
`AmbiguousError` 说明样本不足，继续采样。不要记录指数、共享整数或明文到日志。

## 7. 异常

| 异常 | 含义 |
|---|---|
| `ParameterError` | 公开参数非法（含最小阶/子群检查） |
| `EquationError` | 测量对结构错误（非整数、长度不为 2） |
| `NoSolutionError` | 样本无有效候选，或彼此矛盾，需补采样 |
| `AmbiguousError` | 多个候选无法区分 |
| `CiphertextError` / `DecodeError` / `KeyBitsError` | 密文、UTF-8、密钥宽度问题 |

错误消息不包含隐藏指数、共享密钥或明文。
