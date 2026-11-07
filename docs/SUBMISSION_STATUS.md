# 提交状态：Tier 1–7 已验证

集成基于 `integration/tier07-preparation@d5f4bd8`。Tier 1–6 文件保持不变；复用各关 Checker 证据，并核对了 `hashes.txt` 与评分配置的摘要。仅对 Tier 7 运行了新的官方 Checker。

| Tier | 官方 Checker | 明文 SHA-256 | 双比特门 | 深度 | 总门数 | 活跃 qubit |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | full | 匹配 | 151 | 44 | 298 | 25 |
| 2 | full | 匹配 | 0 | 3 | 3 | 1 |
| 3 | full | 匹配 | 7808 | 8771 | 19497 | 7 |
| 4 | full | 匹配 | 183 | 195 | 455 | 20 |
| 5 | full | 匹配 | 21150 | 33055 | 58620 | 19 |
| 6 | full | 匹配 | 3000 | 5883 | 9534 | 22 |
| 7 | full | 匹配 | 230 | 271 | 760 | 15 |

Tier 1–6 的评分指标均有效，无超时或复核标记。[Tier 6 的验证记录](TIER06_INTEGRATION.md)确认校准和搜索均被 Checker 记录，最后选中 12 轮搜索电路：校准 2048 shots，搜索 640 shots。未发现既有的 `integration/submission-preparation` 分支，本清单不增加展示材料。

## Tier 7 QPE 端到端验证

量子算法及构造取自 `68bfd80`，`tier07_classical.py` 原样取自 `e420753`；所需的 `classical_keystream.py` 已在基线中且内容一致。集成仅修复了固定团队路径的导入，并在返回前检查完整前缀 `QC-07: ` 和官方 SHA-256。改名团队目录中的正式 Checker 验证为 `full`；未读取隐藏相位或记录真实密钥、测量字串或明文。

- [官方 Tier 7 规则](../tier07/README.md)规定 $\phi=k/2^{14}$。电路由 $q_j$ 控制 $U^{2^j}$，使用带首尾交换的完整逆 QFT，随后 $q_j\to c_j$。按 [Qiskit 位序](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering)，单寄存器的 `c13…c0` 直接转成整数，不反转。`solve()` 把测得的整数和公开密文传给 `tier07_classical.decrypt(k, ciphertext_hex)`，由经典模块按 14 位编码并保留前导零。
- 一次真实 Checker 运行包含 **2 个 Aer 批次**：QPE 64 shots、相位抵消检查 32 shots，均通过。每条电路含 14 个压缩受控 $U^{2^j}$ 块，共 28 个电路块，按 shots 计为 1,344 次逻辑块应用。若展开为逐次受控 $U$，则每 shot 等价 16,383 次，全批次 1,572,768 次；实际没有逐次执行这么多基础门。重复平方保留给定 $U$ 的全局相位，不求经典本征值。
- [评分器](../SCORING.md)记录两条电路。抵消电路的双比特门、深度、总门数、活跃位分别为 27、166、263、15；双比特门更多的主 QPE 电路获选，指标见上表。求解计时（含聚合观察器）0.105 秒，工作进程峰值 RSS 96.2 MiB；无超时、内存错误、缺失指标或复核标记。观察器只统计执行，未更改原始 Checker、电路或筛选逻辑。

Junqi 的 24 个合成/模拟用例和准备分支的 4 个经典接口用例全部通过；只在内存中将旧解密 mock 文本补上要求的前缀。正式验收使用真实密文和实际测量。结果来自理想 Aer；噪声下的位序和相位正确性仍需验证，不能从本次结果推断硬件成功率。

复现官方验收：将团队根的 `tier07_classical.py`、`classical_keystream.py` 及 `tier07/{solution.py,qpe.py}` 按原层级复制到临时改名目录，再运行 `python -B tools/check_submission.py <renamed-team-dir> --out <private-report-dir>`。
