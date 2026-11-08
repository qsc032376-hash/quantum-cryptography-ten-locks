import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("tier 5 before/after comparison", () => {
  it("shows both runs, the improvements, and the independent status", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /open tier 5: the small safe/i }));
    const dialog = screen.getByRole("dialog");
    const compare = within(dialog).getByRole("region", { name: /tier 5 — before \/ after/i });

    expect(within(compare).getAllByText(/28\.4%/).length).toBeGreaterThan(0);
    expect(within(compare).getAllByText(/10\.7%/).length).toBeGreaterThan(0);

    expect(within(compare).getAllByText("21,150").length).toBeGreaterThan(0);
    expect(within(compare).getByText("15,150")).toBeInTheDocument();
    expect(within(compare).getAllByText("33,055").length).toBeGreaterThan(0);
    expect(within(compare).getByText("29,503")).toBeInTheDocument();

    expect(within(compare).getByText(/candidate · not merged/i)).toBeInTheDocument();
    expect(within(compare).getByText(/does not claim/i)).toBeInTheDocument();
    expect(within(compare).getByText(/s-box and bit permutation/i)).toBeInTheDocument();
  });

  it("does not present the optimized circuit as the frozen release", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /open tier 5: the small safe/i }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/frozen release remains the baseline/i)).toBeInTheDocument();
  });
});
