# 跨种子回归与电路基准协议

固定基线 `release/ten-locks-v1@868fb65e20c73a27bffc118f3617080df9cf2f8b`。本工具只读取指定 Git 提交，通过临时 `git archive` 快照运行，不切换或修改当前工作树。未提交文件不参与测试；请先提交候选，再比较。锁定仓库依赖（Qiskit 2.6.1、Aer 0.18.2 等）；`psutil` 用于采样内存。`benchmarks/historical_baseline.json` 是已发表证据的摘录，含来源提交与官方评分方法，不是新测量值，也不替代候选评测。

## 跨种子测量

```sh
python benchmarks/cross_seed_regression.py --tiers 2 --seeds 11 23 \
  --timeout 45 --total-seconds 110 --memory-mb 1024 \
  --output benchmarks/results/tier02.json
python benchmarks/cross_seed_regression.py --ref optimization/tier05-oracle \
  --tiers 5 9 10 --seeds 11 23 37 41 53 \
  --timeout 120 --total-seconds 300 --output benchmarks/results/trials.json
```

每个关卡、种子在独立进程和快照中运行 `solve()`；最多 100 次，默认总时限 300 秒，单次最多 120 秒。总时限耗尽后余项标 `SKIP`。从 `AerBackend.run` 的入口覆盖 `seed_simulator`，第 n 个调用使用 `(请求种子+n) % 2**32`，并在真实 backend 返回任务后记录送入的种子、批次及 shots；不修改每关 shots 或应用逻辑。Tier 2 的 Channel 内部 Aer 也经过该入口。报告中列出应用声明的 `SEED_SIMULATOR`、`SEED_TRANSPILER`、`BASIS_SEED`（存在时）；种子注入只控制模拟器，不改变转译或应用 RNG。两个种子系列可能因补采样而重叠；作可靠性证据时使用间隔至少为最大批数的种子并检查实际记录。

`PASS` 需要哈希匹配、实际记录的评分电路与观测到的 Aer 电路数量相同、所有任务的 `result()` 完成且每次注入种子符合规则；它不代表官方 Checker `full` 或已证明遵守题目规则。不可观测的其他模拟或采样路径、未完成任务、种子未能核对时为 `UNCONTROLLED`；异常、哈希不匹配、超时或内存上限为 `FAIL`；未实现及超出总预算的未运行项为 `SKIP`。仅输出异常类，不输出异常消息、counts、密钥或明文。输入种子是用户给定的公开测试参数，不是隐藏数据。

## 前后复杂度比较

```sh
python benchmarks/circuit_benchmark.py --baseline release/ten-locks-v1 \
  --candidate optimization/tier05-oracle --tier 5 --seed 2026 \
  --official --timeout 120 --memory-mb 1024 \
  --output benchmarks/results/tier05_comparison.json
```

程序对两个提交分别构建隔离快照，先核对官方 checker、评分配置、哈希、`common` 与各关官方目录的 Git 树对象完全一致，否则拒绝比较。共享同一 Python 环境及资源预算。性能测量临时覆盖相同的 Aer 种子（按批递增），并在常规 `qiskit.transpile` / `qiskit.compiler.transpile` 入口注入官方评分转译种子；保留各自的模拟器编译设置，并记录实际观测到的编译调用。实际送往 Aer 的电路由未改动的官方 `worker_solve` 记录（Tier 2 按官方 Channel 日志）；再调用未改动的 `worker_transpile`，按官方评分配置转译，选双比特门最多、同数深度最大的电路。`build_circuit()` 不作为评分电路。采样期间的注入是测试，不写入源码；采样可能影响动态选电路，所以需要同时执行 `--official` 对照。

`--official` 分别调用原始 Checker 的 `check_tier`，不注入种子，单独报告 `full` / 哈希 / flags 和官方指标。它需要额外运行两次求解；未指定时显示 `NOT MEASURED`。受测版本若绕过常规编译入口或 Aer backend，不能仅依据仪表结果判定种子受控；请人工检查，保持 `INCONCLUSIVE`。所记录的编译调用与官方测量并不构成规则合规证明。

默认比较目标为双比特门，`--target depth`、`total_gates` 或 `active_qubits` 可改目标。`ACCEPT` 要求双方官方 `full`、SHA 匹配、无 flags、评分指标齐全且与仪表评分一致，预算内运行，目标指标下降、编译观测设置及应用 RNG 相同；还必须对两提交用至少 10 个相同且实际送入 Aer 的种子做全部通过的回归，并经人工审查题目规则与有限样本可靠性。把两个结果路径传给 `--baseline-regression`、`--candidate-regression`，完成审查后才传 `--rules-reviewed --reliability-reviewed`。这些选项是人工确认，不是自动证明。候选被官方确认错误、未执行电路或哈希不匹配，或证据齐全但目标未改善时为 `REJECT`；官方超时/错误、基线失败、证据缺失、复核标记、仪表不匹配或资源未测量时为 `INCONCLUSIVE`。独立比较运行并非正式裁判最终裁决。

10/10 仅是有限样本；记录全部失败、样本数、补采样、耗时和条件，不能据此宣称真实失败率为零或推断噪声硬件成功率。可用独立更多种子和置信区间评估可靠性。不要循环直至成功或丢弃失败样本。

## 资源、保密与恢复

每个工作进程设硬墙钟上限；`psutil` 每 20 ms 采样工作进程及子进程的 RSS 总和，超过上限终止进程树。短暂峰值可能漏采，RSS 之和可能重复计入共享页，不等于操作系统的精确峰值；记录预算与采样方式。Aer 时间为已完成任务从提交到 `result()` 返回的墙钟总和，含调度及等待，非纯设备计算；独立报告 `result()` 等待时间和求解时间。profile 进程同时运行求解和评分转译，因此同一个外部时限与内存峰值涵盖两者，可能比官方分别计时更严格；官方 `check_tier` 另用官方时限。异常信息、子进程输出和官方原始临时文件仅在私有临时目录中使用后删除；JSON 只存聚合结果。`benchmarks/results/` 已忽略，勿提交原始测量、密钥、密文、明文、异常详情或任何私密报告。

验证冻结分支：`git rev-parse release/ten-locks-v1` 应等于 `868fb65e20c73a27bffc118f3617080df9cf2f8b`，再比较 `git ls-remote origin refs/heads/release/ten-locks-v1`。不要重置或强推发布分支；若指针意外不同，先调查。优化从该提交建立新分支，结果独立验证，禁止修改发布版本或在此工具中提交比赛平台。
