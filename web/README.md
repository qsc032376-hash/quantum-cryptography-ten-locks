# Ten Locks — guided quantum demo (web)

A static, front-end-only walkthrough of the ten-lock quantum cryptography challenge:

- **Dashboard** with one lock card per tier (algorithm, level, points, recorded metrics).
- **Detail view** for every tier: problem, quantum approach, circuit schematic, measurement
  analysis, classical post-processing, official checker verification, complexity metrics.
- **Deep dives** written for Tier 1 (Bernstein–Vazirani), Tier 5 (Grover) and Tier 10
  (Shor discrete logarithm); the remaining tiers get shorter but accurate overviews.
- **Tier 5 before/after panel**: frozen-release baseline vs. an independently accepted
  optimized candidate, with percentage improvements and side-by-side bars.
- **Presentation mode**: five curated slides for judges, keyboard navigation
  (`←`/`→`/`Home`/`End`), `Esc` back to the dashboard, projector-sized typography, and
  pre-recorded numbers — no live Aer execution.
- **Deep links**: `#tier-3` opens a tier, `#present` opens the slides (useful for a projector).

No backend. The app is a single Vite build and runs entirely in the browser.

## Requirements

- Node.js 20 or newer (tested with the bundled Node 24 runtime)
- pnpm 10+ (or npm)

## Install and run

```bash
cd web
pnpm install
pnpm dev          # http://localhost:5173
```

If `pnpm` refuses to run `esbuild`'s postinstall under its supply-chain policy:

```bash
pnpm approve-builds --all
pnpm rebuild esbuild
```

## Scripts

| Command | Purpose |
|---|---|
| `pnpm dev` | Vite dev server with HMR |
| `pnpm typecheck` | `tsc --noEmit` (strict, no unused locals/params) |
| `pnpm test` | Vitest + Testing Library (jsdom) |
| `pnpm build` | typecheck then production build into `dist/` |
| `pnpm preview` | serve the production build locally |

`dist/` is a plain static bundle (`base: "./"`), so it can be served from any path.

## Tests

```
Test Files  6 passed (6)
Tests       21 passed (21)
```

- `intro.test.tsx` — hero, presentation entry point, provenance link.
- `dashboard.test.tsx` — ten cards, open/close detail, `Esc` navigation.
- `detail.test.tsx` — required sections, illustrative/recorded badges, focus handling,
  Tier 10 recorded metrics.
- `tier5.test.tsx` — both runs, 28.4% / 10.7% improvements, "candidate · not merged" status.
- `presentation.test.tsx` — button and keyboard navigation, progress dots, pre-recorded note.
- `accessibility.test.tsx` — accessible names on buttons and schematic images, labelled
  modal dialog, single `h1`, labelled presentation region.

## Data provenance and security

**Recorded (authoritative).** Per-tier circuit metrics and checker status were produced by
`python tools/check_submission.py submissions/<team>` on the frozen release
`release/ten-locks-v1`, inside a fresh copy of the repository. They are stored verbatim in
`src/data/tiers.ts` and labelled **Recorded** in the UI.

**Illustrative (teaching figures).** Circuit schematics and outcome histograms are hand-built
from the public algorithm descriptions. They are not screenshots of a run and are labelled
**Illustrative** everywhere they appear.

**Not bundled.** No hidden keys, recovered secrets, real decrypted messages, private oracle
code, `locked.json` contents, credentials or infrastructure configuration are included.
The Tier 5 candidate numbers live in `src/data/tier5.ts` and are marked as an independent,
non-merged acceptance result.

## Tier 5 comparison

| Metric | Frozen release | Candidate |
|---|---|---|
| Two-qubit gates | 21,150 | 15,150 (−28.4%) |
| Depth | 33,055 | 29,503 (−10.7%) |

The candidate folds the public S-box and bit-permutation tables into the oracle wiring and
removes duplicated fixed work. It passed the official checker on its own branch; the UI
explicitly states that the frozen release remains the submission baseline and that the
optimized circuit has **not** replaced it.

## Limitations

- No live quantum execution: every number is pre-recorded.
- Metrics reflect the frozen release and are not recomputed by the browser.
- Circuit diagrams are schematics, not transpiled circuit drawings.
- Histograms are synthetic distributions for explanation, not measured counts.
- Not deployed publicly; deployment requires explicit approval.
- The demo is presentation-oriented; Spanish/localisation and mobile-first layouts are out of scope.
