# Tier 3 / Tier 6 电路简化实验结果

日期：2026-11-08。基线：`integration/optimized-v2-candidate@0cd8adc`。
分支：`optimization/tier03-tier06`。
所有指标由未修改的 `tools/check_submission.py` 生成（`rz,sx,x,cx`、优化级别 1、
seed 12345、全连接、无固定 layout），每次取 2Q 门最多、再取最深的一条电路。

## 结论

| Tier | 实验 | 2Q 门 | 深度 | 总门数 | 活跃位 | 结论 |
|---|---|---:|---:|---:|---:|---|
| 3 | 基线（level 1） | 7,808 | 8,771 | 19,497 | 7 | 参考 |
| 3 | 预转译 level 2 | 7,680 | 10,453 | 22,847 | 7 | **EXPERIMENTAL，未接受** |
| 3 | 预转译 level 3 | 7,680 | 10,453 | 22,847 | 7 | **EXPERIMENTAL，未接受** |
| 6 | 基线（level 1） | 3,000 | 5,883 | 9,534 | 22 | 参考 |
| 6 | 预转译 level 2 | 3,000 | 5,715 | 8,752 | 22 | **已通过官方 Checker** |

## Tier 3：没有净收益，拒绝

Tier 3 每关 24 条独立 7-qubit 电路，每条的 2Q 门几乎全部来自官方不透明 Oracle
的基门展开；外围仅有目标位 X/H、输入 H 层与测量。本轮只尝试审计允许的通用编译：

- level 2/3 预转译把 2Q 门从 7,808 降到 7,680（−128，−1.64%），
- 但深度从 8,771 升到 10,453（+1,682，+19.2%），总门数从 19,497 升到
  22,847（+3,350，+17.2%）。

按 Simplicity 权重（2Q 0.4、深度 0.3、总门 0.2）估算为净负收益，且三条电路均
变差；因此不修改 Tier 3，也不提交该方向。未读取或重写 Oracle 内部，未用经典
分类结果替代量子电路。

## Tier 6：已接受（预编译 level 2）

只改 `submissions/team3/tier06/solution.py` 中 `_simulate()` 的预转译级别
（1 → 2），其余逻辑、Oracle、Diffuser、轮数与测量语义均未改动：

| 指标 | 之前 | 之后 | 变化 |
|---|---:|---:|---:|
| 2Q 门 | 3,000 | 3,000 | 0 |
| 深度 | 5,883 | 5,715 | −168（−2.86%） |
| 总门数 | 9,534 | 8,752 | −782（−8.20%） |
| 活跃位 | 22 | 22 | 0 |

原因：level 2 消除了 level 1 之后仍残留的冗余 RZ 层；CX 数量与线路语义不变。
Checker 会在自己固定的 level 1 配置下重新转译该记录电路，仍然得到上述数值。

### 验证证据

1. **官方 Checker（完整模式，未改动的 `tools/check_submission.py`）**：
   十关全部 `full`、SHA-256 `match`、`circuit run yes`、`metrics ok`、flags 为空；
   总墙钟 108.1 秒。Tier 6 指标如上表。
2. **改名团队目录**：`submissions/team3` → `team_v36` 的隔离副本重跑官方 Checker，
   十关同样全绿、Tier 6 指标一致（107.9 秒）。
3. **量子语义**：同一 12 轮搜索电路分别以 level 1/2 预转译，使用相同 Aer 种子与
   128 shots，**测得 counts 逐项完全相同**（53 个结果、128 shots）。3 轮版本亦相同。
   这说明相位、纠缠与辅助位恢复未被改变。
4. **未受影响关卡**：本分支只改动 `tier06/solution.py` 一个文件；Checker 报告中
   Tier 1–5、7–10 的指标与 v2 基线逐项一致。

### 复现

```bash
python tools/check_submission.py submissions/team3 --out reports/t36
```

## 边界

- Tier 3 的候选仅记录为 EXPERIMENTAL；没有任何 Tier 3 代码进入提交。
- Tier 6 的收益来自通用编译设置，不是新的 Oracle 数学简化；未减少 Grover 轮数，
  未改变标记集合、成功概率或经典筛选逻辑。
- 本文件不声称 v1/v2 已被替换；v2 候选与冻结版均未修改。
