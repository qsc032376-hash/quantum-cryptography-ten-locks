# Team 3 v6 RC 独立验收

日期：2026-11-11。验收人：Youyang Shang（独立执行，不修改 RC）。  
RC 提交：`c4455782ea9388d5897fc27270f42dd3786ed35d`（`release/ten-locks-v6-rc`）。  
冻结回退：`release/ten-locks-v5-verified@41c7c67`（仍可用）。  
本文件只存在于验证分支 `validation/v6-final-independent`。

## 1. 来源与工作区

- 用 `git worktree add --detach` 在独立临时目录检出上述精确提交；`git rev-parse HEAD`
  与期望一致，工作区干净（0 个改动）。
- `git rev-parse c445578:submissions/team3` = `5d825abd0f0c82546c83574bf4148c3a92238d83`，
  与 RC 报告中的 `submission-tree:...` 标签逐字符一致。
- 官方文件与冻结 v5 逐一比较（`common/`、`tier01`–`tier10`、`tools/`、`hashes.txt`、
  `requirements.txt`、`SCORING.md`、`README.md`、`CHALLENGE.md`、`HELPERS.md`、
  `.github/`）：**diff 为空**。

## 2. 生产代码范围

相对 v5，`submissions/team3` 只改动预期文件：

```
M tier02/solution.py
A tier05/gf2_synthesis.py      M tier05/oracle.py   M tier05/solution.py
M tier06/solution.py           M tier07/qpe.py
M tier08/modular.py            M tier08/solution.py
A tier09/global_permutation.py M tier09/shared_controls.py M tier09/solution.py
M tier10/shared_control.py     A tier10/synthesis.py
```

Tier 1/3/4 与共享经典模块未改。逐项对照 manifest 的 source 提交，以下目录与
声明源码**逐文件零差异**：T2 `689c998`、T6 `5a73467`、T7 `7aef6e7`、T8 `b92a17f`、
T9 `00fee41`、T10 `be78cc1`；T5 的 `oracle.py` 与 `0988ac4` 零差异。

Tier 5 的 GF(2) 改造是**运行期**变换：`solution.py` 在正常基门转译之后、送入
Aer 之前调用 `gf2_synthesis.gf2_runs(compiled)`；`gf2_synthesis.py` 为 109 行
自包含模块（高斯消元综合 + 显式 CNOT 块提取），不导入研究驱动。Checker 实测
Tier 5 为 14,552 门 / 19 活跃位，确认使用的是 19 位 GF(2) 方案，而非被排除的
22 位 clean-ancilla 版本。

Tier 8 实测 33,904 2Q，即 OSC 验收的 hybrid 实现；Tier 9 为 v2（55,999），
与未选 v3（55,971）不同；Tier 10 为 v2（46,910），与未选 v3（46,038）不同。
无官方 Oracle/Helper/Checker/评分配置改动，无硬编码因子、指数、密钥或明文。

## 3. ZIP 可复现性

- 现有 `drafts/ten-locks-v6-rc.zip` SHA-256 =
  `b6e40b2d3b1802c7cd193c3307ac442a816599b34ded196b89dca72ca65747c3`，与期望一致。
- 用 RC 自带 `docs/v6-rc/build_zip.py` 在精确提交上重建：SHA-256 **仍为同一值**，
  **逐字节可复现**；30 个条目的名称与内容与原件完全一致。
- 30 个文件的内容 SHA-256 与 `manifest.json.contents_sha256` **全部匹配**，没有
  缺失或多出的条目。压缩包仅含 `.py`（无一测试、文档、缓存或证据），目录为单一
  `team3/` 根。
