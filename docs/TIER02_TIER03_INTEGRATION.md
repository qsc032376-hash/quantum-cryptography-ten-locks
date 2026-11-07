# Tier 2–3 集成与官方评分验证

基线为 `origin/main` 的 `fce7c39`。Tier 1 整个团队目录逐文件保留 `54cf863`，Tier 2、3 电路来自 `c4d2a10`，共用的经典解密模块原样取自 `9b04a63`。没有合并开发分支。环境为 macOS ARM64、Python 3.13.9、Qiskit 2.6.1、Aer 0.18.2、NumPy 2.5.4、PyYAML 6.0.3。

| Tier | 官方状态 | SHA-256 | Checker 执行电路 / shots | Oracle 调用 | 双比特门 | 深度 | 总门数 | 活跃 qubit |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 2 | `full`（PASS） | 匹配 | 2048 / 2048 | 不适用；两个 Channel 各接收一次 | 0 | 3 | 3 | 1 |
| 3 | `full`（PASS） | 匹配 | 24 / 24 | 24（各电路一次） | 7808 | 8771 | 19497 | 7 |

以上门数是官方 Checker 选出的最大评分电路（按双比特门数，平局按深度）。两关均为 `metrics_status: ok`，没有超时、`no metrics` 或复核标记；Checker 中 `solve()` 分别用时 0.388 秒和 5.251 秒。Tier 1 回归仍为 `full`、SHA-256 匹配、指标有效。

Tier 2 共验证 3 次，每次使用新进程：一次 Checker，加两次独立探针。3 次 SHA-256 都匹配；两次探针的链路统计相同：A 为 0/141（0%），B 为 32/127（25.20%）。两次均先盲选基；每链路仅创建一次并依次执行 `receive_all()`、`finish()`，2048 个接收位置无重复，Aer 两个批次，每位置一 shot。只将链路 A 的 371 个同基、非公开检查位置交给公开协调函数，实际调用一次。固定基选择与 Channel 的确定性模拟使这组结果可复现；它不衡量随机种子或噪声下的成功率。

Tier 3 在 Checker 与独立探针中均完成真实解密。探针确认 `solve()` 按 0–23 顺序构建电路，转译前逐条检查一次 Oracle，Aer 一个批次执行 24 条单 shot 电路，实测分类顺序原样传入共用的 `classical_keystream.decrypt()`。Checker 自带 `oracle_calls` 字段只反映默认的展示电路；24 次总调用由独立探针核对。

发现并修复了 Tier 3 固定导入 `submissions.team3` 的集成问题：包加载使用相对导入，Checker 按文件加载时根据 `solution.py` 的位置定位经典模块。改名后的合成样例通过官方加载器；Junqi 的 22 个合成单元用例也全部通过。未记录密钥、明文或逐 Oracle 分类。

剩余风险：Tier 3 的评分电路较深，理想 Aer 的成功与耗时不能代表硬件。后续可单独评估预转译与 Checker 转译之间的重复成本，以及 Oracle 之外的准备、读出和边界处可消除的门；当前未重写官方 Oracle，也未调整评分设置。

复现（在隔离 worktree 根目录，使用上列依赖）：

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 .venv/bin/python -B tools/check_submission.py submissions/team3 --out .venv/checker-tier02-tier03
for tier in 2 2 3; do
  OMP_NUM_THREADS=2 .venv/bin/python -B tests/validate_tier02_tier03.py "$tier"
done
```
