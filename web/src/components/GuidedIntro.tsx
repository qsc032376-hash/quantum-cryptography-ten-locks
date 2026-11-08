import { useCallback, useEffect, useState } from "react";
import { introEstimatedSeconds, introScenes } from "../data/intro";
import { useReducedMotion } from "../hooks/useReducedMotion";

interface GuidedIntroProps {
  onEnter: () => void;
}

export function GuidedIntro({ onEnter }: GuidedIntroProps) {
  const [index, setIndex] = useState(0);
  const [replayKey, setReplayKey] = useState(0);
  const reducedMotion = useReducedMotion();
  const total = introScenes.length;
  const scene = introScenes[index];
  const isLast = index === total - 1;

  const next = useCallback(() => {
    if (index === total - 1) {
      onEnter();
    } else {
      setIndex((current) => current + 1);
    }
  }, [index, onEnter, total]);

  const back = useCallback(() => setIndex((current) => Math.max(current - 1, 0)), []);

  const replay = useCallback(() => {
    setIndex(0);
    setReplayKey((current) => current + 1);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight" || event.key === " " || event.key === "Enter") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowLeft" || event.key === "Backspace") {
        event.preventDefault();
        back();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [next, back]);

  return (
    <main
      className="intro"
      data-reduced-motion={reducedMotion ? "true" : "false"}
      aria-labelledby={`intro-title-${scene.id}`}
    >
      <header className="intro-bar">
        <span className="intro-brand">Ten Locks · guided intro</span>
        <div className="intro-bar-actions">
          <span className="intro-time">≈ {introEstimatedSeconds} s</span>
          <button type="button" className="button ghost small" onClick={replay}>
            Replay intro
          </button>
          <button type="button" className="button ghost small" onClick={onEnter}>
            Skip intro
          </button>
        </div>
      </header>

      <section className="intro-stage">
        <div
          className="intro-scene"
          key={`${scene.id}-${replayKey}`}
          aria-live="polite"
        >
          <p className="eyebrow">{scene.kicker}</p>
          <h1 id={`intro-title-${scene.id}`} className="intro-title">
            {scene.title}
          </h1>
          <p className="intro-body">{scene.body}</p>

          {scene.id === "locks" ? (
            <ul className="intro-lock-list">
              {scene.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          ) : (
            <ul className="intro-points">
              {scene.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          )}

          {scene.note ? <p className="intro-note">{scene.note}</p> : null}
        </div>
      </section>

      <footer className="intro-controls">
        <div className="intro-progress">
          <div
            className="intro-progress-track"
            role="progressbar"
            aria-label="Intro progress"
            aria-valuemin={1}
            aria-valuemax={total}
            aria-valuenow={index + 1}
            aria-valuetext={`Scene ${index + 1} of ${total}`}
          >
            <div
              className="intro-progress-fill"
              style={{ width: `${((index + 1) / total) * 100}%` }}
            />
          </div>
          <span className="intro-progress-label">
            Scene {index + 1} of {total}
          </span>
        </div>

        <div className="intro-buttons">
          <button type="button" className="button ghost" onClick={back} disabled={index === 0}>
            ← Back
          </button>
          <button type="button" className="button primary" onClick={next}>
            {isLast ? scene.cta ?? "Enter the dashboard" : "Next →"}
          </button>
        </div>
      </footer>
    </main>
  );
}
