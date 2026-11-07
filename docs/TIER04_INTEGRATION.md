# Tier 4 Simon 集成验证

基线：`integration/tier02-tier03@5929deb`。Tier 4 电路和 GF(2) 消元来自 `72e3586`，共用的 `classical_keystream.py` 原样取自 `d4f561d`；Tier 1–3 的各关文件未修改。Tier 4 只调整模块加载和解密接线，未改动量子采样或消元算法。

| Tier | 官方 Checker | SHA-256 | 实际执行电路 | 双比特门 | 深度 | 总门数 | 活跃 qubit |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | full | 匹配 | 1 | 151 | 44 | 298 | 25 |
| 2 | full | 匹配 | 2048 | 0 | 3 | 3 | 1 |
| 3 | full | 匹配 | 24 | 7808 | 8771 | 19497 | 7 |
| 4 | full | 匹配 | 1 | 183 | 195 | 455 | 20 |

四关评分指标均有效，无超时、`no metrics` 或复核标记；Tier 4 的 Checker `solve()` 用时 0.101 秒。复用了隔离的 Python 3.13.9 环境，Qiskit 2.6.1、Aer 0.18.2、NumPy 2.5.4、PyYAML 6.0.3。

改名探针使用官方文件加载器，从临时 `submissions/<renamed-team>/tier04/solution.py` 执行完整 `solve()`，SHA-256 匹配。一次 Aer 批次执行一条电路、32 shots，在上限 128 内得到 31 条不同方程，秩 9、零空间维数 1。唯一非零向量满足全部已观测方程，并以 10 位范围内的整数传给 `decrypt_tier4()`。探针只输出统计值，不保存或输出方程、周期或明文。Tier 4 的 29 个合成测试和 Tier 2–3 的 22 个合成测试均通过。

调用规则以 [Tier 4 README](../tier04/README.md) 为准：从实际 Oracle 电路测量中恢复周期，并在 `solve()` 中使用 Aer。题目没有整关只调用一次的限制；Checker 的 `oracle_calls` 对本关为 `null`。探针在转译前只数外层 Oracle 包装块：每条采样电路一次，32 shots 对应 32 次逻辑查询；这与一个 Aer 批次不同。

修复了原实现对团队目录名的固定导入：包模式使用相对导入，Checker 文件加载模式按路径定位 GF(2) 和经典模块。剩余风险是实际采样所需批数随测量结果而变；秩不足时在预算内继续采样，超过预算报错。当前结果来自理想 Aer，未验证硬件噪声下的成功率。

复现（在集成 worktree 根目录，`python` 指向上述依赖环境）：

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 python -B tools/check_submission.py submissions/team3 --out .venv/checker-tier04
OMP_NUM_THREADS=2 python -B tests/validate_tier04.py
```
