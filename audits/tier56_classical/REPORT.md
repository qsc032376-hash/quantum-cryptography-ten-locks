# Tier 5–6 经典模块独立验证

验证基线：`origin/feature/classical-implementation` 的 `cd8e48745113999485e780aaef5df1d71fccafa5`。在独立 worktree 中运行；输入全部为合成数据。未使用真实密文、密钥或 Oracle。

| 状态 | 数量 | 覆盖 |
| --- | ---: | --- |
| PASS | 16 | 位序、前导零、位宽边界、已知答案与二进制往返、十六进制和 UTF-8 异常、前缀与 checksum、坏候选跳过、普通异常文本脱敏、Checker 导入。 |
| FAIL | 2 | 非法 checksum 遇空批次时被忽略；浮点位宽未被 API 一致拒绝。 |
| SKIP | 1 项集成验证 | 未跑 Checker 全流程或 Aer。受审分支没有团队版 Tier 5、6 的 `solution.py`，运行环境也未安装 Aer。 |

运行：在审查 worktree 根目录执行 `python -B audits/tier56_classical/test_audit.py`。实测 Python 3.13.9、PyYAML 6.0.3，18 个 unittest 用例（16 成功、1 断言失败、1 异常，退出码 1）。没有 PyYAML 时，三个导入探针会跳过。静态已知答案从公开的位掩码、S-box 与置换规则独立计算，测试另做 256 字节往返。

## 已确认的问题

| 等级 | 复现与结果 | 建议 |
| --- | --- | --- |
| P2 | `filter_candidates(6, [], "aa", 256)` 返回 `[]`；负数、布尔值、字符串和浮点 checksum 也一样。传入非空候选列表则会抛 `ToyCipherError`。空批次会把配置错误误报成无候选。 | 在消费候选之前统一验证 checksum 类型和 0–255 范围，覆盖空批次。 |
| P3 | `key_from_int(1, 10.0)` 在移位处抛原生 `TypeError`。等值浮点数通过了宽度成员检查，绕过了模块自有错误类型。 | 对公开入口统一校验整数位宽，只接受 10 或 14。 |

`ChecksumError` 的 `str`、`repr` 和常规异常摘要均不打印候选密钥；该值仍保存在 `error.key`，因此结构化日志不应直接序列化整个异常对象。`filter_candidates()` 能跳过坏候选的格式、校验和、UTF-8 错误；非法 tier、缺失 checksum、坏密文和注入的非预期 `RuntimeError` 都会抛出。

## 集成建议

- Tier 5 使用 10 位，Oracle 检查 `QC`；Tier 6 使用 14 位，Oracle 只标记 `Q`，随后用整段解密后的字节之和模 256 与公开值比较。位 $j$ 的权重为 $2^j$。固定宽度的测量字符串从高位到低位；按 qubit 索引传入的列表则从低位到高位。
- 对测得的整数密钥去重，并按 tier 显式调用 `matches_prefix`（Tier 5：`b"QC"`；Tier 6：`b"Q"`）。当前 `filter_candidates()` 按约定依赖前置标记：用合成数据实测，Tier 5 可返回合法 UTF-8 的错前缀文本，Tier 6 可返回 checksum 匹配的错前缀文本。它返回明文列表，不能单独证明候选合格或唯一。
- 用未经修改的官方 `load_solution()` 在临时目录加载两个合成 `solution.py`，复刻 Checker worker 的搜索路径和工作目录。直接导入团队根模块失败；硬编码 `submissions.team3` 在目录改名后失败。根据 `Path(__file__).resolve().parents[1]` 定位团队根再导入，两个 tier 在原名和改名目录均通过。接入团队实现后，先复测导入和前缀边界，再运行完整 Checker。
