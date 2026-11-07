# Tier 1–4 稳定基线与 Tier 5 接入

基线为 `integration/tier04@980b87eb40157e40ec91044aa6dcb090b99205c6`。Tier 1 文件与 `54cf863` 一致，Tier 2–3 文件与 `5929deb` 一致，Tier 4 使用该基线的最终实现，共用 `classical_keystream.py` 与 `d4f561d` 一致。无需补入任何实现。

复用了 [Tier 4 集成记录](TIER04_INTEGRATION.md) 和同一 worktree 保存的官方 Checker JSON：受测实现未变，评分配置与 `hashes.txt` 的 SHA-256 与报告相符。Tier 1–4 均为 `full`、明文 SHA-256 匹配，评分指标有效，无超时或复核标记。另在临时改名后的团队目录中，使用官方文件加载器、相同的导入路径和合成数据调用四关 `solve()`；四关均通过。该探针替换了量子恢复入口，本轮没有重跑量子电路。

## Tier 5 接口与验收

已查 `feature/quantum-circuits@72e3586`：分支最新实现是 Tier 4，尚未发布 Tier 5 电路或 Grover API。以下是拟议的接入约定，待 Junqi 提供提交及确认接口。

1. 由真实 Aer 测量给出 10 位候选。建议量子入口返回整数 `k`，满足 $0\le k<1024$；如果入口给的是 counts 字符串，令密钥 qubit $j$ 测到单一经典寄存器的第 $j$ 位。按 [Qiskit 位序](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering)，字符串为 `c9…c0`，用 `key_from_bitstring(text, 10)` 转整数，保留输入宽度且不反转。若入口已经返回整数，不再作位序转换。
2. 从官方 `load_locked(5)` 取 `ciphertext_hex`，将测量所得整数和十六进制密文传给 `toy_cipher_classical.decrypt_tier5(k, ciphertext_hex)`。Youyang 的 `d4f561d` 接口返回 UTF-8 字符串，但不检查前缀；由 `solve()` 显式验证完整的 `QC-05: `（含末尾空格），再返回字符串供 Checker 独立比较 SHA-256。合成测试已验证改名后可以加载该模块、解析带前导零的测量串，并在调用端拒绝错前缀。
3. 按[官方 Tier 5 规则](../tier05/README.md)，可逆 Oracle 必须同时检查前两个字节 `QC`，使正确密钥成为高概率测量结果；题目未设 Oracle 查询次数上限，不能用随机猜测加经典筛选替代 Grover。若每轮应用一次相位 Oracle，25 轮是唯一解的理想起点，每 shot 计 25 次逻辑查询；另记实际电路数、shots 与转译指标。`solve()` 必须运行 Aer；`build_circuit()` 仅用于展示。官方配置的 `solve` 和评分转译预算分别为 120 秒。
4. 团队文件布局保持 `submissions/<team>/tier05/solution.py` 和 `submissions/<team>/toy_cipher_classical.py`。包模式从父包相对导入；Checker 按文件加载时，以 `Path(__file__).resolve().parents[1]` 定位共享模块，参考 Tier 3–4。不要写死 `submissions.team3`。

## 本地资源与 OSC 后备

先在本地 CPU 上用项目固定的 Qiskit 2.6.1 / Aer 0.18.2 做小批量测量和转译。按 10 个密钥位、8 个复用工作位和 1 个比较位估算，19 位双精度状态向量本体约 8 MiB；这不含额外辅助位、转译、门融合和 Python 进程开销。深度及多控门分解可能比状态向量更早成为瓶颈。建议初次采用 2 线程、单电路并行度、有限 shots，记录求解与转译时间、峰值内存及评分指标。参见 [Aer 资源选项](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html)。

目前没有迁移 OSC 的实测依据。若接入后本地出现内存压力或接近 Checker 时限，再在 [OSC 计算节点的 Slurm 批处理](https://www.osc.edu/supercomputing/batch-processing-at-osc/slurm_directives_summary) 试跑：`--nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4gb --time=00:10:00`，不申请 GPU；设 `OMP_NUM_THREADS=2`，Aer `max_parallel_threads=2`、`max_parallel_experiments=1`、`max_memory_mb=2048`。内存设置只限制状态存储，Slurm 才限制整个进程。登录节点只准备和提交作业；调度时长不改变官方评分时限。

下一步：取得 Junqi 的 Tier 5 提交与实际返回格式，确认可逆 `QC` 检查、辅助位清零和有界采样策略；再接入 Youyang 的经典模块，执行真实 SHA-256、官方评分和 Tier 1–4 回归。
