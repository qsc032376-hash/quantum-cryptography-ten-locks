# 提交状态：Tier 1–6 稳定基线与 Tier 7 接入

准备分支基于 `integration/tier06@075b690`。Tier 1、Tier 2–3、Tier 4、Tier 5 的各关文件分别与 `54cf863`、`5929deb`、`980b87e`、`fad1a13` 一致。复用已保存的 Checker 证据，并核对了 `hashes.txt` 与评分配置的摘要。未重新运行量子电路。

| Tier | 官方 Checker | 明文 SHA-256 | 双比特门 | 深度 | 总门数 | 活跃 qubit |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | full | 匹配 | 151 | 44 | 298 | 25 |
| 2 | full | 匹配 | 0 | 3 | 3 | 1 |
| 3 | full | 匹配 | 7808 | 8771 | 19497 | 7 |
| 4 | full | 匹配 | 183 | 195 | 455 | 20 |
| 5 | full | 匹配 | 21150 | 33055 | 58620 | 19 |
| 6 | full | 匹配 | 3000 | 5883 | 9534 | 22 |
| 7 | 待验证 | 未验证 | — | — | — | — |

Tier 1–6 的评分指标均有效，无超时或复核标记。[Tier 6 的验证记录](TIER06_INTEGRATION.md)确认校准和搜索均被 Checker 记录，最后选中 12 轮搜索电路：校准 2048 shots，搜索 640 shots。未发现既有的 `integration/submission-preparation` 分支，本清单不增加展示材料。

## Tier 7 经典接口与后续验收

已从 `feature/classical-implementation@6c9ce26` 只读取 `submissions/team3/tier07_classical.py`，临时放入改名团队目录，与基线中同版本的 `classical_keystream.py` 和现有公共模块测试。4 个合成测试通过，覆盖整数边界、前导零、正反位序、改名导入、合成解密及官方哈希比较接口。生产模块尚未引入，准备分支仅提交本清单与测试。

- [官方 Tier 7 规则](../tier07/README.md)规定相位为 $\phi=k/2^{14}$，整数 $0\le k\le16383$。待实现的无参 `solve()` 在 Aer 上测得相位，读出整数 `k`，将 `load_locked(7)` 的 `ciphertext_hex` 传给 `tier07_classical.decrypt(k, ciphertext_hex)`。经典模块按 `format(k, "014b")` 保留前导零，返回 UTF-8 字符串；核对 `QC-07: ` 前缀和 SHA-256 后返回该字符串。
- 先核对实际逆 QFT 与测量映射。若输出 $q_j$ 承载 $k$ 的第 $j$ 位且映射到同编号经典位，单寄存器字符串按 [Qiskit 位序](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering)为 `c13…c0`，直接用 `key_from_bitstring`。仅当电路确实让相位最高位落在经典位 0 且其余位也整体反转时，才用 `key_from_reversed_register`。逆 QFT 省略 SWAP 时先查清置换是在输入端还是输出端；接入后用已知的非对称相位验证映射。
- Junqi 的远端分支目前止于 Tier 6。待 Tier 7 电路发布后，验证特征态准备、受控幂保留全局相位、位映射、真实 Aer 执行及官方哈希。按[评分规则](../SCORING.md)，Checker 收集 `solve()` 送入 Aer 的所有电路，转译后选双比特门最多的一条，同数时选深度最大者；展示用 `build_circuit()` 本身不计分。

复现合成测试：先 `git fetch origin feature/classical-implementation`，再运行 `python3 -B tests/test_tier07_preparation.py`。不读取官方 Tier 7 酉算子、真实相位或真实密文。
