# Tier 10 缓存取证报告

日期：2026-11-11。分支：`research/tier10-extreme-superopt-v2`。
结论：**CACHE_RESOLVED**。未修改任何历史缓存、报告、RC 或最终包。

## 1. 原始字节哈希

| 来源 | 提交 / 路径 | 字节 | SHA-256（Git blob） | SHA-1 |
|---|---|---:|---|---|
| v6.1 RC | `0c043a4` `submissions/team3/tier10/public_operations.json` | 156,086 | `b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6` | `01502d42…` |
| v6.2 RC | `aee41fb` 同路径 | 156,086 | 同上 | 同上 |
| Tier 10 研究 | `7edfe87` `research/tier10_global/candidate.json` | 156,086 | 同上 | 同上 |
| Ultra-heavy | `9ca45f3` `submissions/team3/tier10/public_operations.json` | 156,086 | 同上 | 同上 |

四个版本的解析后 operations 完全相同，规范指纹均为
`2e6b5f9bda70192ffffc14766c870ec5488bcabe3df1797141a48d8f0c802644`。

## 2. 历史差异的解释

之前的 `62b6eb…82d6` 是 **Windows 工作区检出后的文件字节**，不是 Git blob。
该仓库在 Windows 上把 LF 转为 CRLF，行数约 5,000，故字节数增加；
`git show <commit>:<path>` 读出的是 LF 规范化后的 156,086 字节，SHA-256 为
`b5de82…`。两者 JSON 解析结果、operations 数组与语义完全一致。

因此：
- 期望值 `b5de82…` 对应 **Git blob / LF 规范化内容**；
- 旧报告中的 `62b6eb…` 对应 **CRLF 工作区副本**；
- 不是两个不同缓存，也不是内容错误或篡改。

## 3. 电路级等价

对规范缓存的 12 个不同乘子逐一重建受控乘子网络，并与理想受控置换比较：

- 完整 256×256 复算子：最大误差 **1.46e-13**；
- 逆算子：最大误差 **1.45e-13**；
- 77–127 padding 全部固定；
- 控制 0 为恒等，控制 1 为精确模乘；
- 无私有数据（仅公开乘子与置换）。

解析成功本身不作为等价证明；上述算子检查与全 128 输入符号检查才是证据。

## 4. 各次验收使用的缓存

- v6.1 的 38,823-CX Checker 与 v6.2 的 Tier 10 代码均使用上述
  `b5de82…` blob；
- 本研究 38,163 与 36,885 候选都基于同一缓存（仅叠加研究用的仿射覆盖，
  不改写缓存文件）；
- 最终包 `ca7290c` 的 Tier 10 仍是 v6 的 46,910-CX 实现，**不含**
  `public_operations.json`，因此不存在最终包与缓存哈希冲突。

## 5. 清理与证据

- 新增审计脚本与结果：`research/tier10_extreme_v2/cache_audit/audit.py`、
  `audit.json`。
- 未删除历史证据，未重写提交，未强推。
- 历史报告中较早的 `62b6eb` 记录保留，不修改；本报告给出正确解释。
