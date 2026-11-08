# v2 发布就绪审计

**结论：READY_WITH_CAVEATS。** 对现有官方 Checker 的单团队、每关新进程模型，未发现阻断性提交问题；同进程多团队隔离缺陷和 Tier 10 独立报告缺口须保留。工程就绪不等于已经提交或获得比赛平台裁定；未上传 ZIP，也未创建正式 release。

## 来源与既有验证

- 审计目标：`integration/optimized-v2-candidate@0cd8adc025e89fa190836e9295f6b5ffa482e17a`；父提交为冻结回退 `release/ten-locks-v1@868fb65e20c73a27bffc118f3617080df9cf2f8b`。v1→v2 diff 仅有集成报告及两个生产文件。
- Tier 5 `oracle.py` 与 [`804b9dd`](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/commit/804b9dd349a40edd834fd06dfb2ceb09c6658bfc) 字节相同；[独立验收 `ab96767`](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/ab9676749e00da904d0b8076811a2407d3b7205f/docs/TIER05_INDEPENDENT_ACCEPTANCE.md) 给出人工 ACCEPT、官方 Checker 和五组配对种子证据，明确不是零失败率证明。
- Tier 10 `dh_classical.py` 与 [`44766ba`](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/commit/44766baa3f9ba5859cc32f45fc53feaf8807af4b) 字节相同；该提交只含源码变更。检索仓库当前远端分支的文档及测试路径后，未找到针对该提交的独立验收报告。[作者的接口交接说明](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/dad1190f29ad5ac015fde7ffcee28f2cdc248983/docs/TIER10_CLASSICAL_INTERFACE.md)描述容错并自述测试，不能视为独立报告；不补造历史结果。本次复用 [v2 集成记录](OPTIMIZED_V2_CANDIDATE.md)中的 4 项合成集成测试、额外人工参数检查与真实 Checker 证据。
- Tier 1–4、6–9、Tier 10 量子电路和正式 `solve()`、官方代码及配置未变。Tier 5 保留 25 次量子 Oracle；Tier 10 仍运行量子电路。v2 集成记录保存的实际 Tier 10 电路 QPY 与 v1 记录字节一致。

原 v2 [集成报告](OPTIMIZED_V2_CANDIDATE.md)中的完整官方 Checker：**10/10 `full`、10/10 SHA-256 匹配、指标齐全、flags 空**。审计读取了仍存在的原始本地 Checker JSON：`sha` 元数据字段当时未指定；为核对身份，本次把当时实际检查的改名团队副本中 27 个跟踪文件逐字节与 `0cd8adc` 比较，全部一致。它是本地官方 Checker 运行记录，并非比赛平台提交证明。本次没有重复完整 Checker 或 Tier 5 配对种子。

| 实际评分指标 | v1 | v2 |
| --- | ---: | ---: |
| Tier 5 双比特门 / 深度 | 21,150 / 33,055 | 15,150 / 29,503 |
| Tier 5 总门 / 活跃 qubits | 58,620 / 19 | 42,211 / 19 |
| Tier 10 双比特门 / 深度 | 107,168 / 287,674 | 107,168 / 287,674 |
| Tier 10 总门 / 活跃 qubits | 317,957 / 19 | 317,957 / 19 |

## 同进程团队隔离：发现非阻断缺陷

`dh_classical.py` 把团队路径放入 `sys.path` 后使用顶层名称导入 `rsa_classical` 和 `classical_keystream`。`sys.modules` 已缓存同名模块时，第二个团队优先复用第一个团队的模块，而不是解析第二个目录。测试把同一源码复制为 `team_alpha`、`team_beta`，分别测试两个导入顺序：第二个团队的 DH 和 Tier 10 readout 文件本身来自第二目录，但其 RSA 与密钥流依赖来自第一目录。第二目录的 Tier 8/9 解密函数来自第二团队的包内 RSA 文件，该文件内部的顶层密钥流依赖仍来自第一目录。

