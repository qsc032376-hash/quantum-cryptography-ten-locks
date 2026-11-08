# Tier 9 / Tier 10 独立复核

日期：2026-11-08。基线：`integration/optimized-v4-candidate@73f4dbe`。
本文件放在独立分支 `validation/tier09-tier10-independent`，不包含算法改动。

## 方法与边界

- **文档审阅**：读取提交 `17df36d`（Tier 9）与 `7c9d032`（Tier 10）的说明、
  v4 证据 `docs/evidence/v4/report.json` 与 `docs/OPTIMIZED_V4_CANDIDATE.md`。
- **独立执行**：所有标“实测”的数字都由本轮在本机运行未修改的 Checker 或自写
  小规模等价测试得到，不是转述作者报告。
- **未执行**：21 位 Tier 9 / 19 位 Tier 10 的完整稠密算子；官方评分（依赖其他
  队伍）；噪声硬件与多种子失败率统计。

## Tier 9 — ACCEPT

来源：`optimization/tier09-mcx@17df36d`（实现 `f86a442`），v4 由 `04feb70` 引入
`tier09/shared_controls.py` 并替换 `solution.py` 的一行导入。

### 实测

1. **受控模乘的酉等价（本轮自写测试）**：对 multiplier ∈ {2, 3, 5, 13}、modulus = 77、
   work_bits = 7，比较旧 `tier09.modular.build_controlled_multiplier` 与新
   `tier09.shared_controls.build_controlled_multiplier` 的 8-qubit 算子：

   | multiplier | 维度 | `Operator.equiv` | max\|U_old − U_new\| |
   |---:|---|---:|---:|
   | 2 | 2⁸ | True | 4.35e-14 |
   | 3 | 2⁸ | True | 1.30e-13 |
   | 5 | 2⁸ | True | 1.75e-13 |
   | 13 | 2⁸ | True | 1.32e-13 |

   8 位包含控制位与 7 个 work 位，覆盖 padding 与全部分支；误差为浮点噪声。
   这同时验证了“无辅助位 + 扇出后复原”的构造：电路不新增 qubit，等价性覆盖所有
   基态列，因此不存在残留辅助位或相位差。

2. **官方 Checker（完整模式，本机 v4 树）**：Tier 9 为
   **89,075 / 235,048 / 263,601 / 21**，`full`、SHA-256 `match`、`metrics ok`、
   flags 为空；与候选声明一致。
3. **改名团队目录**（`team_v4_t36`）重跑：十关全绿，Tier 9 数值不变。

### 判断

构造是“同条件翻转合并 + F·X_p·F 扇出”的精确置换，控制条件不含目标线；本轮的
算子等价测试与端到端哈希都通过。判 **ACCEPT**，但这是有界复核，不是形式化证明。

## Tier 10 — ACCEPT

来源：`optimization/tier10-qft-control@7c9d032`，v4 由 `73f4dbe` 引入
`tier10/shared_control.py` 与 `circuit.py` 改动。

### 实测

1. **输出分布等价（本轮自写测试）**：用官方公开参数（`p=83, g=3, A=11`）分别构建
   - 旧契约 `build_qpe_qft_only`（含两组完整逆 QFT 的 SWAP），
   - 新默认 `build_qpe_circuit`（SWAP 并入控制线 + 无辅助位扇出），

   两者均为 19 qubits / 12 clbits。以同一官方基门配置转译、同一 Aer 种子、256 shots：

   | 对比 | 不同结果数 | 结果 |
   |---|---:|---|
   | 旧 vs 新 | 0（115 个结果完全一致） | 分布逐项相同 |

   这直接检验了问题最关心的两点：逆 QFT 位序与受控相位没有改变，`qj → cj` 的
   测量布局与经典恢复接口保持一致。求解耗时（含转译）旧 29.0 s、新 24.3 s，仅作参考。
2. **官方 Checker**：Tier 10 为 **82,804 / 218,263 / 245,153 / 19**，`full`、
   `match`、`metrics ok`、无 flags；与候选声明一致。
3. **接口**：`0cd8adc..73f4dbe` 的 Tier 10 改动只涉及 `circuit.py` 与
   `shared_control.py`；`solution.py`、`readout.py`、`dh_classical.py` 未改。端到端
   SHA-256 匹配证明经典恢复路径仍可用。

### 判断

SWAP 吸收依赖初始计数态 `|+>^12` 在寄存器反转下不变；对实际输入成立，文档也明确
说明任意输入需同时反转。本轮的完整分布相等测试与 Checker 通过支持该结论。判
**ACCEPT**；未对任意初态或噪声条件作结论。

## 汇总

| Tier | 结论 | 依据 |
|---|---|---|
| 3 | REJECT | 无净收益，保持基线（见 `TIER03_TIER06_OPTIMIZATION_RESULTS.md`） |
| 6 | ACCEPT | 深度 −168、总门 −782，Checker 全绿 |
| 9 | ACCEPT | 8-qubit 算子等价 + Checker 89,075 / 235,048 |
| 10 | ACCEPT | 256-shot 分布逐项相同 + Checker 82,804 / 218,263 |

## 限制

- 等价性测试覆盖小规模算子/单参数分布，不是 21/19 位的完整算子证明。
- 全部结果来自固定种子的理想模拟；不代表其他种子、噪声硬件或评分排名。
- v4 的作者证据、ZIP 摘要与提交记录只做了文档核对，未重新打包。
- 本轮未修改 v1–v4 任何分支或官方文件。
