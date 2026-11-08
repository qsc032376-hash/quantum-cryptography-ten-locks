import {
  formatPercent,
  tier5Baseline,
  tier5Candidate,
  tier5Comparison,
  tier5Improvements,
  tier5Notes,
  type ComparisonMetric,
} from "../data/tier5";
import type { Version } from "../data/tiers";

interface Tier5ComparisonProps {
  compact?: boolean;
  version?: Version;
}

const numberFormat = new Intl.NumberFormat("en-US");

function MetricPair({ metric }: { metric: ComparisonMetric }) {
  const max = Math.max(metric.baseline, metric.candidate);
  const improvement = ((metric.baseline - metric.candidate) / metric.baseline) * 100;

  return (
    <div className="compare-metric">
      <div className="compare-head">
        <h4>{metric.label}</h4>
        <span className="delta-chip">−{formatPercent(improvement)}</span>
      </div>

      <div className="compare-row">
        <span className="compare-tag">Baseline</span>
        <div className="compare-track">
          <div
            className="compare-bar baseline"
            style={{ width: `${(metric.baseline / max) * 100}%` }}
          >
            <span>{numberFormat.format(metric.baseline)}</span>
          </div>
        </div>
      </div>

      <div className="compare-row">
        <span className="compare-tag candidate">Candidate</span>
        <div className="compare-track">
          <div
            className="compare-bar candidate"
            style={{ width: `${(metric.candidate / max) * 100}%` }}
          >
            <span>{numberFormat.format(metric.candidate)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Tier5Comparison({ compact = false, version = "v1" }: Tier5ComparisonProps) {
  const context =
    version === "v2"
      ? "You are viewing v2, which includes this optimization. The candidate is still not an official submission."
      : "You are viewing the frozen v1 baseline. The candidate is shown for context and is not part of v1.";
  return (
    <section className={`tier5-compare${compact ? " is-compact" : ""}`} aria-labelledby="tier5-compare-title">
      <header className="compare-top">
        <div>
          <p className="eyebrow">Independent optimization result</p>
          <h3 id="tier5-compare-title">Tier 5 — before / after</h3>
        </div>
        <span className="status-pill is-candidate">Candidate · not merged</span>
      </header>

      <p className="compare-summary">
        Two-qubit gates drop by <strong>{formatPercent(tier5Improvements.twoQubitGates)}</strong>{" "}
        and depth by <strong>{formatPercent(tier5Improvements.depth)}</strong> against the frozen
        release. The candidate has passed the official checker on its own branch.
      </p>
      <p className="compare-context">{context}</p>

      <div className="compare-grid">
        {tier5Comparison.map((metric) => (
          <MetricPair key={metric.label} metric={metric} />
        ))}
      </div>

      <dl className="compare-facts">
        <div>
          <dt>Baseline</dt>
          <dd>
            {numberFormat.format(tier5Baseline.twoQubitGates)} 2Q · depth{" "}
            {numberFormat.format(tier5Baseline.depth)} <span>({tier5Baseline.label})</span>
          </dd>
        </div>
        <div>
          <dt>Candidate</dt>
          <dd>
            {numberFormat.format(tier5Candidate.twoQubitGates)} 2Q · depth{" "}
            {numberFormat.format(tier5Candidate.depth)} <span>({tier5Candidate.label})</span>
          </dd>
        </div>
      </dl>

      <div className="compare-notes">
        <h4>How the gates were removed</h4>
        <p>{tier5Notes.technique}</p>
        <h4>Acceptance status</h4>
        <p>{tier5Notes.acceptance}</p>
      </div>

      <p className="compare-disclaimer">
        The frozen release remains the baseline submission. This panel does not claim that the
        optimized circuit has replaced it.
      </p>
    </section>
  );
}
