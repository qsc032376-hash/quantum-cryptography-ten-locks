/**
 * Tier 5 circuit optimization: baseline vs. an independently accepted candidate.
 *
 * Numbers are recorded from the official checker run on the frozen release
 * (baseline) and from the optimization branch's own full checker run
 * (candidate). The candidate is NOT part of `release/ten-locks-v1`; the demo
 * must always say so.
 */

export interface ComparisonMetric {
  label: string;
  unit: string;
  baseline: number;
  candidate: number;
}

export const tier5Baseline = {
  twoQubitGates: 21150,
  depth: 33055,
  label: "Frozen release (release/ten-locks-v1)",
} as const;

export const tier5Candidate = {
  twoQubitGates: 15150,
  depth: 29503,
  label: "Optimized candidate (accepted independently)",
} as const;

function improvement(baseline: number, candidate: number): number {
  return ((baseline - candidate) / baseline) * 100;
}

export const tier5Comparison: ComparisonMetric[] = [
  {
    label: "Two-qubit gates",
    unit: "gates",
    baseline: tier5Baseline.twoQubitGates,
    candidate: tier5Candidate.twoQubitGates,
  },
  {
    label: "Circuit depth",
    unit: "layers",
    baseline: tier5Baseline.depth,
    candidate: tier5Candidate.depth,
  },
];

export const tier5Improvements = {
  twoQubitGates: improvement(
    tier5Baseline.twoQubitGates,
    tier5Candidate.twoQubitGates,
  ),
  depth: improvement(tier5Baseline.depth, tier5Candidate.depth),
};

/** Rounded, display-ready percentages (one decimal place). */
export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export const tier5Notes = {
  technique:
    "Public S-box and permutation constant folding: the toy cipher's S-box and bit permutation are fixed, public tables. The optimized circuit folds them into the oracle's wiring and precomputes fixed sub-circuits, removing duplicate gates rather than approximating the cipher.",
  acceptance:
    "The candidate passed the official checker in full mode with a matching hash and unchanged circuit semantics. It is an independent acceptance result, not a replacement of the frozen release.",
};
