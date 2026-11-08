import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "../App";

async function openTier(name: RegExp) {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name }));
  return { user, dialog: screen.getByRole("dialog") };
}

describe("tier detail", () => {
  it("exposes every required section for a featured tier", async () => {
    const { dialog } = await openTier(/open tier 1: the parity vault/i);

    for (const heading of [
      /^problem$/i,
      /^quantum approach$/i,
      /^circuit$/i,
      /^measurement analysis$/i,
      /^classical post-processing$/i,
      /^official checker verification$/i,
      /^circuit complexity$/i,
    ]) {
      expect(within(dialog).getByRole("heading", { name: heading })).toBeInTheDocument();
    }
  });

  it("labels illustrative figures and recorded checker output", async () => {
    const { dialog } = await openTier(/open tier 1: the parity vault/i);

    expect(within(dialog).getAllByText(/illustrative schematic/i).length).toBeGreaterThan(0);
    expect(within(dialog).getByText(/illustrative distribution/i)).toBeInTheDocument();
    expect(within(dialog).getAllByText(/^recorded$/i).length).toBe(2);
    expect(within(dialog).getByText(/official checker verification/i)).toBeInTheDocument();
  });

  it("moves focus to the close control and restores the page on close", async () => {
    const { user, dialog } = await openTier(/open tier 1: the parity vault/i);

    const close = within(dialog).getByRole("button", { name: /close tier detail/i });
    expect(close).toHaveFocus();

    await user.click(close);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("");
  });

  it("shows the exact recorded metrics for tier 10", async () => {
    const { dialog } = await openTier(/open tier 10: the handshake/i);

    expect(within(dialog).getByText("107,168")).toBeInTheDocument();
    expect(within(dialog).getByText("287,674")).toBeInTheDocument();
    expect(within(dialog).getAllByText(/64 .*41|64-point|64 points/i).length).toBeGreaterThan(0);
  });
});
