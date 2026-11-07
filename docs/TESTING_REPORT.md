# 第一阶段经典模块验证 · Junrui Yu

2026-11-08。测试分支 `feature/testing-validation` 起点 `1623cf945dff3044580012d43b060521f14efd7c`，检出后工作区干净。Fetch 后确认 `origin/feature/classical-implementation` 指向 `d65efdb54d213ebd7b7fe39cd4235dce053f5604`；实际导入的是该 SHA 的 detached worktree 中的两个模块。两版本的 common、requirements 和 tools 无差异。量子接口仅静态对照 `origin/feature/quantum-circuits` 的 `87cb6bb3c138253fd49c6aa4c492e6c1d9f68eb9`。未合并成员分支。

## 环境与复现

Windows 11 build 26200；项目 .venv 使用 CPython 3.12.10。已核对八项实装版本：qiskit 2.6.1、qiskit-aer 0.18.2、numpy 2.5.4、pyyaml 6.0.3、matplotlib 3.11.2、pylatexenc 2.11、notebook 7.6.4、ipykernel 7.4.0。`pip check` 无冲突。`tools/check_setup.py` 验证 Qiskit/Aer、28 个供应电路和 helper、8-shot Aer 冒烟测试，退出 0。官方文件未改。

在测试分支仓库根目录运行（已创建同名 worktree 时跳过第二行）：

```powershell
git fetch origin feature/classical-implementation
git worktree add --detach ../classical-d65efdb d65efdb54d213ebd7b7fe39cd4235dce053f5604
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python tools/check_setup.py
.\.venv\Scripts\python -m unittest discover -s tests -p test_classical_integration.py -v
```

可用 `CLASSICAL_WORKTREE` 指定另一处同 SHA 工作树。缺工作树时 unittest 标记模块 SKIP；提交不符或被测源有改动时报错。用例按 unittest 方法计数，子用例不另计。

| 分组 | PASS | FAIL | SKIP | 验证证据 |
|---|---:|---:|---:|---|
| Tier 1 | 5 | 0 | 0 | 0、1、最大值与非对称字节；c14/c0 人工测量转整数，三字节循环 XOR 多轮 UTF-8；拒绝坏密钥、Hex、UTF-8 |
| Tier 3 | 3 | 0 | 0 | 逐个把 Oracle 0–23 设为唯一 balanced，其他为 constant；混合 flags 按序生成带前导零的串；拒绝非法长度/分类 |
| Tier 4 | 3 | 1 | 0 | 10 个单比特位置、最大值、跨块解密、非法整数；全零隐藏串未被拒绝 |
| 公共与导入 | 4 | 0 | 0 | 两层各自的宽度、字符、Hex、UTF-8；根目录独立进程导入；干净 Checker 工作者 |
| **总计** | **15** | **1** | **0** | **16 项，退出 1** |

Tier 3/4 的加密夹具独立使用 hashlib，以人工位串的 ASCII 和从 0 起算的四字节大端计数器生成掩码；明文含多字节字符并超过两个 SHA-256 块。没有读取实际挑战密钥或密文。导入探针在临时目录只放官方 common、原版 checker 和团队两个被测文件；为三个 Tier 分别放入合成 solution，直接调用 checker 的 `--_solve` 工作者。三个探针均返回人工文本 OK 的 SHA-256，无错误，记录电路数均为 0。该测试验证提交依赖边界及真实模块搜索路径，不是整队评分。

## 官方评分机制

依据 README、CHALLENGE、SCORING、tools/check_submission.py、tools/scoring_config.yaml 和 TEAM_TEMPLATE。评分器从仓库根运行，把 solution 所在 tier 目录排在 sys.path 首位、仓库根次之，用临时模块名 team_solution 加载文件。solve() 必须返回 str；仅去掉末尾 CR/LF，再以 UTF-8 做 SHA-256，逐层与 hashes.txt 对比。前后空格等其他字符保留。

