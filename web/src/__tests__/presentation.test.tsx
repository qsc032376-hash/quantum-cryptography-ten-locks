import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("presentation mode", () => {
  it("steps through the curated tiers with the buttons", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));
    expect(screen.getByRole("heading", { level: 2, name: /ten locks, one message/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByRole("heading", { level: 2, name: /bernstein–vazirani/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByRole("heading", { level: 2, name: /grover search/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(
      screen.getByRole("heading", { level: 2, name: /discrete logarithm/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByRole("heading", { level: 2, name: /summary/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("supports keyboard navigation and escape to the dashboard", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("heading", { level: 2, name: /bernstein–vazirani/i })).toBeInTheDocument();

    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("heading", { level: 2, name: /ten locks, one message/i })).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: /enter presentation mode/i })).toBeInTheDocument();
  });

  it("jumps with the progress dots", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));
    await user.click(screen.getByRole("button", { name: /go to slide 4: shor discrete logarithm/i }));

    expect(
      screen.getByRole("heading", { level: 2, name: /discrete logarithm/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("4 / 5")).toBeInTheDocument();
  });

  it("tells judges that results are pre-recorded", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /enter presentation mode/i }));

    expect(screen.getByText(/nothing runs live in this demo/i)).toBeInTheDocument();
  });
});
