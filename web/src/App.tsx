import { useCallback, useEffect, useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { PresentationMode } from "./components/PresentationMode";
import { TierDetail } from "./components/TierDetail";
import { tierMap } from "./data/tiers";

type View = "dashboard" | "detail" | "presentation";

interface Route {
  view: View;
  tier: number | null;
}

function parseHash(hash: string): Route {
  const value = hash.replace(/^#/, "");
  if (value === "present") {
    return { view: "presentation", tier: null };
  }
  const match = /^tier-(\d+)$/.exec(value);
  if (match && tierMap.has(Number(match[1]))) {
    return { view: "detail", tier: Number(match[1]) };
  }
  return { view: "dashboard", tier: null };
}

function hashFor(route: Route): string {
  if (route.view === "presentation") {
    return "#present";
  }
  if (route.view === "detail" && route.tier !== null) {
    return `#tier-${route.tier}`;
  }
  return "";
}

export default function App() {
  const [route, setRoute] = useState<Route>(() =>
    typeof window === "undefined" ? { view: "dashboard", tier: null } : parseHash(window.location.hash),
  );

  const openTier = useCallback((id: number) => setRoute({ view: "detail", tier: id }), []);
  const startPresentation = useCallback(() => setRoute({ view: "presentation", tier: null }), []);
  const returnToDashboard = useCallback(() => setRoute({ view: "dashboard", tier: null }), []);

  // Keep the URL hash in sync so a projector view can be restored after a refresh.
  useEffect(() => {
    const next = hashFor(route);
    const current = window.location.hash;
    if (current !== next) {
      window.history.replaceState(null, "", next || window.location.pathname + window.location.search);
    }
  }, [route]);

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (route.view === "dashboard") {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        returnToDashboard();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [route.view, returnToDashboard]);

  if (route.view === "presentation") {
    return <PresentationMode onExit={returnToDashboard} />;
  }

  const tier = route.tier === null ? undefined : tierMap.get(route.tier);

  return (
    <div className="app">
      <Dashboard onOpenTier={openTier} onPresent={startPresentation} />
      {route.view === "detail" && tier ? (
        <TierDetail tier={tier} onClose={returnToDashboard} />
      ) : null}
    </div>
  );
}
