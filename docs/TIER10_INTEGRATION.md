# Tier 10 端到端集成与官方验收

基线为 `integration/tier08-tier09@03c79a3`。电路取自 Junqi 的 `b0f450a`；读数转换与 Diffie–Hellman 解密取自 Youyang 的 `dc47b15`。改动仅限 Tier 10 的接口、导入、前缀和哈希验证；复用基线的逆 QFT、可逆模乘、RSA 模逆及密钥流依赖。Tier 1–9 与官方文件逐字节不变，复用 [Tier 1–7](SUBMISSION_STATUS.md) 和 [Tier 8–9](TIER08_TIER09_INTEGRATION.md) 的 Checker 证据。

按[官方 Tier 10 规则](../tier10/README.md)，`solve()` 对公开的两个群元素构造受控模乘置换：合法工作整数映射到其模乘结果，填充态固定；通过可逆多控 X 实现，未构造或查询离散对数表。两组 6 位计数寄存器和 7 位工作寄存器共 19 qubits。两组均用带三个 SWAP 的完整逆 QFT，按 `qj → cj` 写入同一个 12 位经典寄存器；counts 左 6 位为 Z，右 6 位为 X，不反转。

所有有效格式的读数均走 `dh_classical.measurement_from_counts(..., layout="xz")`，先对每组以整数式 `((82*y + 64)//128) % 41` 将 64 点读数舍入到模 41 的频率 $(u,v)$，再生成 `((-v) % 41, u)`。只对能确定完整模数的测量方程生成候选；按 shots 支持排序，以 `pow(g,a,p)==A` 验证，最多两批、每批最多八个新候选。经典解密仅接收一条已验真的完整同余，避免峰外样本互相冲突或枚举未由测量确定的指数。共享密钥按官方宽度编码；`solve()` 检查完整 `QC-10: ` 前缀及 SHA-256，Checker 另行检查返回字符串的哈希。未记录真实读数、指数、密钥或明文。

| 改名目录中的官方 Checker | 实测 |
| --- | ---: |
| Checker / 明文 SHA-256 | full / 匹配 |
| Aer 批次 / shots / 补采样 | 1 / 128 / 0 |
| 提供完整同余的 shots | 120 / 128（93.75%） |
| 支持经公开关系验证候选的 shots | 95 / 128（74.22%）；占完整同余 79.17% |
| 退化 / 无解 / 部分同余 shots | 8 / 0 / 0 |
| 测量产生的候选数 / 公开验真次数 | 19 / 1 |
| 记录并评分的电路数 | 1 |
| 双比特门 / 深度 | 107,168 / 287,674 |
| 总门数 / 活跃 qubits | 317,957 / 19 |
| 超时 / 内存错误 / 缺失指标 / 复核标记 | 无 |

每 shot 有 12 个压缩受控模幂块，全批共 1,536 个；逐次展开等价 16,128 次基础模乘，实际没有逐次执行。支持率是固定种子下该批实测比例，不能外推为独立运行或真实硬件的成功率。

| 本地计时及内存（Apple M2，Qiskit 2.6.1 / Aer 0.18.2，2 个 Aer 线程） | 实测 |
| --- | ---: |
| Checker 求解 / Aer 采样 | 1.874 / 1.707 秒 |
| 执行前转译 / 官方评分转译及计指标 | 0.050 / 0.833 秒 |
| Checker 总墙钟 | 3.95 秒 |
| 求解 / 评分工作进程峰值 RSS | 119.1 / 222.7 MiB |

临时观察器仅核对两组逆 QFT、测量接线、依赖来源并记录聚合指标；没有修改 Checker 文件、执行电路或返回值。改名副本实际加载了本地的 Tier 7–10 与共享经典依赖。额外以两种顺序导入原 Tier 1–9 模块和 Tier 10，共享依赖均正常。项目新增的两项合成集成测试通过；Junqi 的 43 项测试也通过，其中原成功样例的模拟返回值在临时副本中补上了正式前缀。正式验收使用真实量子测量和官方密文。

复现时从仓库根目录运行，`python` 指向项目固定依赖环境：

```bash
OMP_NUM_THREADS=2 python -B tests/test_tier10_integration.py -v

run_dir=$(mktemp -d)
mkdir -p "$run_dir/team-renamed"/tier{07,08,09,10}
cp submissions/team3/{classical_keystream,rsa_classical,dh_classical}.py "$run_dir/team-renamed/"
cp submissions/team3/tier07/qpe.py "$run_dir/team-renamed/tier07/"
cp submissions/team3/tier08/{modular,order}.py "$run_dir/team-renamed/tier08/"
cp submissions/team3/tier09/modular.py "$run_dir/team-renamed/tier09/"
cp submissions/team3/tier10/{circuit,readout,solution}.py "$run_dir/team-renamed/tier10/"
OMP_NUM_THREADS=2 python -B tools/check_submission.py "$run_dir/team-renamed" --out "$run_dir/official"
```
