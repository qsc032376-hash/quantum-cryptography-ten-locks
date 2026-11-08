# Ten Locks — guided quantum demo (web)

Static, front-end-only walkthrough of the ten-lock quantum cryptography challenge.

- **Guided intro** (4 scenes, ≈55 s): the mystery, superposition/interference/measurement,
  the ten algorithms, and a hand-off into the dashboard.
- **Dashboard** with one lock card per tier (algorithm, level, points, metrics for the
  selected version).
- **Detail view** for every tier: problem, quantum approach, circuit schematic, measurement
  analysis, classical post-processing, official checker verification, complexity metrics.
- **Deep dives** for Tier 1 (Bernstein–Vazirani), Tier 5 (Grover) and Tier 10 (Shor DLP).
- **Tier 5 before/after panel**: frozen baseline vs. independently accepted candidate.
- **Presentation mode** (5 slides) for judges: keyboard navigation, projector typography,
  a dedicated Tier 5 moment, and a final team/results slide with honest simulation caveats.
- **v1/v2 version switch** with aggregates recomputed from per-tier records.
- **Deep links**: `#intro`, `#dashboard`, `#tier-3`, `#present`.

No backend, no external fonts, no network calls: after the bundle loads the whole flow works
offline.

## Requirements

- Node.js 20+ (tested with the bundled Node 24 runtime)
- pnpm 10+ (or npm)

## Install and run

```bash
cd web
pnpm install
pnpm dev          # http://localhost:5173
```

If `pnpm` blocks `esbuild`'s postinstall under its supply-chain policy:

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

## Guided intro

| Scene | Content |
|---|---|
| 1 · The mystery | One message, ten quantum locks; the ten decrypted lines form the message. |
| 2 · The quantum principle | Superposition, interference, measurement — explicitly *not* parallel evaluation of every key. |
| 3 · Ten different locks | One line per tier, from parity queries to the discrete logarithm. |
| 4 · Enter the lab | Version explanation and the dashboard hand-off. |

Controls: **Next**, **Back**, **Skip intro**, **Replay intro**, visible progress bar with
“Scene n of 4”, and keyboard support (`→`/`Space`/`Enter` next, `←` next back, `Esc` to the
dashboard). Scene and progress animations are disabled when `prefers-reduced-motion` is set.

**Storyboard dependency.** `docs/WEB_DEMO_STORYBOARD.md` (Sicheng's branch) was not present on
any fetched branch during this sprint, so the scene copy lives in `src/data/intro.ts` as
editable placeholder text and can be swapped without touching components.

## Versions and metrics

All numbers are **recorded** checker output, never recomputed in the browser.

| Metric | v1 — frozen baseline | v2 — verified candidate |
|---|---:|---:|
| Sum of two-qubit gates | 307,349 | 301,349 |
| Sum of per-tier depth | 787,876 | 784,324 |
| Tier 5 two-qubit gates | 21,150 | 15,150 |
| Tier 5 depth | 33,055 | 29,503 |

v1 is `release/ten-locks-v1`; v2 is `integration/optimized-v2-candidate` (Tier 5 oracle +
Tier 10 classical module only). **v2 has not been submitted** and the frozen v1 release remains
the baseline. The depth total is an aggregate of ten separate circuits, not the depth of one
physical circuit; the dashboard states this explicitly.

Unchanged tiers inherit the v1 record. One footnote: the external v2 report lists Tier 7 total
gates as 760 while the local v1 checker run recorded 763 for the same untouched circuit; the
two-qubit-gate and depth totals used here agree.

## Data provenance and security

**Recorded**: circuit metrics and checker status from
`python tools/check_submission.py submissions/<team>` on the frozen release / v2 candidate,
shown verbatim per tier.

**Illustrative**: circuit schematics and outcome histograms are hand-drawn teaching figures
derived from the public algorithm descriptions. They are not screenshots of a run and are
labelled as schematics everywhere.

**Not bundled**: no hidden keys, recovered secrets, decrypted messages, private oracle code,
`locked.json` contents, credentials or infrastructure configuration. The demo performs no
quantum execution.

## Presentation mode

Five slides: opening, Bernstein–Vazirani, Grover (with the Tier 5 before/after), Shor discrete
logarithm, and a final slide with team roles, results, the Aer-execution explanation and the
simulator-vs-hardware caveat. `←`/`→`/`Home`/`End` navigate; `Esc` returns to the dashboard; the
progress dots jump directly.

## Tests

```
Test Files  7 passed (7)
Tests       30 passed (30)
```

- `intro.test.tsx` — four scenes, Next/Back/Skip/Replay, keyboard, reduced motion,
  no-parallelism claim.
- `dashboard.test.tsx` — ten cards, open/close, `Esc`.
- `detail.test.tsx` — required sections, labels, focus handling, recorded metrics.
- `tier5.test.tsx` — both runs, 28.4% / 10.7%, “candidate · not merged”.
- `version.test.tsx` — aggregate recomputation, v1/v2 totals, version carried into detail and
  presentation.
- `presentation.test.tsx` — buttons, keyboard, dots, pre-recorded note.
- `accessibility.test.tsx` — names, labelled dialog/images, single `h1`, narrow viewport.

## Build

`pnpm build` emits `dist/` (`base: "./"`) — about 183 kB JS / 57 kB gzip.

## Limitations

- No live quantum execution; every number is pre-recorded.
- Histograms are synthetic distributions, not measured counts.
- Circuit diagrams are schematics, not transpiled drawings.
- v2 is a candidate; it is not submitted and has no separate public acceptance report beyond
  the integration document.
- Not deployed publicly; deployment requires explicit approval.
