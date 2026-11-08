/**
 * Public-facing tier data.
 *
 * Provenance rules (see web/README.md):
 * - `metrics` and `checker` are RECORDED output of `tools/check_submission.py`
 *   on `release/ten-locks-v1` (frozen release). No key, plaintext or ciphertext
 *   is stored here.
 * - `circuit` and `histogram` are ILLUSTRATIVE schematics built from the public
 *   algorithm descriptions. They are not screenshots of a run and must always be
 *   labelled as such in the UI.
 */

export type GateKind = "gate" | "control" | "measure" | "step";

export interface GateSpec {
  /** Horizontal column, 0-based. */
  col: number;
  /** Top wire, 0-based. */
  wire: number;
  label: string;
  kind: GateKind;
  /** For `control`, the target wire. For `step`, how many wires to span. */
  target?: number;
  span?: number;
}

export interface CircuitSpec {
  shownWires: string[];
  totalWires: number;
  gates: GateSpec[];
  caption: string;
}

export interface HistogramBin {
  label: string;
  value: number;
  highlight?: boolean;
}

export interface TierMetrics {
  twoQubitGates: number;
  depth: number;
  totalGates: number;
  activeQubits: number;
}

export interface TierData {
  id: number;
  codename: string;
  algorithm: string;
  level: string;
  points: number;
  lock: string;
  problem: string;
  approach: string;
  measurement: string;
  postprocessing: string;
  caveat?: string;
  metrics: TierMetrics;
  /** Verified v2 candidate metrics, only where they differ from v1. */
  metricsV2?: TierMetrics;
  circuit: CircuitSpec;
  histogram: HistogramBin[];
  /** Long-form sections are only written for the three priority tiers. */
  featured: boolean;
}

const checker = {
  status: "full",
  hash: "match",
  circuitRun: true,
  metricsStatus: "ok",
} as const;

export const checkerVerification = checker;

