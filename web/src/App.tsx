import { useCallback, useEffect, useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { GuidedIntro } from "./components/GuidedIntro";
import { PresentationMode } from "./components/PresentationMode";
import { TierDetail } from "./components/TierDetail";
import { tierMap, type Version } from "./data/tiers";

type View = "intro" | "dashboard" | "detail" | "presentation";

interface Route {
  view: View;
  tier: number | null;
}

function parseHash(hash: string): Route {
  const value = hash.replace(/^#/, "");
  if (value === "intro" || value === "") {
    return { view: "intro", tier: null };
  }
  if (value === "present") {
    return { view: "presentation", tier: null };
  }
  if (value === "dashboard") {
    return { view: "dashboard", tier: null };
  }
  const match = /^tier-(\d+)$/.exec(value);
  if (match && tierMap.has(Number(match[1]))) {
    return { view: "detail", tier: Number(match[1]) };
  }
  return { view: "intro", tier: null };
}

function hashFor(route: Route): string {
  if (route.view === "presentation") {
    return "#present";
  }
  if (route.view === "detail" && route.tier !== null) {
    return `#tier-${route.tier}`;
  }
  if (route.view === "dashboard") {
    return "#dashboard";
  }
  return "#intro";
}

export default function App() {
  const [route, setRoute] = useState<Route>(() =>
    typeof window === "undefined"
      ? { view: "intro", tier: null }
      : parseHash(window.location.hash),
  );
  const [version, setVersion] = useState<Version>("v1");

  const openTier = useCallback((id: number) => setRoute({ view: "detail", tier: id }), []);
  const startPresentation = useCallback(() => setRoute({ view: "presentation", tier: null }), []);
  const returnToDashboard = useCallback(() => setRoute({ view: "dashboard", tier: null }), []);
  const replayIntro = useCallback(() => setRoute({ view: "intro", tier: null }), []);
  const enterDashboard = useCallback(() => setRoute({ view: "dashboard", tier: null }), []);

  useEffect(() => {
    const next = hashFor(route);
    const current = window.location.hash;
    if (current !== next) {
      window.history.replaceState(
        null,
        "",
        next || window.location.pathname + window.location.search,
      );
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

  if (route.view === "intro") {
    return <GuidedIntro onEnter={enterDashboard} />;
  }

  if (route.view === "presentation") {
    return (
      <PresentationMode
        version={version}
        onVersionChange={setVersion}
        onExit={returnToDashboard}
      />
    );
  }

  const tier = route.tier === null ? undefined : tierMap.get(route.tier);

  return (
    <div className="app">
      <Dashboard
        version={version}
        onVersionChange={setVersion}
        onOpenTier={openTier}
        onPresent={startPresentation}
        onReplayIntro={replayIntro}
      />
      {route.view === "detail" && tier ? (
        <TierDetail tier={tier} version={version} onClose={returnToDashboard} />
      ) : null}
    </div>
  );
}
