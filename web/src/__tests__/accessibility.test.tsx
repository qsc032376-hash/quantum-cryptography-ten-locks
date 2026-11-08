import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderDashboard } from "../test/helpers";

describe("accessibility basics", () => {
  it("gives every button an accessible name", () => {
    renderDashboard();
    for (const button of screen.getAllByRole("button")) {
      expect(button).toHaveAccessibleName();
    }
  });

  it("labels every schematic image", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("button", { name: /open tier 1: the parity vault/i }));

    const images = screen.getAllByRole("img");
    expect(images.length).toBeGreaterThan(0);
    for (const image of images) {
      expect(image).toHaveAttribute("aria-label");
    }
  });

  it("exposes the tier detail as a labelled modal dialog", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("button", { name: /open tier 10: the handshake/i }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName(/the handshake/i);
  });

  it("keeps a single top-level heading on the dashboard", () => {
    renderDashboard();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("keeps navigation available at a narrow viewport", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 375 });
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 667 });
    window.dispatchEvent(new Event("resize"));

    renderDashboard();

    expect(screen.getAllByRole("button", { name: /^open tier \d+:/i })).toHaveLength(10);
    expect(screen.getByRole("radiogroup", { name: /verification version/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /enter presentation mode/i })).toBeInTheDocument();
  });

  it("labels the presentation region and progress controls", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));

    expect(screen.getByRole("region", { name: /presentation mode/i })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: /presentation progress/i })).toBeInTheDocument();
    for (const dot of screen.getAllByRole("button", { name: /go to slide \d+: /i })) {
      expect(dot).toHaveAccessibleName();
    }
  });
});
