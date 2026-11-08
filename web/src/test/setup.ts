import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

// The app mirrors its route into the URL hash; keep tests isolated from it.
afterEach(() => {
  window.history.replaceState(null, "", "/");
});