- 导入/执行过程中安装的 recorder 包装 AerBackend.run 及可用的 Aer Sampler/Estimator.run；Tier 2 使用 Channel 日志。对本次三层，必须在 solve() 中真实使用 Aer 测量恢复密钥。哈希正确且及时并记录电路才有全分资格。仅哈希匹配为该层 25%；有电路但无正确答案由评委根据说明酌给至多 50%。不相关的电路、检查 Oracle 内部或缺乏测量证据会影响信用。
- build_circuit() 供画图，Tier 1/3 另用它检查是否恰一次 Oracle 调用，不作为复杂度计分电路。solve 与 transpile 上限均为 120 秒（工作进程另有 60 秒启动宽限，不能延长计分时限）。导入失败、异常、返回非字符串、超时、明文不符都可阻止满分。`--metrics-only` 仍运行 solve()。
- 去掉 Aer save_/set_ 指令，QPY 去重，再按 rz/sx/x/cx、全连接、优化级 1、种子 12345、无预设布局转译。按双比特门最多、再按深度最大选一个实际电路。总门数按有效指令数，双比特门按恰好两条线计，活跃比特是至少被一个门触及的线；每门层级为所在线已有最大层级加一，深度取最高层。measure/reset/barrier/delay 不计，控制流展开各分支，for 循环按轮计。
- Simplicity 要求层满分且有有效指标；QPY 或转译失败/超时该层无简洁分。权重依次为双比特门 0.4、深度 0.3、总门 0.2、活跃比特 0.1。各指标取合资格队伍最佳值/本队值，最佳为零时本队零得 1、否则得 1/(1+本队值)。每层分池为层分 × 0.375。Tier 1/3/4 活跃位少于 25/7/20 触发人工复核，本身不自动扣分。shots、运行和 Oracle 调用次数另记入 write-up；经典测试不能证明上述得分。

## 问题与整合门槛

| 级别 | 复现及影响 | 建议 |
|---|---|---|
| P0 | 本阶段未发现。完整量子路径尚未验证。 | 正式整合后再做全量评分。 |
| P1 · Tier 4 领域校验 | 运行 test_simon_hidden_string_must_be_nonzero：以全零 10-bit 串加密人工明文，decrypt_tier4(0, cipher) 正常解密，预期 KeyBitsError 未触发。tier04/README 要求非零。量子侧若把无效解 0 交给经典层，可被当成有效候选。 | 由接口负责人在 Simon 专用入口或调用前检查 1 ≤ s < 1024，保留通用位格式化能力。测试保留 FAIL。 |
| P1 · 条件性导入失败 | Junqi 的 Tier 1 solve() 硬编码 submissions.team3.tier01.classical。在干净临时根把团队目录换成 final_name，保留相同文件及 checker 路径顺序；导入新名称成功，原导入报 No module named 'submissions.team3'。当前 team3 名称下通过。 | 定稿队名后统一导入；Tier 1 可使用同层 from classical import decrypt_tier1，已由 worker 探针验证。用最终目录名重新打包测试。 |
| P2 · 共享模块位置 | 同样的干净根中直接 import classical_keystream 报 ModuleNotFoundError。Checker 不自动加团队父目录；根目录或 notebook 曾修改 sys.path 会掩盖问题。 | Tier 3/4 按真实团队包名导入共享模块，打包时连同团队根的 classical_keystream.py 一起提交。只依赖官方 common.crypto。 |

**整合条件。** Tier 1 的静态接口 measurement_to_key(c23…c0) → int → decrypt_tier1(key, hex) → str 与测试一致，可以开始联调。Tier 3 需 Junqi 提供按 oracle index 排序的 24 个 0/1 分类结果；Tier 4 需提供非零 10-bit 整数且 q[j] 对应第 j 位。在所查量子提交未见 Tier 3/4 solution.py。

**阶段外 SKIP（不计入上述 16 项）：** 三层真实 solve()、真实明文哈希、Aer 记录、Oracle 调用审查、转译指标、最终 zip 和整队评分均未执行。待团队入口、目录名、非零校验就绪，在干净官方仓库仅放最终团队文件，以固定依赖运行完整 checker，核对 hash、circuit_executed、metrics_status 和 flags，保留测量到密钥的证据，再判断满分资格。
