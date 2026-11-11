# v6.3 runtime cache and archive manifest

Candidate A preserves the exact v6.2 Git blobs. The independently calculated digests below refer to raw bytes. The CRLF column is an in-memory diagnostic. No cache file was rewritten.

| Tier | Git/ZIP bytes | Git blob contents / ZIP member SHA-256 | Hypothetical CRLF SHA-256 |
|---|---:|---|---|
| 09 | 9,916 | `06c9a4fc5a30c893a9bd1e4e0b862070c2b2a17545a9d10e5465fa6dc7f1083b` | `e898fb78da461946d1cd4f15fb855d5c42dc3eff534b217cf9ccde2107304d92` |
| 10 | 156,086 | `b5de825230fba9ff3c01b6d0237685b836aea319dccab9d8d7e50b20447a1db6` | `62b6ebf880d91d7f71bd981a51c037c1305bd3fbe875d6e078649ad6c03182d6` |

The Tier 10 study at 9ca45f3 recorded the CRLF digest. Replacing LF with CRLF alone reproduces that digest, and parsing either byte sequence yields identical ordered operations. Deliver the LF members from Git. Tier 8's final selected numeric tables are embedded in its extreme_synthesis.py module.

ZIP: `drafts/ten-locks-team3-v6.3-rc.zip` (37 files). SHA-256: `64c0e648010b3e601d3696e051b7f31ed4bbe8d3b8039c22b10fb2a4c7806c94`. Tested team tree: `b965048fa4d7db33876b33c60e5a9e206085f1ee`. [Full member digests](v63-evidence/zip-manifest.json). The archive contains a single team3/ root, both team documents, all ten entries, both JSON caches and runtime Python modules. Development tests, research files and generated caches are excluded. Production members are read directly from Git.
