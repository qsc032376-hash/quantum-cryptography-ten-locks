import {
  aggregateFor,
  depthAggregateNote,
  metricsFor,
  tiers,
  versionLabels,
  type Version,
} from "../data/tiers";
import { VersionToggle } from "./VersionToggle";

interface DashboardProps {
  version: Version;
  onVersionChange: (version: Version) => void;
  onOpenTier: (id: number) => void;
  onPresent: () => void;
  onReplayIntro: () => void;
}

const numberFormat = new Intl.NumberFormat("en-US");

function LockGlyph({ locked }: { locked: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="lock-glyph">
      <rect x="4.5" y="10" width="15" height="10.5" rx="2.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path
        d={locked ? "M8 10V7.5a4 4 0 0 1 8 0V10" : "M8 10V7.5a4 4 0 0 1 7.6-1.7"}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="12" cy="15.2" r="1.35" fill="currentColor" />
    </svg>
  );
}

export function Dashboard({
  version,
  onVersionChange,
  onOpenTier,
  onPresent,
  onReplayIntro,
}: DashboardProps) {
  const totals = aggregateFor(version);
  const label = versionLabels[version];

  return (
    <main className="dashboard" id="main">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Qiskit Fall Fest · Ohio State · Quantum Cryptography</p>
          <h1>
            Ten locks.
            <br />
            One message.
          </h1>
          <p className="lede">
            Ten encrypted files, each opened by a different quantum algorithm. This demo walks
            through the algorithms, the circuits, the measurement logic and the classical
            post-processing behind all ten — with recorded checker results for each tier.
          </p>
          <div className="hero-actions">
            <button className="button primary" type="button" onClick={onPresent}>
              Enter presentation mode
            </button>
            <button className="button ghost" type="button" onClick={onReplayIntro}>
              Replay guided intro
            </button>
          </div>
        </div>
        <div className="hero-panel" aria-hidden="true">
          <div className="hero-ring" />
          <div className="hero-core">
            <span>10</span>
            <small>locks</small>
          </div>
          <div className="hero-orbit orbit-a" />
          <div className="hero-orbit orbit-b" />
        </div>
      </header>

      <section className="version-bar" aria-label="Data version">
        <div>
          <p className="eyebrow">Verification version</p>
          <p className="version-summary">
            <strong>{label.name}</strong>
            <span> · {label.detail}</span>
          </p>
        </div>
        <VersionToggle version={version} onChange={onVersionChange} />
      </section>

      <section className="stats" aria-label="Challenge summary">
        <article>
          <span className="stat-value">{tiers.length}</span>
          <span className="stat-label">locks</span>
        </article>
        <article>
          <span className="stat-value">10 / 10</span>
          <span className="stat-label">checker status full</span>
        </article>
        <article>
          <span className="stat-value">{numberFormat.format(totals.twoQubitGates)}</span>
          <span className="stat-label">two-qubit gates, summed</span>
        </article>
        <article>
          <span className="stat-value">{numberFormat.format(totals.depth)}</span>
          <span className="stat-label">depth, summed across 10 circuits</span>
        </article>
      </section>
      <p className="aggregate-note">{depthAggregateNote}</p>

      <section className="tier-section" aria-labelledby="tier-grid-title">
        <div className="section-head">
          <h2 id="tier-grid-title">The ten locks</h2>
          <p>Select a lock to open its algorithm, circuit, measurement and verification detail.</p>
        </div>

        <ul className="tier-grid">
          {tiers.map((tier) => {
            const metrics = metricsFor(tier, version);
            return (
              <li key={tier.id}>
                <button
                  type="button"
                  className={`tier-card${tier.featured ? " is-featured" : ""}`}
                  onClick={() => onOpenTier(tier.id)}
                  aria-label={`Open tier ${tier.id}: ${tier.codename}, ${tier.algorithm}`}
                >
                  <span className="tier-top">
                    <span className="tier-number">{String(tier.id).padStart(2, "0")}</span>
                    <LockGlyph locked={false} />
                  </span>
                  <span className="tier-name">{tier.codename}</span>
                  <span className="tier-algorithm">{tier.algorithm}</span>
                  <span className="tier-meta">
                    <span>{tier.level}</span>
                    <span>{tier.points} pts</span>
                    <span className="status-dot">full</span>
                  </span>
                  <span className="tier-metrics">
                    <span>
                      <strong>{numberFormat.format(metrics.twoQubitGates)}</strong> 2Q
                    </span>
                    <span>
                      depth <strong>{numberFormat.format(metrics.depth)}</strong>
                    </span>
                  </span>
                  {tier.featured ? <span className="featured-flag">Curated deep dive</span> : null}
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="provenance" id="provenance" aria-labelledby="provenance-title">
        <h2 id="provenance-title">What is recorded, what is illustrative</h2>
        <div className="provenance-grid">
          <article>
            <h3>Recorded</h3>
            <p>
              Circuit metrics and checker status come from the official checker run on{" "}
              <code>{label.detail}</code> inside a fresh copy of the repository. They are shown
              verbatim, one row per tier. The v2 candidate has not been submitted.
            </p>
          </article>
          <article>
            <h3>Illustrative</h3>
            <p>
              Circuit schematics and outcome histograms are hand-drawn teaching figures derived
              from the public algorithm descriptions. They are not screenshots of a run and are
              labelled as schematics in every panel.
            </p>
          </article>
          <article>
            <h3>Not included</h3>
            <p>
              No hidden keys, recovered secrets, decrypted messages, private oracle code,
              <code>locked.json</code> contents or credentials are bundled. The demo is a static
              front end and performs no quantum execution.
            </p>
          </article>
        </div>
      </section>

      <footer className="footer">
        <p>
          Public demo · static data · no backend. Metrics are labelled v1 or v2 and never mixed;
          the Tier 5 optimization is shown as a separate, independently accepted candidate.
        </p>
      </footer>
    </main>
  );
}
