import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import App from "../App";

function stubReducedMotion(reduced: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: reduced && query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => {
  // @ts-expect-error - jsdom does not implement matchMedia by default
  delete window.matchMedia;
});

describe("guided intro", () => {
  it("opens on the first scene and shows progress", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { level: 1, name: /one message\. ten quantum locks\./i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/scene 1 of 4/i)).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: /intro progress/i })).toHaveAttribute(
      "aria-valuenow",
      "1",
    );
  });

  it("walks all four scenes and enters the dashboard", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByRole("heading", { level: 1, name: /superposition, interference, measurement/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByRole("heading", { level: 1, name: /each lock needs a different idea/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByRole("heading", { level: 1, name: /open a lock, see the whole pipeline/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /enter the dashboard/i }));
    expect(screen.getByRole("heading", { level: 1, name: /ten locks\.\s*one message\./i })).toBeInTheDocument();
  });

  it("supports back, skip and replay", async () => {
    const user = userEvent.setup();
    render(<App />);

    const back = screen.getByRole("button", { name: /back/i });
    expect(back).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(back);
    expect(screen.getByText(/scene 1 of 4/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /skip intro/i }));
    expect(screen.getByRole("button", { name: /replay guided intro/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /replay guided intro/i }));
    expect(screen.getByText(/scene 1 of 4/i)).toBeInTheDocument();
  });

  it("replays from the intro bar", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /next/i }));
    await user.click(screen.getByRole("button", { name: /replay intro/i }));
    expect(screen.getByText(/scene 1 of 4/i)).toBeInTheDocument();
  });

  it("navigates with the keyboard", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.keyboard("{ArrowRight}");
    expect(screen.getByText(/scene 2 of 4/i)).toBeInTheDocument();

    await user.keyboard("{ArrowLeft}");
    expect(screen.getByText(/scene 1 of 4/i)).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: /replay guided intro/i })).toBeInTheDocument();
  });

  it("honours the reduced-motion preference", () => {
    stubReducedMotion(true);
    render(<App />);
    expect(screen.getByRole("main")).toHaveAttribute("data-reduced-motion", "true");
  });

  it("does not claim parallel evaluation of every key", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(
      screen.getByText(/not a shortcut that reads every key at the same time/i),
    ).toBeInTheDocument();
  });
});
