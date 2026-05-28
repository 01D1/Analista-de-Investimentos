"use client";

import React, { useState } from "react";
import RadarAI from "./components/pages/RadarAI";
import ThesisBuilder from "./components/pages/ThesisBuilder";
import SignalMatrix from "./components/pages/SignalMatrix";
import Watchlist from "./components/pages/Watchlist";
import MacroEngine from "./components/pages/MacroEngine";
import QuantCore from "./components/pages/QuantCore";
import ValuationEngine from "./components/pages/ValuationEngine";
import ConvictionDesk from "./components/pages/ConvictionDesk";
import EventScheduler from "./components/pages/EventScheduler";
import AgentRuntime from "./components/pages/AgentRuntime";
import OptionsRadar from "./components/pages/OptionsRadar";
import AssetDetailDrawer from "./components/AssetDetailDrawer";

type Page = "radar-ai" | "thesis-builder" | "signal-matrix" | "watchlist"
  | "macro-engine" | "quant-core" | "valuation-engine" | "options-radar"
  | "conviction-desk" | "event-scheduler" | "agent-runtime";

const NAVIGATION = [
  {
    section: "INTELLIGENCE",
    items: ["radar-ai", "thesis-builder", "signal-matrix", "watchlist"] as Page[],
  },
  {
    section: "MARKETS",
    items: ["macro-engine", "quant-core", "options-radar", "valuation-engine"] as Page[],
  },
  {
    section: "OPERATIONS",
    items: ["conviction-desk", "event-scheduler", "agent-runtime"] as Page[],
  },
];

function label(page: Page): string {
  return page.replaceAll("-", " ").toUpperCase();
}

export default function AppShell() {
  const [page, setPage] = useState<Page>("radar-ai");

  function renderPage(): React.ReactNode {
    switch (page) {
      case "radar-ai":        return <RadarAI />;
      case "thesis-builder":   return <ThesisBuilder />;
      case "signal-matrix":    return <SignalMatrix />;
      case "watchlist":        return <Watchlist />;
      case "macro-engine":     return <MacroEngine />;
      case "quant-core":       return <QuantCore />;
      case "options-radar":    return <OptionsRadar />;
      case "valuation-engine": return <ValuationEngine />;
      case "conviction-desk":  return <ConvictionDesk />;
      case "event-scheduler":  return <EventScheduler />;
      case "agent-runtime":    return <AgentRuntime />;
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="wordmark">
            <b>RADAR MACRO</b>
            <span>TERMINAL</span>
          </div>
        </div>

        {NAVIGATION.map((group) => (
          <div key={group.section}>
            <div className="sec">{group.section}</div>

            {group.items.map((item) => (
              <button
                key={item}
                className={`nav-item ${page === item ? "active" : ""}`}
                onClick={() => setPage(item)}
              >
                {label(item)}
              </button>
            ))}
          </div>
        ))}
      </aside>

      <main className="main-col">
        <div className="topbar">
          <div className="search">
            <input placeholder="Buscar ativo, tese ou sinal..." />
          </div>

          <div className="right">
            <button className="btn primary" onClick={() => window.location.reload()}>
              Executar Scan
            </button>

            <div className="market-status">
              <span className="dot" />
              API conectada
            </div>
          </div>
        </div>

        <div className="content">{renderPage()}</div>
      </main>

      {/* Global drawer, mounted once — subscribes to drawerStore */}
      <AssetDetailDrawer />
    </div>
  );
}