为证明功能影响的可能性，测试仅在临时进程中将第一团队的 `mod_inverse` 替换为合成哨兵，再导入第二团队；第二团队引用了哨兵并返回错误的合成结果。没有修改任何团队源码文件。两份未修改的相同副本中，来源错配本身不证明结果已经错误；不同团队实现或预先污染的缓存可产生实际错误。

官方 `tools/check_submission.py` 的 `run_worker` 为每关启动新 Python 子进程，单次 `worker_solve` 只加载一个团队的 `solution.py`；它不把前一团队的 `sys.modules` 继承进下一进程。新的 Checker 风格进程实测解析到当前团队的共享依赖，因此上述跨团队复用场景**不阻断当前官方模型**。这不是所有长期服务、嵌入式调用或第三方评测器的保证；此类环境应按团队/关卡隔离进程，或在后续独立版本设计包相对导入并重新验证，不能在已验证包上临时打补丁。

最小可复现测试：[tests/test_v2_import_isolation.py](../tests/test_v2_import_isolation.py)。执行 `python -B -m unittest tests.test_v2_import_isolation -v`，2 项通过（包含两个污染顺序和干净 Checker 风格进程）。扩展测试时曾因测试断言把 `decrypt_tier8` 写成 `decrypt_tier08` 而报错；修正测试名称后两种顺序通过，没有改动提交算法，也未重跑 Checker。

## ZIP 与回退

现有 v2 `ten-locks-v2-team3-draft.zip` 的 SHA-256：`9e4fb149f67898e737ebf88a197b2df22a0035cafa015ede3c86383e1f31f49a`。复用 [`2ebf7a1` 的既有打包脚本](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/2ebf7a1f64bf5450ca862d2e6dba2eaf7718e1d0/tools/package_release_draft.py)，只在运行时传入精确 commit `0cd8adc` 和当前仓库根目录，在临时目录重建；本机输出与现有 ZIP **逐字节相同**。压缩器版本可能影响跨环境字节复现，应同时核验文件内容。

独立解压验证：ZIP 恰有一个 `team3/` 顶层目录、25 个 `.py` 文件，清单等于精确提交中团队源码排除仅供本地运行的两个 Tier 1 测试/验证文件；CRC、无重复/越界路径和每个文件与提交的逐字节比较均通过。改名后在干净子进程按 Checker 风格加载十关及共享依赖，10/10 通过。无文档、日志、缓存、环境、官方锁文件或额外依赖被打包；常见 PEM 私钥、云访问令牌及常见 API token 特征扫描未命中。该扫描和来源核对不能数学证明不存在所有可能的秘密；未输出或检查真实隐藏密钥/明文。ZIP 解压后的完整 Checker 本轮没有重跑，原有全量结果来自字节一致的团队源码副本。

v1 回退 `ten-locks-v1-team3-draft.zip` 仍在，SHA-256 与原记录一致：`62351aca20d8fac24723aaf1418620e60b425db0d3c5f28a020da63d82bc3e3a`。未上传比赛平台。

同环境复现打包，输出路径必须不存在（`2ebf7a1` 对象需在本地）：

```sh
python - <<'PY'
import pathlib, runpy, subprocess, sys, tempfile
root = pathlib.Path.cwd()
with tempfile.TemporaryDirectory() as tmp:
    script = pathlib.Path(tmp) / 'package_release_draft.py'
    script.write_bytes(subprocess.check_output(['git', 'show', '2ebf7a1:tools/package_release_draft.py']))
    main = runpy.run_path(str(script), run_name='v2_packager')['main']
    main.__globals__['BASE'] = '0cd8adc025e89fa190836e9295f6b5ffa482e17a'
    main.__globals__['ROOT'] = root
    sys.argv = [str(script), '/tmp/team3-v2-reconstructed.zip']
    main()
PY
```

## 剩余风险

现有固定种子 Aer 验证、五组 Tier 5 配对种子和合成测试均是有限理想模拟证据；不保证其他种子或真实硬件。Tier 10 经典修复的独立历史报告仍缺失，且其通用部分方程处理存在有界候选展开；本次正式 Tier 10 路径只传入已验证的完整模数见证。正式提交前应确认平台确实使用上述新进程模型，并保留回退包。
