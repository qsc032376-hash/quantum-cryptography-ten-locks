import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("intro and shell", () => {
  it("shows the hero copy and the checker summary", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { level: 1, name: /ten locks\.\s*one message\./i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/10 \/ 10/i)).toBeInTheDocument();
    expect(screen.getByText(/checker status full/i)).toBeInTheDocument();
  });

  it("opens presentation mode from the intro", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));

    expect(screen.getByRole("region", { name: /presentation mode/i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: /ten locks, one message/i }),
    ).toBeInTheDocument();
  });

  it("links to the provenance section", () => {
    render(<App />);
    expect(screen.getByRole("link", { name: /how the data is sourced/i })).toHaveAttribute(
      "href",
      "#provenance",
    );
  });
});
