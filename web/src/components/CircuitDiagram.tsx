import type { CircuitSpec, GateSpec } from "../data/tiers";

const WIRE_GAP = 44;
const TOP = 44;
const LEFT = 138;
const GAP = 26;

function widthOf(gate: GateSpec): number {
  if (gate.kind === "step") {
    return Math.max(96, gate.label.length * 5.9 + 22);
  }
  if (gate.kind === "measure") {
    return 46;
  }
  return 34;
}

/**
 * Illustrative gate-level schematic.
 *
 * This is a teaching diagram built from the public algorithm description, not a
 * screenshot of a transpiled circuit. The UI always labels it as illustrative.
 */
export function CircuitDiagram({ circuit }: { circuit: CircuitSpec }) {
  const columnWidths = new Map<number, number>();
  for (const gate of circuit.gates) {
    const current = columnWidths.get(gate.col) ?? 0;
    columnWidths.set(gate.col, Math.max(current, widthOf(gate)));
  }

  const columns = [...columnWidths.keys()].sort((a, b) => a - b);
  const centers = new Map<number, number>();
  let cursor = LEFT;
  for (const col of columns) {
    const width = columnWidths.get(col) ?? 34;
    centers.set(col, cursor + width / 2);
    cursor += width + GAP;
  }

  const width = cursor + 12;
  const height = TOP + circuit.shownWires.length * WIRE_GAP;
  const y = (wire: number) => TOP + wire * WIRE_GAP;

  return (
    <div className="circuit">
      <svg
        role="img"
        aria-label={`Schematic circuit for ${circuit.totalWires} qubits`}
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        preserveAspectRatio="xMidYMin meet"
        className="circuit-svg"
      >
        <defs>
          <linearGradient id="wire" x1="0" x2="1">
            <stop offset="0" stopColor="#2a3a5e" />
            <stop offset="1" stopColor="#3c5a8f" />
          </linearGradient>
        </defs>

        {circuit.shownWires.map((label, index) => (
          <g key={`${label}-${index}`}>
            <text x={LEFT - 16} y={y(index) + 4} textAnchor="end" className="wire-label">
              {label}
            </text>
            <line
              x1={LEFT - 4}
              x2={width - 12}
              y1={y(index)}
              y2={y(index)}
              stroke="url(#wire)"
              strokeWidth={1.4}
            />
          </g>
        ))}

        {circuit.gates.map((gate, index) => {
          const cx = centers.get(gate.col) ?? LEFT;
          const cy = y(gate.wire);

          if (gate.kind === "control") {
            const target = y(gate.target ?? gate.wire + 1);
            return (
              <g key={`${gate.col}-${gate.wire}-${index}`}>
                <line x1={cx} x2={cx} y1={cy} y2={target} stroke="#7dd3fc" strokeWidth={1.6} />
                <circle cx={cx} cy={cy} r={4.5} fill="#7dd3fc" />
                <circle cx={cx} cy={target} r={9} fill="none" stroke="#7dd3fc" strokeWidth={1.6} />
                <line x1={cx - 9} x2={cx + 9} y1={target} y2={target} stroke="#7dd3fc" strokeWidth={1.4} />
                <line x1={cx} x2={cx} y1={target - 9} y2={target + 9} stroke="#7dd3fc" strokeWidth={1.4} />
              </g>
            );
          }

          if (gate.kind === "measure") {
            return (
              <g key={`${gate.col}-${gate.wire}-${index}`}>
                <rect
                  x={cx - 22}
                  y={cy - 15}
                  width={44}
                  height={30}
                  rx={6}
                  className="gate-box gate-measure"
                />
                <text x={cx} y={cy + 4} textAnchor="middle" className="gate-label">
                  M
                </text>
              </g>
            );
          }

          if (gate.kind === "step") {
            const span = gate.span ?? 1;
            const top = y(gate.wire) - 18;
            const bottom = y(gate.wire + span - 1) + 18;
            const w = columnWidths.get(gate.col) ?? 96;
            return (
              <g key={`${gate.col}-${gate.wire}-${index}`}>
                <rect
                  x={cx - w / 2}
                  y={top}
                  width={w}
                  height={bottom - top}
                  rx={10}
                  className="gate-box gate-step"
                />
                <text
                  x={cx}
                  y={(top + bottom) / 2 + 4}
                  textAnchor="middle"
                  className="gate-label step-label"
                >
                  {gate.label}
                </text>
              </g>
            );
          }

          return (
            <g key={`${gate.col}-${gate.wire}-${index}`}>
              <rect
                x={cx - 17}
                y={cy - 15}
                width={34}
                height={30}
                rx={6}
                className="gate-box"
              />
              <text x={cx} y={cy + 4} textAnchor="middle" className="gate-label">
                {gate.label}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="circuit-caption">{circuit.caption}</p>
    </div>
  );
}
