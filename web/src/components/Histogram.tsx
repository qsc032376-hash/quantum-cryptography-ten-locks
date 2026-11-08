import type { HistogramBin } from "../data/tiers";

interface HistogramProps {
  bins: HistogramBin[];
  label: string;
}

/**
 * Illustrative outcome distribution. Values are synthetic teaching numbers,
 * never a recorded run, and the parent panel labels them accordingly.
 */
export function Histogram({ bins, label }: HistogramProps) {
  const max = Math.max(...bins.map((bin) => bin.value), 0.0001);

  return (
    <figure className="histogram">
      <div className="histogram-bars" role="img" aria-label={label}>
        {bins.map((bin, index) => (
          <div className="histogram-column" key={`${bin.label}-${index}`}>
            <div className="histogram-track">
              <div
                className={`histogram-bar${bin.highlight ? " is-highlight" : ""}`}
                style={{ height: `${Math.max((bin.value / max) * 100, 2)}%` }}
              >
                <span className="histogram-value">{(bin.value * 100).toFixed(1)}%</span>
              </div>
            </div>
            <span className="histogram-label">{bin.label}</span>
          </div>
        ))}
      </div>
      <figcaption className="histogram-caption">{label}</figcaption>
    </figure>
  );
}
