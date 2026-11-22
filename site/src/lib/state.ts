// View state for the overview, kept in the URL so a view can be shared as a link.
import type { WindowKey } from "./types";

export type Unit = "usd" | "pct";
export type CapType = "total" | "fdi" | "portfolio" | "other";
export type Reserves = "ex" | "in";
export type Sel = "top20" | "all";

export interface ViewState {
  period: WindowKey;
  unit: Unit;
  type: CapType;
  reserves: Reserves;
  sel: Sel;
}

// Design default: last four quarters, excluding reserves, USD bn.
export const DEFAULTS: ViewState = {
  period: "4q",
  unit: "usd",
  type: "total",
  reserves: "ex",
  sel: "top20",
};

const ALLOWED: { [K in keyof ViewState]: readonly ViewState[K][] } = {
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
  return out as ViewState;
}

/** Only non-default values go into the URL, so the default view has a clean link. */
export function serializeState(s: ViewState): string {
  const params = new URLSearchParams();
  for (const key of Object.keys(ALLOWED) as (keyof ViewState)[]) {
    if (s[key] !== DEFAULTS[key]) params.set(key, s[key]);
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
