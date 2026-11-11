# v6.3 independent release audit handoff

Candidate A's base is aee41fb328027f8927a55d65c68e8a3e30332697. Pin the exact v6.3 commit supplied in the integration handoff; the immutable team directory tree must be b965048fa4d7db33876b33c60e5a9e206085f1ee. Junrui prepared the RC. Independent acceptance of this commit and ZIP is pending.

1. In a fresh checkout of the private RC at that commit, run git rev-parse HEAD:submissions/team3. Compare the staged runtime changes against v6.2. Verify the Tier 8 module and dispatcher against 8b18d3d18a6ee6b744e5ce60af13ed1c4f259c9d, and the Tier 5 selected builder/configuration against 97fcc0c7d6dec3b7385dc237d47d89d4d6ffd15c. The Tier 5 solver precompilation level is 2, the official scoring level is 1.
2. Independently hash drafts/ten-locks-team3-v6.3-rc.zip and all 37 members before running Python. Compare with [the manifest](v63-evidence/zip-manifest.json). Confirm the JSON assets match v6.2 Git bytes, and check the README and write-up distinguish their historical v6 evidence from this RC.
3. In a fresh official checkout pinned to fce7c3950d06bb4d23e3c057b4625f901c396de4, extract that exact ZIP to submissions/. The official tree originally has no submissions/team3. Use Python 3.12 with the pinned requirements. From the official root run the following, with an output directory outside the submission.

~~~text
python -I tools/check_submission.py submissions/team3 --out AUDIT_REPORT
~~~

4. Compare all ten status, hash, circuit execution, metrics and flag fields with [the ZIP run](v63-evidence/zip-checker/report.json). Record any differences. For targeted checks, run the next commands from a disposable RC checkout, substituting the absolute path to the fresh official root. psutil is required for RSS sampling. Keep independent evidence separate from the committed results.

~~~text
python docs/v63-evidence/operators.py OFFICIAL_ROOT
python docs/v63-evidence/seeds.py OFFICIAL_ROOT
~~~

5. Record your identity, date, exact commit and ZIP SHA-256, package-content review, new Checker report and disposition. A source-level or historical research acceptance does not approve this ZIP. If release approval is withheld, the separate frozen v6 package on release/ten-locks-v6-final-package remains available. No competition upload is part of this handoff.
