import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderDashboard } from "../test/helpers";
import { aggregateFor, metricsFor, tierMap, tiers } from "../data/tiers";

describe("v1 / v2 version selection", () => {
  it("recomputes the aggregates from per-tier records", () => {
    const v1 = aggregateFor("v1");
    const v2 = aggregateFor("v2");

    expect(v1.twoQubitGates).toBe(307349);
    expect(v1.depth).toBe(787876);
    expect(v2.twoQubitGates).toBe(301349);
    expect(v2.depth).toBe(784324);

    // The aggregates must equal the sum of the rendered per-tier records.
    for (const version of ["v1", "v2"] as const) {
      const sumQ = tiers.reduce((sum, tier) => sum + metricsFor(tier, version).twoQubitGates, 0);
      const sumDepth = tiers.reduce((sum, tier) => sum + metricsFor(tier, version).depth, 0);
      expect(aggregateFor(version).twoQubitGates).toBe(sumQ);
      expect(aggregateFor(version).depth).toBe(sumDepth);
    }

    expect(metricsFor(tierMap.get(5)!, "v1")).toMatchObject({
      twoQubitGates: 21150,
      depth: 33055,
    });
    expect(metricsFor(tierMap.get(5)!, "v2")).toMatchObject({
      twoQubitGates: 15150,
      depth: 29503,
    });
    // Unchanged tiers inherit the v1 record.
    expect(metricsFor(tierMap.get(1)!, "v2")).toEqual(metricsFor(tierMap.get(1)!, "v1"));
  });

  it("updates dashboard totals when v2 is selected", async () => {
    const user = userEvent.setup();
    renderDashboard();

    expect(screen.getByText("307,349")).toBeInTheDocument();
    expect(screen.getByText("787,876")).toBeInTheDocument();
    expect(screen.getByText(/sum of ten separate circuits/i)).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: /v2/i }));

    expect(screen.getByText("301,349")).toBeInTheDocument();
    expect(screen.getByText("784,324")).toBeInTheDocument();
    expect(screen.getAllByText(/not submitted/i).length).toBeGreaterThan(0);
  });

  it("carries the selected version into the Tier 5 detail", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(screen.getByRole("radio", { name: /v2/i }));
    await user.click(screen.getByRole("button", { name: /open tier 5: the small safe/i }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/V2 · candidate/i)).toBeInTheDocument();
    expect(within(dialog).getAllByText("15,150").length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText("29,503").length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText("21,150").length).toBeGreaterThan(0);
  });

  it("keeps the selected version in presentation mode", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(screen.getByRole("radio", { name: /v2/i }));
    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));

    expect(screen.getByText("301,349")).toBeInTheDocument();
    expect(screen.getByText(/v2/i, { selector: ".slide-facts strong" })).toBeInTheDocument();
  });
});