export const tiers: TierData[] = [
  {
    id: 1,
    codename: "The Parity Vault",
    algorithm: "Bernstein–Vazirani",
    level: "Warm-up",
    points: 1,
    lock: "Repeating XOR with a hidden 24-bit string, three key bytes repeated over the line.",
    problem:
      "A vault answers one parity question about a hidden 24-bit string s. Classically that is 24 queries; quantumly a single oracle call is enough.",
    approach:
      "Prepare the target in |−〉, query the oracle once, then interfere the input register. The phase (−1)^(s·x) becomes a visible bit pattern after a second layer of Hadamards.",
    measurement:
      "Every noiseless shot collapses onto the same 24-bit pattern; the histogram is a single spike. Real hardware spreads the spike, so the majority outcome is taken.",
    postprocessing:
      "Read the measured bits as the integer s (qubit j has weight 2^j), convert to three big-endian bytes, then XOR the repeated key stream over the ciphertext.",
    metrics: { twoQubitGates: 151, depth: 44, totalGates: 298, activeQubits: 25 },
    circuit: {
      shownWires: ["q0", "q1", "q2", "q3", "q4", "… 20 more", "target"],
      totalWires: 25,
      gates: [
        ...Array.from({ length: 6 }, (_, wire) => ({ col: 0, wire, label: "H", kind: "gate" as const })),
        { col: 1, wire: 0, label: "Oracle  f(x) = s·x mod 2", kind: "step", span: 7 },
        ...Array.from({ length: 6 }, (_, wire) => ({ col: 2, wire, label: "H", kind: "gate" as const })),
        ...Array.from({ length: 6 }, (_, wire) => ({ col: 3, wire, label: "", kind: "measure" as const })),
      ],
      caption:
        "One oracle call. The target starts in |−〉 so the phase kickback lands on the input register.",
    },
    histogram: [
      { label: "measured pattern", value: 1, highlight: true },
      { label: "other outcomes", value: 0.02 },
    ],
    featured: true,
  },
  {
    id: 2,
    codename: "Two Links",
    algorithm: "Quantum key distribution (BB84-style)",
    level: "Easy",
    points: 2,
    lock: "A key rebuilt from qubits sent over a simulated link, one of which is tapped.",
    problem:
      "Two links carry qubits. One is noisy because it is eavesdropped; the public check bits reveal which one, and the clean link supplies the key.",
    approach:
      "Measure each incoming qubit in the basis announced by the sender, compare the public check positions, discard the tapped link, then solve the public reconciliation equations.",
    measurement:
      "Per-link error rates: the clean link sits near the expected baseline, the tapped link is far above it. The histogram shows the sifted error fraction for both.",
    postprocessing:
      "Exclude the check positions, run the binary reconciliation solver, and use the resulting shared bytes as the repeating XOR key.",
    metrics: { twoQubitGates: 0, depth: 3, totalGates: 3, activeQubits: 1 },
    circuit: {
      shownWires: ["link A", "link B"],
      totalWires: 2,
      gates: [
        { col: 0, wire: 0, label: "receive + measure", kind: "step", span: 1 },
        { col: 1, wire: 0, label: "sift by basis", kind: "step", span: 1 },
        { col: 0, wire: 1, label: "receive + measure", kind: "step", span: 1 },
        { col: 1, wire: 1, label: "reject (tapped)", kind: "step", span: 1 },
      ],
      caption:
        "No entangling gates: the work is basis choice and public reconciliation, not circuit depth.",
    },
    histogram: [
      { label: "clean link error", value: 0.03 },
      { label: "tapped link error", value: 0.27, highlight: true },
    ],
    featured: false,
  },
  {
    id: 3,
    codename: "Twenty-Four Seals",
    algorithm: "Deutsch–Jozsa (24 oracles)",
    level: "Easy",
    points: 2,
    lock: "SHA-256 keystream XOR with a 24-bit key, one bit per sealed oracle.",
    problem:
      "Twenty-four oracles are each promised constant or balanced. One query per oracle is enough to classify it; oracle i gives key bit i.",
    approach:
      "Put the input register in a uniform superposition, query the oracle once with the target in |−〉, then Hadamard back. Constant oracles return |0…0〉 with certainty, balanced ones never do.",
    measurement:
      "Twenty-four independent single-shot classifications. The recorded circuit applies each oracle exactly once; the run is checked for oracle-call count.",
    postprocessing:
      "Assemble the 24 flags in oracle order into a bit string, run the SHA-256 keystream, XOR the ciphertext, and check the published hash.",
    metrics: { twoQubitGates: 7808, depth: 8771, totalGates: 19497, activeQubits: 7 },
    circuit: {
      shownWires: ["q0", "q1", "q2", "q3", "q4", "q5", "target"],
      totalWires: 7,
      gates: [
        ...Array.from({ length: 6 }, (_, wire) => ({ col: 0, wire, label: "H", kind: "gate" as const })),
        { col: 1, wire: 0, label: "Oracle i (one application)", kind: "step", span: 7 },
        ...Array.from({ length: 6 }, (_, wire) => ({ col: 2, wire, label: "H", kind: "gate" as const })),
        { col: 3, wire: 0, label: "M", kind: "measure" },
      ],
      caption:
        "Repeated 24 times, one oracle per key bit. Measured all-zero means constant.",
    },
    histogram: [
      { label: "constant → 000000", value: 1, highlight: true },
      { label: "balanced outcomes", value: 0.02 },
    ],
    featured: false,
  },
  {
    id: 4,
    codename: "The Echo",
    algorithm: "Simon's algorithm",
    level: "Medium",
    points: 3,
    lock: "SHA-256 keystream XOR with a 10-bit hidden period.",
    problem:
      "A 2-to-1 function on 10 bits repeats under XOR with a hidden nonzero string s. Classically this costs about 2^(n/2) queries.",
    approach:
      "Query the function on a uniform superposition, measure the output, then Hadamard the input register. Each run yields one GF(2) equation orthogonal to s; about n runs pin s down.",
    measurement:
      "Input-register readouts are uniform over the orthogonal complement. The histogram is flat over the support — the signal is in the linear equations, not in a single peak.",
    postprocessing:
      "Collect independent equations, solve the GF(2) system for the unique nonzero solution, build the 10-bit key string, decrypt and verify.",
    metrics: { twoQubitGates: 183, depth: 195, totalGates: 455, activeQubits: 20 },
    circuit: {
      shownWires: ["q0…q9 (input)", "a0…a9 (output)"],
      totalWires: 20,
      gates: [
        { col: 0, wire: 0, label: "H⊗10", kind: "step", span: 1 },
        { col: 1, wire: 0, label: "Oracle f (2-to-1)", kind: "step", span: 2 },
        { col: 2, wire: 0, label: "H⊗10", kind: "step", span: 1 },
        { col: 3, wire: 0, label: "measure input", kind: "measure" },
      ],
      caption:
        "The output register starts in |0…0〉; each shot contributes one orthogonal vector.",
    },
    histogram: [
      { label: "orthogonal x", value: 0.5 },
      { label: "other x", value: 0.02 },
      { label: "orthogonal x′", value: 0.48 },
    ],
    featured: false,
  },
  {
    id: 5,
    codename: "The Small Safe",
    algorithm: "Grover search",
    level: "Medium",
    points: 4,
    lock: "Toy byte cipher with a 10-bit key; the first two plaintext bytes are known.",
    problem:
      "A reversible byte cipher guards the line. Only 1024 keys exist, but the challenge scores the circuit, so the key must be found by amplitude amplification, not by trying keys.",
    approach:
      "Build a reversible oracle that marks keys decrypting the known two bytes correctly, then alternate it with a reflection about the uniform superposition. The number of iterations is about (π/4)√N.",
    measurement:
      "After the right number of iterations the correct key dominates: one tall bar with the remaining probability spread thinly across the other 1023 keys.",
    postprocessing:
      "Decrypt with the measured key, check the known prefix, run the SHA-256 keystream, and verify the published hash.",
    caveat:
      "The oracle must be a real reversible circuit; measuring random keys and checking them classically is explicitly disallowed.",
    metrics: { twoQubitGates: 21150, depth: 33055, totalGates: 58620, activeQubits: 19 },
    metricsV2: { twoQubitGates: 15150, depth: 29503, totalGates: 42211, activeQubits: 19 },
    circuit: {
      shownWires: ["k0", "k1", "k2", "… 7 key qubits", "data (8+)"],
      totalWires: 19,
      gates: [
        { col: 0, wire: 0, label: "H⊗10", kind: "step", span: 4 },
        { col: 1, wire: 0, label: "Oracle: decrypt 2 bytes ", kind: "step", span: 4 },
        { col: 2, wire: 0, label: "Diffusion", kind: "step", span: 4 },
        { col: 3, wire: 0, label: "repeat (π/4)√N", kind: "step", span: 4 },
        { col: 4, wire: 0, label: "M", kind: "measure" },
      ],
      caption:
        "Each round is a marked-key oracle plus a reflection. The S-box and permutation are applied to 8 data wires per byte.",
    },
    histogram: [
      { label: "candidate key", value: 0.62, highlight: true },
      { label: "other 1023 keys", value: 0.38 / 6 },
      { label: "…", value: 0.38 / 6 },
      { label: "…", value: 0.38 / 6 },
      { label: "…", value: 0.38 / 6 },
      { label: "…", value: 0.38 / 6 },
    ],
    featured: true,
  },
  {
    id: 6,
    codename: "The Bigger Safe",
    algorithm: "Grover search with a classical checksum filter",
    level: "Medium–hard",
    points: 4,
    lock: "Same toy cipher, 14-bit key; about 64 keys pass the single known byte.",
    problem:
      "With 14 key bits and only the first byte known, roughly 64 keys survive the oracle. The search has many valid answers, so the reflection schedule changes.",
    approach:
      "Reuse the tier-5 oracle widened to 14 key qubits. With M marked keys among N, the optimal number of iterations shrinks to about (π/4)√(N/M).",
    measurement:
      "A broad plateau of marked keys rather than one spike. Every measured candidate must be decrypted and filtered by the public checksum.",
    postprocessing:
      "Decrypt each measured candidate, keep the one whose plaintext bytes sum to the published checksum mod 256, then verify the hash.",
    metrics: { twoQubitGates: 3000, depth: 5883, totalGates: 9534, activeQubits: 22 },
    circuit: {
      shownWires: ["k0…k13 (14 key qubits)", "data (8)", "scratch"],
      totalWires: 22,
      gates: [
        { col: 0, wire: 0, label: "H⊗14", kind: "step", span: 3 },
        { col: 1, wire: 0, label: "Oracle: first byte only", kind: "step", span: 3 },
        { col: 2, wire: 0, label: "Diffuser", kind: "step", span: 3 },
        { col: 3, wire: 0, label: "repeat (π/4)√(N/M)", kind: "step", span: 3 },
        { col: 4, wire: 0, label: "M", kind: "measure" },
      ],
      caption:
        "Many marked keys change the iteration count, not the oracle structure.",
    },
    histogram: [
      { label: "marked key A", value: 0.18 },
      { label: "marked key B", value: 0.17 },
      { label: "marked key C", value: 0.16, highlight: true },
      { label: "other marked", value: 0.15 },
      { label: "rest", value: 0.34 / 4 },
      { label: "…", value: 0.34 / 4 },
      { label: "…", value: 0.34 / 4 },
      { label: "…", value: 0.34 / 4 },
    ],
    featured: false,
  },
  {
    id: 7,
    codename: "The Hidden Angle",
    algorithm: "Quantum phase estimation",
    level: "Hard",
    points: 5,
    lock: "SHA-256 keystream XOR with a 14-bit phase key.",
    problem:
      "A one-qubit gate U hides an angle φ = k/2^14. Its eigenstate is provided; the global phase of U matters once it is controlled.",
    approach:
      "Put the eigenstate in U's eigenvector, apply controlled-U^(2^j) on 14 control qubits, and read the phase bits with an inverse QFT. The 14 bits are exact, one per qubit.",
    measurement:
      "The 14-bit readout is a binary fraction: the histogram peaks at the bit pattern of k, and noise appears as neighbouring patterns.",
    postprocessing:
      "Assemble the 14 bits in register order into k, format with leading zeros, run the keystream, XOR and verify.",
    metrics: { twoQubitGates: 230, depth: 271, totalGates: 763, activeQubits: 15 },
    circuit: {
      shownWires: ["c0…c13 (phase)", "eigenstate"],
      totalWires: 15,
      gates: [
        { col: 0, wire: 0, label: "H⊗14", kind: "step", span: 1 },
        { col: 1, wire: 0, label: "controlled-U^2^j", kind: "step", span: 2 },
        { col: 2, wire: 0, label: "QFT†", kind: "step", span: 1 },
        { col: 3, wire: 0, label: "measure 14 bits", kind: "measure" },
      ],
      caption:
        "Controlled powers put the angle on the control register; the inverse QFT turns it into binary digits.",
    },
    histogram: [
      { label: "0110 1001 1011 01", value: 0.74, highlight: true },
      { label: "neighbour −1", value: 0.09 },
      { label: "neighbour +1", value: 0.08 },
      { label: "other", value: 0.09 / 3 },
      { label: "…", value: 0.09 / 3 },
      { label: "…", value: 0.09 / 3 },
    ],
    featured: false,
  },
  {
    id: 8,
    codename: "The Wrapped Key, N = 35",
    algorithm: "Shor's algorithm (factoring)",
    level: "Hard",
    points: 6,
    lock: "RSA-wrapped key (N = 35), then SHA-256 keystream XOR.",
    problem:
      "Textbook RSA wraps a small symmetric key. Factoring a 35 modulus is easy classically; the challenge is to factor it with a quantum order-finding circuit.",
    approach:
      "Pick a base coprime to N, build a reversible modular multiplication, and use phase estimation to find the multiplicative order r. Factors follow from gcd(a^(r/2) ± 1, N).",
    measurement:
      "The order-finding register shows peaks at multiples of 1/r. Continued fractions turn the measured phase into a candidate order, which is then verified.",
    postprocessing:
      "Derive the private exponent d, compute k = c^d mod N, format it to the published key width, run the keystream and verify.",
    metrics: { twoQubitGates: 49920, depth: 135160, totalGates: 148085, activeQubits: 18 },
    circuit: {
      shownWires: ["counting (2n)", "work register"],
      totalWires: 18,
      gates: [
        { col: 0, wire: 0, label: "H⊗counting", kind: "step", span: 1 },
        { col: 1, wire: 0, label: "controlled a^(2^j) mod N", kind: "step", span: 2 },
        { col: 2, wire: 0, label: "QFT†", kind: "step", span: 1 },
        { col: 3, wire: 0, label: "measure", kind: "measure" },
      ],
      caption:
        "Order finding is the quantum core; factoring and RSA unwrapping are classical.",
    },
    histogram: [
      { label: "phase ≈ 0", value: 0.21 },
      { label: "1/r", value: 0.24, highlight: true },
      { label: "2/r", value: 0.22 },
      { label: "3/r", value: 0.19 },
      { label: "other", value: 0.14 },
    ],
    featured: false,
  },
  {
    id: 9,
    codename: "The Wrapped Key, N = 77",
    algorithm: "Shor's algorithm, N = 77",
    level: "Very hard",
    points: 6,
    lock: "RSA-wrapped key (N = 77), then SHA-256 keystream XOR.",
    problem:
      "Same scheme with N = 77. There is no shortcut for this modulus, so modular multiplication has to be built for real.",
    approach:
      "A reversible controlled multiplication by a on 7 work qubits, then order finding exactly as in tier 8. Dense unitary constructions transpile slowly and lose simplicity points.",
    measurement:
      "Order peaks at multiples of 1/r over the counting register; the clock and work registers must both be initialised correctly.",
    postprocessing:
      "Factor verification, private exponent, RSA unwrap, fixed-width key string, keystream and hash check.",
    metrics: { twoQubitGates: 117739, depth: 316820, totalGates: 349949, activeQubits: 21 },
    circuit: {
      shownWires: ["counting", "work (7 qubits)", "aux"],
      totalWires: 21,
      gates: [
        { col: 0, wire: 0, label: "H⊗counting", kind: "step", span: 1 },
        { col: 1, wire: 0, label: "controlled ×a mod 77", kind: "step", span: 3 },
        { col: 2, wire: 0, label: "QFT†", kind: "step", span: 1 },
        { col: 3, wire: 0, label: "measure", kind: "measure" },
      ],
      caption:
        "The permutation-based multiplier dominates the gate count and depth.",
    },
    histogram: [
      { label: "phase ≈ 0", value: 0.16 },
      { label: "1/r", value: 0.28, highlight: true },
      { label: "2/r", value: 0.24 },
      { label: "3/r", value: 0.2 },
      { label: "other", value: 0.12 },
    ],
    featured: false,
  },
  {
    id: 10,
    codename: "The Handshake",
    algorithm: "Shor's discrete logarithm",
    level: "Boss",
    points: 7,
    lock: "Diffie–Hellman shared secret, then SHA-256 keystream XOR with a 7-bit key.",
    problem:
      "Alice and Bob agreed on a secret with Diffie–Hellman in a small group. One exponent is enough to rebuild the shared secret.",
    approach:
      "Two 6-bit control registers and a 7-bit work register. The function f(x,z) = g^x A^z is periodic: measuring both registers and applying two inverse QFTs yields a linear congruence on the exponent.",
    measurement:
      "Readouts are 12-bit strings, but the QFT has 64 points while the group order is 41. Raw values are rounded to the nearest frequency before any equation is formed.",
    postprocessing:
      "The two frequencies satisfy u·a ≡ v (mod 41). Candidate exponents are checked against A = g^a; a wrong rounding simply produces a failed candidate and is skipped. The shared secret B^a then becomes the 7-bit keystream key.",
    caveat:
      "Raw 6-bit readouts must never be used as mod-41 frequencies: 64 ≠ 41. The classical module rejects inconsistent samples rather than merging them blindly.",
    metrics: { twoQubitGates: 107168, depth: 287674, totalGates: 317957, activeQubits: 19 },
    circuit: {
      shownWires: ["X: x0…x5", "Z: z0…z5", "work: w0…w6"],
      totalWires: 19,
      gates: [
        { col: 0, wire: 0, label: "H⊗6", kind: "step", span: 1 },
        { col: 0, wire: 1, label: "H⊗6", kind: "step", span: 1 },
        { col: 1, wire: 0, label: "controlled g^2^j", kind: "step", span: 1 },
        { col: 1, wire: 1, label: "controlled A^2^j", kind: "step", span: 1 },
        { col: 2, wire: 0, label: "QFT†", kind: "step", span: 1 },
        { col: 2, wire: 1, label: "QFT†", kind: "step", span: 1 },
        { col: 3, wire: 0, label: "measure", kind: "measure" },
        { col: 3, wire: 1, label: "measure", kind: "measure" },
      ],
      caption:
        "X_j → c_j and Z_j → c_(6+j); counts print c11…c0, so the left six characters are Z.",
    },
    histogram: [
      { label: "support (x/64 ≈ s/41)", value: 0.31, highlight: true },
      { label: "support", value: 0.29 },
      { label: "support", value: 0.22 },
      { label: "off-support", value: 0.18 / 3 },
      { label: "…", value: 0.18 / 3 },
      { label: "…", value: 0.18 / 3 },
    ],
    featured: true,
  },
];

