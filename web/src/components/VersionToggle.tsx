import type { Version } from "../data/tiers";
import { versionLabels } from "../data/tiers";

interface VersionToggleProps {
  version: Version;
  onChange: (version: Version) => void;
  /** Compact form for the presentation bar. */
  compact?: boolean;
}

export function VersionToggle({ version, onChange, compact = false }: VersionToggleProps) {
  return (
    <div
      className={`version-toggle${compact ? " is-compact" : ""}`}
      role="radiogroup"
      aria-label="Verification version"
    >
      {(["v1", "v2"] as const).map((value) => {
        const label = versionLabels[value];
        const checked = value === version;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={checked}
            className={`version-option${checked ? " is-active" : ""}`}
            onClick={() => onChange(value)}
            title={label.detail}
          >
            <span className="version-name">{value.toUpperCase()}</span>
            {compact ? null : <span className="version-tagline">{label.name.split("— ")[1]}</span>}
          </button>
        );
      })}
      <span className="version-current">
        {versionLabels[version].detail}
        {version === "v2" ? " · not submitted" : ""}
      </span>
    </div>
  );
}
