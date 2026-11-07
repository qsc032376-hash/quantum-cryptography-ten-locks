# Tier 8–9 Shor 与 RSA 集成验证

基于已验证的 `integration/tier07@a9860a3`。两关量子实现取自 Junqi 的 `9cfc92a`（包含 `01b0c6a` 的 Tier 8 代码）；RSA 适配器原样取自 Youyang 的 `6c9ce26`，复用基线中与该版本内容一致的 `classical_keystream.py`。集成改动限于按团队目录定位模块、校验完整前缀和官方哈希，以及在 RSA 验证失败时抑制可能包含敏感值的异常细节。Tier 1–7 的实现、官方题目、密文、哈希和评分工具均与基线一致；复用[已有的 Tier 1–7 验证结果](SUBMISSION_STATUS.md)。

两关的 `solve()` 均运行实际 Aer 电路。Tier 8 使用 12 个计数位与 6 个工作位，模块乘法借用并复原其他计数位；Tier 9 使用 14 个计数位与 7 个工作位，Aer 保留原生多控 X，Checker 对同一执行电路单独转译评分。两关均使用带交换的完整逆 QFT，把单寄存器读数直接解释为二进制整数。连分数分母及其最小公倍数提供候选周期；先验证 `pow(a, r, N) == 1`，再按候选周期的素因子验证最小性，然后用半阶 GCD 取得互补的非平凡因子。未对官方模数做试除，未硬编码周期或因子。

因子只在进程内传给相应的 `rsa_classical.decrypt_tier8()` 或 `decrypt_tier9()`。模块按各自公开参数解包 RSA 并以 `key_width_bits` 保留前导零，生成对称密钥流。`solve()` 在返回前检查完整 `QC-08: ` 或 `QC-09: ` 前缀和官方 SHA-256；Checker 独立核对返回字符串的哈希。证据仅保留通过状态、统计量和评分指标。

| 官方 Checker 指标 | Tier 8 | Tier 9 |
| --- | ---: | ---: |
| Checker / 明文 SHA-256 | full / 匹配 | full / 匹配 |
| Aer 批次 / shots | 1 / 64 | 1 / 64 |
| 周期方程 / 最小性 / 非平凡因子验证 | PASS / PASS / PASS | PASS / PASS / PASS |
| 通过连分数误差门限的 shots | 59 | 57 |
| 压缩受控模幂块 / shot | 12 | 14 |
| 压缩受控模幂块，按 shots 计 | 768 | 896 |
| 双比特门 | 49,920 | 117,739 |
| 深度 | 135,160 | 316,820 |
| 总门数 | 148,085 | 349,949 |
| 活跃 qubits | 18 | 21 |
| 超时 / 缺失指标 / 复核标记 | 无 | 无 |
| 改名目录中运行并定位本地模块 | PASS | PASS |

两关各记录一条真实执行电路，指标来自官方评分转译结果。等价逐次模乘量每 shot 分别为 4,095 和 16,383；实际执行的是上表的受控模幂块，不是逐次调用基础模乘。两关未触发补采样；仅在测量证据不足且时间允许时，才最多补一批。

| 本地实测（Apple M2、8 GiB，Qiskit 2.6.1 / Aer 0.18.2，2 个 Aer 线程） | Tier 8 | Tier 9 |
| --- | ---: | ---: |
| Checker 求解计时 | 32.768 s | 5.991 s |
| 执行前转译 | 0.163 s | 0.045 s |
| Aer 采样 | 32.560 s | 5.901 s |
| 官方评分转译及计指标 | 0.266 s | 0.867 s |
| 求解工作进程峰值 RSS | 562.2 MiB | 144.5 MiB |
| 评分工作进程峰值 RSS | 214.7 MiB | 218.8 MiB |

两关同一 Checker 进程的总墙钟为 **44.91 s**，包含工作进程启动和报告写入。临时观察器只读求解统计、转译时长与各进程 RSS，并确认逆 QFT、模乘、求阶和 RSA 从改名副本加载；未修改 Checker 或改写电路、counts、明文及返回值。两关无内存错误。Tier 8 的执行基展开是当前耗时主项；其他硬件、补采样或依赖版本可能改变成本，固定种子的理想 Aer 结果不代表真实硬件表现。

合成回归 **4/4 PASS**：两关分别用小模数真实 Aer 完成求阶、RSA 和哈希验证；另外覆盖无测量证据、非最小周期、错误前缀和错误哈希。复现时从仓库根目录运行，`python` 指向项目固定依赖环境：

```bash
OMP_NUM_THREADS=2 python -B tests/test_tier08_tier09_integration.py -v

run_dir=$(mktemp -d)
mkdir -p "$run_dir/team-renamed"/tier0{7,8,9}
cp submissions/team3/{classical_keystream,rsa_classical}.py "$run_dir/team-renamed/"
cp submissions/team3/tier07/qpe.py "$run_dir/team-renamed/tier07/"
cp submissions/team3/tier08/{modular,order,solution}.py "$run_dir/team-renamed/tier08/"
cp submissions/team3/tier09/{modular,solution}.py "$run_dir/team-renamed/tier09/"
OMP_NUM_THREADS=2 python -B tools/check_submission.py "$run_dir/team-renamed" --out "$run_dir/official"
```