export type Version = "v1" | "v2";

export const versionLabels: Record<
  Version,
  { name: string; tag: string; detail: string }
> = {
  v1: {
    name: "v1 — Frozen Baseline",
    tag: "v1 · baseline",
    detail: "release/ten-locks-v1 (frozen submission)",
  },
  v2: {
    name: "v2 — Verified Optimized Candidate",
    tag: "v2 · candidate",
    detail: "integration/optimized-v2-candidate (not submitted)",
  },
};

export const depthAggregateNote =
  "The depth figure is the sum of ten separate circuits, not the depth of a single physical circuit.";

/** Metrics for the selected version; unchanged tiers inherit the v1 record. */
export function metricsFor(tier: TierData, version: Version): TierMetrics {
  if (version === "v2" && tier.metricsV2) {
    return tier.metricsV2;
  }
  return tier.metrics;
}

export const tierMap = new Map(tiers.map((tier) => [tier.id, tier]));

export interface AggregateMetrics {
  twoQubitGates: number;
  depth: number;
  totalGates: number;
}

/** Totals recomputed from the per-tier records of the selected version. */
export function aggregateFor(version: Version): AggregateMetrics {
  return tiers.reduce<AggregateMetrics>(
    (total, tier) => {
      const metrics = metricsFor(tier, version);
      return {
        twoQubitGates: total.twoQubitGates + metrics.twoQubitGates,
        depth: total.depth + metrics.depth,
        totalGates: total.totalGates + metrics.totalGates,
      };
    },
    { twoQubitGates: 0, depth: 0, totalGates: 0 },
  );
}

export function totalTwoQubitGates(version: Version = "v1"): number {
  return aggregateFor(version).twoQubitGates;
}

export function totalDepth(version: Version = "v1"): number {
  return aggregateFor(version).depth;
}

export const presentationTiers = [1, 5, 10];
