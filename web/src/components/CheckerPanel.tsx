import { checkerVerification } from "../data/tiers";

/**
 * Recorded checker output. These four chips mirror the columns of
 * `tools/check_submission.py`'s report for the frozen release.
 */
export function CheckerPanel() {
  const items = [
    { key: "status", label: "Status", value: checkerVerification.status },
    { key: "hash", label: "Hash", value: checkerVerification.hash },
    { key: "circuit", label: "Circuit run", value: checkerVerification.circuitRun ? "yes" : "no" },
    { key: "metrics", label: "Metrics", value: checkerVerification.metricsStatus },
  ];

  return (
    <div className="checker">
      <ul className="checker-grid" aria-label="Official checker verification">
        {items.map((item) => (
          <li key={item.key} className="checker-chip">
            <span className="checker-key">{item.label}</span>
            <strong className={`checker-value is-${item.value}`}>{item.value}</strong>
          </li>
        ))}
      </ul>
      <p className="checker-note">
        Recorded with <code>python tools/check_submission.py submissions/&lt;team&gt;</code> on
        the frozen release. The checker is run inside a fresh copy of the repository and
        re-executes <code>solve()</code>; these values are not hand-entered.
      </p>
    </div>
  );
}
