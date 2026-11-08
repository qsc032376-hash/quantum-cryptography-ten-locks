import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderDashboard } from "../test/helpers";

describe("dashboard navigation", () => {
  it("renders one card per tier and opens a detail view", async () => {
    const user = userEvent.setup();
    renderDashboard();

    const cards = screen.getAllByRole("button", { name: /^open tier \d+:/i });
    expect(cards).toHaveLength(10);

    await user.click(screen.getByRole("button", { name: /open tier 3: twenty-four seals/i }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("heading", { level: 2, name: /twenty-four seals/i })).toBeInTheDocument();
  });

  it("returns to the dashboard from the detail footer", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(screen.getByRole("button", { name: /open tier 7: the hidden angle/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /back to all ten locks/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^open tier \d+:/i })).toHaveLength(10);
  });

  it("closes the detail with the escape key", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(screen.getByRole("button", { name: /open tier 1: the parity vault/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
