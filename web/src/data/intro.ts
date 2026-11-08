/**
 * Guided intro copy — editable placeholder text.
 *
 * Dependency: `docs/WEB_DEMO_STORYBOARD.md` from Sicheng's branch was not found
 * on any fetched branch when this sprint ran, so the four scenes below are
 * written locally and kept as plain data for an easy swap once the storyboard
 * is approved. See web/README.md ("Storyboard dependency").
 */

export interface IntroScene {
  id: "mystery" | "principle" | "locks" | "lab";
  kicker: string;
  title: string;
  body: string;
  points: string[];
  note?: string;
  cta?: string;
}

export const introScenes: IntroScene[] = [
  {
    id: "mystery",
    kicker: "Scene 1 · The mystery",
    title: "One message. Ten quantum locks.",
    body: "Ten files are sealed, each with a different lock. Every lock says how its file is encoded, but not which algorithm opens it. Decrypt all ten, read the lines in order, and they form one message.",
    points: ["10 encrypted files", "10 different quantum algorithms", "1 final message"],
  },
  {
    id: "principle",
    kicker: "Scene 2 · The quantum principle",
    title: "Superposition, interference, measurement.",
    body: "A circuit prepares amplitudes over many inputs at once, but one measurement still returns one outcome. The algorithms win through interference: wrong paths cancel and the hidden structure survives. Quantum computing is not a shortcut that reads every key at the same time.",
    points: [
      "Prepare a superposition of inputs",
      "Interfere so wrong paths cancel",
      "Measure, then finish classically",
    ],
    note: "Nothing in this demo claims parallel evaluation of every candidate key.",
  },
  {
    id: "locks",
    kicker: "Scene 3 · Ten different locks",
    title: "Each lock needs a different idea.",
    body: "There is no single quantum trick that opens all ten. A parity query, a key handshake, oracle classification, a hidden period, a search, a phase readout, factoring, and a discrete logarithm each need their own circuit and their own classical follow-up.",
    points: [
      "Tier 1 · Bernstein–Vazirani parity",
      "Tier 2 · key distribution over a tapped link",
      "Tier 3 · Deutsch–Jozsa classification",
      "Tier 4 · Simon's hidden period",
      "Tier 5–6 · Grover search with a classical filter",
      "Tier 7 · quantum phase estimation",
      "Tier 8–9 · Shor order finding for RSA",
      "Tier 10 · Shor discrete logarithm",
    ],
  },
  {
    id: "lab",
    kicker: "Scene 4 · Enter the lab",
    title: "Open a lock, see the whole pipeline.",
    body: "The dashboard holds one card per lock: the algorithm, an illustrative circuit, the measurement logic, the classical post-processing and the recorded checker result. Switch between the frozen baseline and the verified optimized candidate.",
    points: [
      "v1 — frozen baseline metrics",
      "v2 — verified candidate, not submitted",
      "Recorded checker output, clearly labelled",
    ],
    cta: "Enter the dashboard",
  },
];

export const introStoryboardDependency =
  "docs/WEB_DEMO_STORYBOARD.md was not available on the fetched branches; scene copy is local placeholder text in src/data/intro.ts.";

export const introEstimatedSeconds = 55;
