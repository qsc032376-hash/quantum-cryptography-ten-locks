import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("accessibility basics", () => {
  it("gives every button an accessible name", () => {
    render(<App />);
    for (const button of screen.getAllByRole("button")) {
      expect(button).toHaveAccessibleName();
    }
  });

  it("labels every schematic image", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /open tier 1: the parity vault/i }));

    const images = screen.getAllByRole("img");
    expect(images.length).toBeGreaterThan(0);
    for (const image of images) {
      expect(image).toHaveAttribute("aria-label");
    }
  });

  it("exposes the tier detail as a labelled modal dialog", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /open tier 10: the handshake/i }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName(/the handshake/i);
  });

  it("keeps a single top-level heading on the dashboard", () => {
    render(<App />);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("labels the presentation region and progress controls", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));

    expect(screen.getByRole("region", { name: /presentation mode/i })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: /presentation progress/i })).toBeInTheDocument();
    for (const dot of screen.getAllByRole("button", { name: /go to slide \d+: /i })) {
      expect(dot).toHaveAccessibleName();
    }
  });
});
