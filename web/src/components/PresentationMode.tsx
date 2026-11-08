import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  aggregateFor,
  metricsFor,
  tierMap,
  tiers,
  versionLabels,
  type Version,
} from "../data/tiers";
import { formatPercent, tier5Improvements } from "../data/tier5";
import { CircuitDiagram } from "./CircuitDiagram";
import { Tier5Comparison } from "./Tier5Comparison";
import { VersionToggle } from "./VersionToggle";

interface PresentationModeProps {
  version: Version;
  onVersionChange: (version: Version) => void;
  onExit: () => void;
}

const numberFormat = new Intl.NumberFormat("en-US");

const teamRoles = [
  { role: "Quantum circuits", name: "Junqi" },
  { role: "Classical post-processing & web demo", name: "Youyang Shang" },
  { role: "Validation & independent testing", name: "Junrui Yu" },
  { role: "Mathematical modelling", name: "Sicheng" },
];

type SlideKind = "intro" | "tier" | "summary";

interface Slide {
  kind: SlideKind;
  tierId?: number;
  title: string;
}

const slides: Slide[] = [
  { kind: "intro", title: "Ten locks, one message" },
  { kind: "tier", tierId: 1, title: "Bernstein–Vazirani" },
  { kind: "tier", tierId: 5, title: "Grover search" },
  { kind: "tier", tierId: 10, title: "Shor discrete logarithm" },
  { kind: "summary", title: "Team & results" },
];

function SlideFrame({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <article className="slide">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="slide-title">{title}</h2>
      <div className="slide-content">{children}</div>
    </article>
  );
}

