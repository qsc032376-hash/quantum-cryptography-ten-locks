import { useEffect, useRef } from "react";
import { metricsFor, versionLabels, type TierData, type Version } from "../data/tiers";
import { CheckerPanel } from "./CheckerPanel";
import { CircuitDiagram } from "./CircuitDiagram";
import { ComplexityBars } from "./ComplexityBars";
import { Histogram } from "./Histogram";
import { Tier5Comparison } from "./Tier5Comparison";

interface TierDetailProps {
  tier: TierData;
  version: Version;
  onClose: () => void;
}

export function TierDetail({ tier, version, onClose }: TierDetailProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const metrics = metricsFor(tier, version);

  useEffect(() => {
    closeRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return (
    <div className="detail-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section
        className="detail"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`tier-${tier.id}-title`}
        aria-describedby={`tier-${tier.id}-problem`}
      >
        <header className="detail-header">
          <div>
            <p className="eyebrow">
              Tier {String(tier.id).padStart(2, "0")} · {tier.level} · {tier.points} pts
            </p>
            <span className="data-badge is-version" title={versionLabels[version].detail}>
              {version.toUpperCase()} · {version === "v1" ? "frozen baseline" : "candidate"}
            </span>
            <h2 id={`tier-${tier.id}-title`}>
              {tier.codename}
              <span className="detail-algorithm">{tier.algorithm}</span>
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close tier detail"
          >
            <span aria-hidden="true">×</span>
          </button>
        </header>

        <div className="detail-body">
          <section className="detail-section" aria-labelledby={`tier-${tier.id}-problem-title`}>
            <h3 id={`tier-${tier.id}-problem-title`}>Problem</h3>
            <p id={`tier-${tier.id}-problem`}>{tier.problem}</p>
            <p className="muted">{tier.lock}</p>
          </section>

          <section className="detail-section" aria-labelledby={`tier-${tier.id}-approach-title`}>
            <h3 id={`tier-${tier.id}-approach-title`}>Quantum approach</h3>
            <p>{tier.approach}</p>
            {tier.caveat ? <p className="callout">{tier.caveat}</p> : null}
          </section>

          <section className="detail-section" aria-labelledby={`tier-${tier.id}-circuit-title`}>
            <div className="section-heading">
              <h3 id={`tier-${tier.id}-circuit-title`}>Circuit</h3>
              <span className="data-badge is-illustrative">Illustrative schematic</span>
            </div>
            <CircuitDiagram circuit={tier.circuit} />
          </section>

          <section className="detail-section" aria-labelledby={`tier-${tier.id}-measurement-title`}>
            <div className="section-heading">
              <h3 id={`tier-${tier.id}-measurement-title`}>Measurement analysis</h3>
              <span className="data-badge is-illustrative">Illustrative distribution</span>
            </div>
            <p>{tier.measurement}</p>
            <Histogram bins={tier.histogram} label={`Illustrative outcome distribution for tier ${tier.id}`} />
          </section>

          <section className="detail-section" aria-labelledby={`tier-${tier.id}-post-title`}>
            <h3 id={`tier-${tier.id}-post-title`}>Classical post-processing</h3>
            <p>{tier.postprocessing}</p>
          </section>

          <section className="detail-section" aria-labelledby={`tier-${tier.id}-checker-title`}>
            <div className="section-heading">
              <h3 id={`tier-${tier.id}-checker-title`}>Official checker verification</h3>
              <span className="data-badge is-recorded">Recorded</span>
            </div>
            <CheckerPanel />
          </section>

          <section className="detail-section" aria-labelledby={`tier-${tier.id}-complexity-title`}>
            <div className="section-heading">
              <h3 id={`tier-${tier.id}-complexity-title`}>Circuit complexity</h3>
              <span className="data-badge is-recorded">Recorded</span>
            </div>
            <ComplexityBars metrics={metrics} />
          </section>

          {tier.id === 5 ? (
            <section className="detail-section" aria-labelledby={`tier-${tier.id}-compare-title`}>
              <div className="section-heading">
                <h3 id={`tier-${tier.id}-compare-title`}>Optimization preview</h3>
                <span className="data-badge is-candidate">Independent candidate</span>
              </div>
              <Tier5Comparison version={version} />
            </section>
          ) : null}
        </div>

        <footer className="detail-footer">
          <button type="button" className="button primary" onClick={onClose}>
            Back to all ten locks
          </button>
          <span className="muted">Press Esc to close</span>
        </footer>
      </section>
    </div>
  );
}
