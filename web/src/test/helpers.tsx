import { render } from "@testing-library/react";
import App from "../App";

/**
 * Render the app directly on a route. The app boots into the guided intro when
 * the hash is empty, so dashboard-oriented tests start at `#dashboard`.
 */
export function renderAt(hash: string) {
  window.history.replaceState(null, "", hash);
  return render(<App />);
}

export function renderDashboard() {
  return renderAt("#dashboard");
}
