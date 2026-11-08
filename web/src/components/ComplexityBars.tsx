import { tiers, type TierMetrics } from "../data/tiers";

interface ComplexityProps {
  metrics: TierMetrics;
}

const numberFormat = new Intl.NumberFormat("en-US");

export function ComplexityBars({ metrics }: ComplexityProps) {
  const maxTwoQubit = Math.max(...tiers.map((tier) => tier.metrics.twoQubitGates), 1);
  const maxDepth = Math.max(...tiers.map((tier) => tier.metrics.depth), 1);
  const maxGates = Math.max(...tiers.map((tier) => tier.metrics.totalGates), 1);
  const maxQubits = Math.max(...tiers.map((tier) => tier.metrics.activeQubits), 1);

  const rows = [
    {
      label: "Two-qubit gates",
      value: metrics.twoQubitGates,
      max: maxTwoQubit,
      hint: "scored first: 40% of simplicity weight",
    },
    {
      label: "Depth",
      value: metrics.depth,
      max: maxDepth,
      hint: "30% of simplicity weight",
    },
    {
      label: "Total gates",
      value: metrics.totalGates,
      max: maxGates,
      hint: "20% of simplicity weight",
    },
    {
      label: "Active qubits",
      value: metrics.activeQubits,
      max: maxQubits,
      hint: "10% of simplicity weight",
    },
  ];

  return (
    <div className="complexity">
      <p className="metric-source">
        Recorded transpiled metrics for the scored circuit (<code>rz/sx/x/cx</code>,
        optimization level 1, seed 12345).
      </p>
      <ul className="complexity-list" aria-label="Circuit complexity metrics">
        {rows.map((row) => (
          <li key={row.label} className="complexity-row">
            <div className="complexity-head">
              <span className="complexity-label">{row.label}</span>
              <span className="complexity-value">{numberFormat.format(row.value)}</span>
            </div>
            <div
              className="complexity-track"
              role="img"
              aria-label={`${row.label}: ${numberFormat.format(row.value)}`}
            >
              <div
                className="complexity-bar"
                style={{ width: `${Math.max((row.value / row.max) * 100, 1)}%` }}
              />
            </div>
            <span className="complexity-hint">{row.hint}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