export function PresentationMode({ version, onVersionChange, onExit }: PresentationModeProps) {
  const [index, setIndex] = useState(0);
  const total = slides.length;

  const go = useCallback(
    (delta: number) => setIndex((current) => Math.min(Math.max(current + delta, 0), total - 1)),
    [total],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight" || event.key === " " || event.key === "PageDown") {
        event.preventDefault();
        go(1);
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        go(-1);
      } else if (event.key === "Home") {
        event.preventDefault();
        setIndex(0);
      } else if (event.key === "End") {
        event.preventDefault();
        setIndex(total - 1);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [go, total]);

  const slide = slides[index];

  const content = useMemo(() => {
    const totals = aggregateFor(version);
    const label = versionLabels[version];

    if (slide.kind === "intro") {
      return (
        <SlideFrame eyebrow="Judges briefing · public demo" title="Ten locks, one message">
          <div className="slide-grid two">
            <p className="slide-lede">
              Ten encrypted files, ten quantum algorithms, one message. This walkthrough covers
              three showcase tiers in depth and names the algorithm behind every other lock.
            </p>
            <ul className="slide-facts">
              <li>
                <strong>10 / 10</strong> tiers returned <em>full</em> from the official checker.
              </li>
              <li>
                <strong>{numberFormat.format(totals.twoQubitGates)}</strong> two-qubit gates,{" "}
                <strong>{numberFormat.format(totals.depth)}</strong> total depth across ten
                separate circuits.
              </li>
              <li>
                Version <strong>{version.toUpperCase()}</strong>: {label.name}.
              </li>
            </ul>
          </div>
          <p className="slide-note">
            Every number is pre-recorded — nothing runs live in this demo. Use ← / → or the
            buttons below; Esc returns to the dashboard.
          </p>
        </SlideFrame>
      );
    }

    if (slide.kind === "summary") {
      return (
        <SlideFrame eyebrow="Wrap-up" title="Team & results">
          <div className="slide-grid two">
            <div>
              <ul className="slide-facts">
                <li>
                  <strong>10 / 10</strong> tiers verified in full mode with matching SHA-256.
                </li>
                <li>
                  Version <strong>{version.toUpperCase()}</strong>:{" "}
                  {numberFormat.format(totals.twoQubitGates)} two-qubit gates ·{" "}
                  {numberFormat.format(totals.depth)} aggregate depth.
                </li>
                <li>
                  Tier 5 candidate: {formatPercent(tier5Improvements.twoQubitGates)} fewer
                  two-qubit gates, independently accepted.
                </li>
              </ul>
              <div className="role-list">
                <h3>Team</h3>
                <ul>
                  {teamRoles.map((member) => (
                    <li key={member.name}>
                      <span>{member.role}</span>
                      <strong>{member.name}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div>
              <div className="summary-table">
                {tiers.map((tier) => (
                  <div key={tier.id} className="summary-row">
                    <span>{String(tier.id).padStart(2, "0")}</span>
                    <span>{tier.codename}</span>
                    <span>{tier.algorithm}</span>
                    <span className="status-dot">full</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="caveat-box">
            <p>
              <strong>How the results were produced.</strong> Each <code>solve()</code> runs its
              circuit on the Aer state-vector simulator; the official checker re-executes{" "}
              <code>solve()</code> in a fresh copy of the repository and records the scored
              circuit. Aer is a simulator, not physical quantum hardware, so these results say
              nothing about device noise or runtime on a real QPU.
            </p>
            <p>
              The v2 figure is a verified candidate; it has not been submitted, and the frozen v1
              release remains the baseline.
            </p>
          </div>
        </SlideFrame>
      );
    }

    const tierId = slide.tierId ?? 1;
    const tier = tierMap.get(tierId);
    if (!tier) {
      return null;
    }
    const metrics = metricsFor(tier, version);

    return (
      <SlideFrame
        eyebrow={`Tier ${String(tier.id).padStart(2, "0")} · ${tier.level} · ${version.toUpperCase()}`}
        title={tier.algorithm}
      >
        <div className="slide-grid two">
          <div>
            <p className="slide-lede">{tier.problem}</p>
            <ul className="slide-facts">
              <li>
                <strong>{numberFormat.format(metrics.twoQubitGates)}</strong> two-qubit gates ·
                depth <strong>{numberFormat.format(metrics.depth)}</strong>
              </li>
              <li>{tier.approach}</li>
              <li>{tier.postprocessing}</li>
            </ul>
          </div>
          <div className="slide-visual">
            <CircuitDiagram circuit={tier.circuit} />
          </div>
        </div>

        {tier.id === 5 ? (
          <div className="slide-compare">
            <Tier5Comparison compact version={version} />
          </div>
        ) : null}

        {tier.id === 10 ? (
          <p className="slide-note">
            Readout rule: two 6-bit registers at 64 QFT points for a 41-element group — raw
            values are rounded to the nearest frequency before any congruence is formed.
          </p>
        ) : null}
      </SlideFrame>
    );
  }, [slide, version]);

  return (
    <div className="presentation" role="region" aria-label="Presentation mode">
      <header className="presentation-bar">
        <button type="button" className="button ghost" onClick={onExit}>
          Exit to dashboard
        </button>
        <ol className="slide-dots" aria-label="Presentation progress">
          {slides.map((item, itemIndex) => (
            <li key={item.title}>
              <button
                type="button"
                className={`slide-dot${itemIndex === index ? " is-active" : ""}`}
                aria-label={`Go to slide ${itemIndex + 1}: ${item.title}`}
                aria-current={itemIndex === index ? "step" : undefined}
                onClick={() => setIndex(itemIndex)}
              />
            </li>
          ))}
        </ol>
        <div className="presentation-actions">
          <VersionToggle version={version} onChange={onVersionChange} compact />
          <span className="slide-counter">
            {index + 1} / {total}
          </span>
        </div>
      </header>

      <main className="presentation-stage" aria-live="polite">
        {content}
      </main>

      <footer className="presentation-controls">
        <button
          type="button"
          className="button ghost"
          onClick={() => go(-1)}
          disabled={index === 0}
        >
          ← Previous
        </button>
        <button
          type="button"
          className="button ghost"
          onClick={() => go(1)}
          disabled={index === total - 1}
        >
          Next →
        </button>
      </footer>
    </div>
  );
}

export const presentationSlideCount = slides.length;
