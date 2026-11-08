# Tier 9 独立复核交接 · Youyang

**状态：开发侧 ACCEPT；独立意见待填写。** 建议从 ZIP 重现一次 Tier 9 官方评分及两个等价测试。完整十关的原报告已封存；无需为这次交接再次运行十关。

| 对象 | 固定提交 |
|---|---|
| v2 基线 | `0cd8adc025e89fa190836e9295f6b5ffa482e17a` |
| 待评 v3 | `04feb70e52f5522aa2976ca9c7df2e48f27f3cce` |
| Tier 9 实现 | `f86a4422c1a609da9b24079cc916d69437d67af7` |
| Tier 9 实验记录 | `17df36d1c31cd441cd3bd840157caadd3062cada` |
| Benchmark Harness | `ab9676749e00da904d0b8076811a2407d3b7205f` |

**源码检查。** 从 v2 到 v3，提交目录中仅 `submissions/team3/tier09/solution.py` 的生成器导入和新增 `submissions/team3/tier09/shared_controls.py` 有差异。原来的 modular.py 仍供 Tier 10 使用；整棵 Tier 9 子树与 f86a442 一致，Git tree 为 `6d28f5c02b63a512d17b27c84c4c0d4ae39b661b`。以下第二条命令应无差异且退出 0：

```text
git diff --name-status 0cd8adc 04feb70 -- submissions/team3
git diff --exit-code f86a442 04feb70 -- submissions/team3
```

**数学检查。** 对同一控制掩码的连续受控 X，相同目标出现偶数次即相消。选剩余目标之一为枢轴 p，先从 p 扇出到其余目标，再对 p 做一次受控 X，最后反向扇出。控制关闭时两次扇出抵消；控制开启时每个选定目标恰翻转一次。控制条件不含这些目标。全部原语都是矩阵元为 +1 的置换，不改变相对相位；p 可以是任意态。候选没有额外或借用的辅助位，因此没有 clean/dirty 工作位需要复原。

原测试逐列验证 14 个公开幂次的全部 256 个控制/work 输入，包括控制关闭与 77–127 填充恒等，并检查原语、控制极性和全局相位。另在 N=15、两个底数、4+4 位缩小电路上比对全部复振幅、相位边际分布（绝对容差 1e−12）与 q[j] → c[j] 位序。完整题目保持 14 个相位位、7 个 work 位、真实 Aer 采样、基于测量恢复阶、RSA 解包和官方哈希校验。[原始实验证据](https://github.com/qsc032376-hash/quantum-cryptography-ten-locks/blob/17df36d1c31cd441cd3bd840157caadd3062cada/docs/TIER09_OPTIMIZATION_RESULT.md)

**复验命令。** 在本审计分支根目录、已安装官方 requirements.txt 的 Python 3.12 环境执行；脚本按固定 Git 对象取材，本地 clone 需要含实验分支历史。已有环境可直接复用。第二条命令使用一个尚不存在的输出目录：

```text
git fetch origin
python docs/release-audit/verify_zip.py
python docs/release-audit/review_tier09.py reports/youyang-tier09
```

复核脚本先在干净临时目录运行原版等价测试，再将 ZIP 解压改名为 independent_review。保留所有 helper，只在该临时副本移走其他九关的 solution.py，使原版 Checker 只发现 Tier 9。脚本的官方调用等同于：

```text
python -I tools/check_submission.py submissions/independent_review --sha 04feb70e52f5522aa2976ca9c7df2e48f27f3cce --out <review-output>
```

**验收值。** 两项测试通过；report.json 仅有 Tier 9，status=full、hash_ok=true、circuit_executed=true、metrics_status=ok、flags=[]。期望双比特门 **89,075**、深度 **235,048**、总门 **263,601**、活跃位 **21**；同机 v2 分别为 117,739、316,820、349,949、21。脚本会断言这些结果；如不符，请保留 report.json、版本与失败用例。本次开发侧已实际跑通此流程。[本次复演](release-audit/evidence/tier09-rehearsal.json)

**种子与运行代价。** 完整电路的原配对实验使用 Aer seeds 900–909。v2 和 f86a442 各 10/10 通过，每次 64 shots，核对实际转发的种子及明文哈希。基线 solve 4.823–5.102 秒，候选 8.245–9.005 秒。整包 v2/v3 同机 solve 为 4.881/8.618 秒，首轮 benchmark 的 Aer 作业为 4.752/8.258 秒。CX 降低 24.35%，深度降低 25.81%，理想模拟更慢；十个固定种子不是失败概率保证或硬件证据。[v2 种子记录](release-audit/evidence/tier09-v2-seeds.json) · [候选种子记录](release-audit/evidence/tier09-candidate-seeds.json)

如需审查采样，以下从当前仓库另开只读用途的 detached 工作树，在同一 Python 环境仅跑 Tier 9。将 REF 分别替换为 0cd8adc、f86a442，输出文件分别命名。该操作是可选的；不影响十关官方记录。

```text
git worktree add --detach ../tier09-review-harness ab9676749e00da904d0b8076811a2407d3b7205f
python ../tier09-review-harness/benchmarks/cross_seed_regression.py --tiers 9 --seeds 900 901 902 903 904 905 906 907 908 909 --ref REF --timeout 120 --total-seconds 230 --memory-mb 2600 --output reports/REF-review.json
```

独立复核完成后，请记录审查人、实际 SHA、环境、哈希匹配与门指标、差异及 ACCEPT / REJECT / 证据不足的判断。报告中只需汇总结果，无需公开阶、因子、密钥或明文。
