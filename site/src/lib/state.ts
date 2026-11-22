// View state for the overview, kept in the URL so a view can be shared as a link.
import type { WindowKey } from "./types";

export type Unit = "usd" | "pct";
export type CapType = "total" | "fdi" | "portfolio" | "other";
export type Reserves = "ex" | "in";
export type Sel = "top20" | "all";
export type View = "ranking" | "map";

export interface ViewState {
  view: View;
  period: WindowKey;
  unit: Unit;
  type: CapType;
  reserves: Reserves;
  sel: Sel;
}

// Design default: last four quarters, excluding reserves, USD bn (the map defaults to % of GDP).
export const DEFAULTS: ViewState = {
  view: "ranking",
  period: "4q",
  unit: "usd",
  type: "total",
  reserves: "ex",
  sel: "top20",
};

const ALLOWED: { [K in keyof ViewState]: readonly ViewState[K][] } = {
  view: ["ranking", "map"],
  period: ["q", "4q", "year", "latest"],
  unit: ["usd", "pct"],
  type: ["total", "fdi", "portfolio", "other"],
  reserves: ["ex", "in"],
  sel: ["top20", "all"],
};

export function parseState(search: string): ViewState {
  const params = new URLSearchParams(search);
  const out = { ...DEFAULTS } as Record<keyof ViewState, string>;
  for (const key of Object.keys(ALLOWED) as (keyof ViewState)[]) {
    const v = params.get(key);
    if (v !== null && (ALLOWED[key] as readonly string[]).includes(v)) out[key] = v;
  }
  if (out.view === "map" && params.get("unit") === null) out.unit = "pct";
  return out as ViewState;
}

const defaultUnit = (s: ViewState): Unit => (s.view === "map" ? "pct" : "usd");

/** Only non-default values go into the URL, so the default view has a clean link. */
export function serializeState(s: ViewState): string {
  const params = new URLSearchParams();
  for (const key of Object.keys(ALLOWED) as (keyof ViewState)[]) {
    const def = key === "unit" ? defaultUnit(s) : DEFAULTS[key];
    if (s[key] !== def) params.set(key, s[key]);
  }
  const q = params.toString();
  return q ? `?${q}` : "";
}

export function measureFor(s: ViewState): string {
  switch (s.type) {
    case "fdi":
      return "fdi";
    case "portfolio":
      return "portfolio";
    case "other":
      return "other_inv";
    default:
      return s.reserves === "in" ? "fa_total" : "fa_ex_reserves";
  }
}
