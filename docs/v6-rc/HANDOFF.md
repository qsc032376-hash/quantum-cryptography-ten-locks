# v6 RC independent review handoff for Youyang

Independent review of this combined RC and ZIP is pending. Sicheng can forward the exact commit and ZIP digest accompanying this handoff. Review the pinned commit in a clean checkout.

The unchanged official Checker ran in full mode on a renamed extraction of the runtime archive, with only the frozen official tools, common code, challenge tier directories and hashes present. The SHA label in the original report identifies the staged submission Git tree before the release commit. Match it to the immutable RC with the command below. The manifest identifies the source commits, each archived file and its digest. The ZIP is stored in the private repository.

| Measured aggregate across ten separate circuits | Value |
|---|---:|
| Two-qubit gates | 162,716 |
| Sum of per-tier depths | 369,186 |
| Total gates | 473,370 |

See [full official output](report.md), [machine-readable results and solve times](report.json), and [source and archive manifest](manifest.json). Ten hashes matched, ten circuits executed, all metrics were valid and all flag lists were empty. Each tier completed within its official timeout.

## Source checks

Tiers 1, 3 and 4 and shared classical files match frozen v5. Tiers 2, 6, 7, 8, 9 and 10 match their selected tier directories by Git diff. Tier 9 also matches the provisional integration. Official files match v5. Tier 5 uses the approved fallback oracle and the final accepted GF(2) rewrite at the tested point between transpilation and Aer execution. Its local module contains the pinned synthesis module and the original gf2_runs function extracted verbatim. Packaging those functions alongside solution.py avoids importing unrelated research drivers. The complete Checker reproduced the accepted Tier 5 metrics. The 22-qubit Tier 5 and Tier 9/10 v3 research variants are excluded.

## Independent replay

Use the exact SHA supplied with this handoff. From the root of a clean checkout at that SHA, run with the pinned requirements in Python 3.12. Substitute your own empty temporary directory paths.

~~~powershell
git rev-parse HEAD
git rev-parse HEAD:submissions/team3
python docs/v6-rc/build_zip.py HEAD "$env:TEMP/rebuilt-v6.zip"
Get-FileHash "$env:TEMP/rebuilt-v6.zip", drafts/ten-locks-v6-rc.zip
python -m zipfile -l drafts/ten-locks-v6-rc.zip
python -m zipfile -e drafts/ten-locks-v6-rc.zip "$env:TEMP/independent-v6"
Rename-Item "$env:TEMP/independent-v6/team3" youyang_rc
python -I tools/check_submission.py "$env:TEMP/independent-v6/youyang_rc" --sha (git rev-parse HEAD) --out "$env:TEMP/independent-v6-report"
~~~

Verify the tree and both archive digests against the manifest, compare the extracted files to the referenced blobs and compare all ten metric rows, hash results, circuit execution and flag lists. Record your independent decision against the exact RC SHA and ZIP digest. A passing unseeded run cannot guarantee future random outcomes. The archive is a runtime RC draft. The team README and linked competition write-up remain to be finalized before submission. Any archive change needs a fresh digest and review. Keep frozen v5 as the rollback.