- 全量扫描 30 个源文件：无 `C:\`、`/Users/`、password、token、私钥标记等
  绝对路径或凭据。

## 4. 独立官方 Checker

从重建 ZIP 解压到独立目录，将 `team3` 改名为 `youyang_rc`，使用未修改的
`tools/check_submission.py` 与固定环境（Python 3.12.10、Qiskit 2.6.1、Aer 0.18.2）
执行 `--sha c445578...`。总墙钟 **110.2 秒**，无超时。

**结果：10/10 `full`、10/10 SHA-256 `match`、10/10 实际执行电路、10/10 指标有效、
全部 flags 为空。**

| Tier | 2Q | 深度 | 总门 | 活跃位 | solve 秒 |
|---|---:|---:|---:|---:|---:|
| 1 | 151 | 44 | 298 | 25 | 7.79 |
| 2 | 0 | 3 | 3 | 1 | 0.93 |
| 3 | 7,808 | 8,771 | 19,497 | 7 | 8.59 |
| 4 | 183 | 195 | 455 | 20 | 0.25 |
| 5 | 14,552 | 28,132 | 40,938 | 19 | 10.89 |
| 6 | 3,000 | 5,715 | 8,752 | 22 | 14.04 |
| 7 | 209 | 266 | 727 | 15 | 0.20 |
| 8 | 33,904 | 96,055 | 102,561 | 18 | 9.06 |
| 9 | 55,999 | 120,242 | 168,116 | 22 | 15.74 |
| 10 | 46,910 | 109,763 | 132,023 | 19 | 4.37 |

**合计（十条独立评分电路的和，不是单条联合电路）：**

| 指标 | 本次独立实测 | RC 报告 |
|---|---:|---:|
| 双比特门 | **162,716** | 162,716 |
| 逐层深度之和 | **369,186** | 369,186 |
| 总门数 | **473,370** | 473,370 |
| 活跃位之和 | 168 | — |

每层指标与 `docs/v6-rc/report.json` 逐项一致；电路记录总数 2,082 条（主要是
Tier 2 的 2,048 次测量）。

## 5. 已有证据审阅（未重复运行 OSC）

- **Tier 5**：`docs/TIER05_FINAL_SELECTION.md`（提交 `0134d0d`）记录
  `ACCEPT_GF2`：B 版 14,552 / 28,132 / 40,938，19 活跃位；十组 OSC 配对与一次
  独立官方 Checker 通过；明确排除 22 位 clean-ancilla。
- **Tier 8**：`docs/TIER08_OSC_VALIDATION.md`（`3dac27e`）记录 Cardinal 十组配对
  全部通过，候选 33,904 / 96,055 / 102,561，活跃位 18 不变；含全复算子等价审计。
- **Tier 9**：`docs/TIER09_FINAL_DECISION.md`（`8501328`）明确 `INCLUDE_V2`，并
  **保留历史 Harness 的 INCONCLUSIVE 标签**，不把它改写成自动 ACCEPT；v2 经
  OSC 十组与官方 Checker 后入选，v3 未采用。
- **Tier 10**：v2 已由独立审计 `V6_TIER10_INDEPENDENT_AUDIT` 通过，19 位全态矢
  与 v5 等价到 6.5e-15；v3 与 20 位 clean-ancilla 未入选。
- **Junqi 技术复核**（`a03d45d`）：源码/证据审阅，明确“不是新的模拟运行、不是
  本独立审计”；其结论与本次实测相符。

OSC 是经典模拟集群，不是物理量子硬件；有限种子与固定 Checker 单次运行都不构成
零失败率保证。

## 6. 提交结构

- 解压 ZIP 后 30 个 `.py`：十个 `tierNN/solution.py` 齐备，含共享经典模块
  （`classical_keystream.py`、`rsa_classical.py`、`dh_classical.py`、
  `toy_cipher_classical.py`、`tier07_classical.py`）与 tier 级 helper/oracle/
  modular/QFT 模块；无研究实验、测试、证据或缓存。
- 所有十个 solution 在干净解压中被官方 Checker 实际导入并执行 Aer，导入路径正常，
  无仓库外依赖。
- **`submissions/team3` 中没有任何 README.md 或 WRITEUP.md**；RC handoff 也写明
  “team README 与 competition write-up 仍需完成”。因此归档是运行期草稿，不是
  可提交的最终包。

## 7. 风险与限制

- 本次 Checker 是一次未注入种子的运行；不证明其他种子/负载下零失败。
- Tier 9 活跃位由 21 增至 22；Tier 5 的 GF(2) 运行期改写使 solve 变慢（10.89 s），
  门数收益不等于模拟加速。
- Tier 6/7/8/9/10 的种子证据有限；OSC 数据为经典模拟。
- 未验证比赛平台上传、团队 README/WRITEUP、最终 ZIP（尚不存在）。
- 任何 RC 源码或归档变更都需重新计算 ZIP 摘要并重跑本审计的相应部分。

## 8. 结论

**ACCEPT_RUNTIME_RC — FINAL_PACKAGE_PENDING**

精确 RC 源码、ZIP 可复现性与独立十关 Checker 全部通过；因缺少团队 README 与
WRITEUP，最终提交包尚未就绪，不能宣称已完成官方提交或已冻结发布。
