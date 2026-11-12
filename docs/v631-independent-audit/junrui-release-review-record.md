# v6.3.1 release review record

**RELEASE_BLOCKED pending independent sign-off.** Junrui completed package verification. Junqi Sheng was sent the independent audit request via Outlook at his OSU address on November 12, 2026. The request included the immutable archive link, member comparison, full digest, expected results, verification steps and deadline. Delivery action completed; no reviewer decision is recorded here.

| Item | Record |
|---|---|
| Package commit | 2fe40b2d096d87875244d5ccbb8a76ef979ac499 |
| Documentation source | Youyang's fd8d3a0f8f89aa9566c9ed25f071a64f1d177f96 |
| ZIP SHA-256 | 4f1b2de8c7b554bed75319ab7f965937bad85906aa11a26172f5573dc24dfb52 |
| Clean official checkout | fce7c3950d06bb4d23e3c057b4625f901c396de4 |
| Local verification | 10/10 FULL, ten matching hashes, all tiers executed circuits, valid metrics, empty flag lists, zero timeouts |
| Aggregate | 103,166 CX / 217,625 sum of depths / 294,982 total gates |
| Independent decision for this exact ZIP | Pending |
| Approved v6.3 fallback | ce75c0721622d363e77912191a52a02c34f92472 / ZIP SHA-256 64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94 |

The ten README metric rows were compared programmatically with the official report. Technical edits to Youyang's draft clarify the Tier 8 and Tier 9 synthesis families, Tier 10 baseline history, probabilities versus amplitudes, seed sample scope, historical acceptance and the metric variation recorded in e49ed058ed83b43866ffca4ca9b9785e3f9301ed. The [manifest](V631_PACKAGE_MANIFEST.md) records each member in both ZIPs. The [full Checker report](V631_FULL_CHECKER.md) binds the fresh run to the new digest. The package contains no audit evidence or generated files. Keep the old approved ZIP available until another team member signs the new digest. No platform upload was made.
