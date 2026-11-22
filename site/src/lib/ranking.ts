import type { Meta, Ranking, Status } from "./types";
import { measureFor, type ViewState } from "./state";

export interface Bar {
  country: string;
  value: number | null; // in the selected unit
  usd: number | null;
  pct: number | null;
  period: string | null; // the period the value refers to (only varies for "latest")
  status: Status;
  aggregate: boolean;
  inTop20: boolean;
}

/** Rows for the ranking: present values sorted high -> low, then missing ones. Never 0 for missing. */
export function rankingBars(meta: Meta, ranking: Ranking, s: ViewState): Bar[] {
  const measure = measureFor(s);
  const isMain = measure === "fa_ex_reserves";
  const byIso = new Map(meta.countries.map((c) => [c.iso3, c]));
  const bars: Bar[] = [];
  for (const row of ranking.rows) {
    const c = byIso.get(row.country);
    if (!c) continue;
    if (s.sel === "top20" && !row.in_top20) continue;
    const mv = row.values[measure];
    const cell = mv?.[s.period];
    const v = cell ? cell[s.unit] : null;
    let status: Status;
    if (v === null || v === undefined) status = "missing";
    else if (isMain && s.period !== "latest") status = row.status[s.period] === "derived" ? "derived" : "reported";
    else status = "reported";
    const period =
      s.period === "latest" ? (mv?.latest.period ?? null) : s.period === "q" ? ranking.windows.q[0] : null;
    bars.push({
      country: row.country,
      value: v ?? null,
      usd: cell?.usd ?? null,
      pct: cell?.pct ?? null,
      period,
      status,
      aggregate: c.aggregate,
      inTop20: row.in_top20,
    });
  }
  const present = bars.filter((b) => b.value !== null).sort((a, b) => (b.value as number) - (a.value as number));
  const missing = bars.filter((b) => b.value === null).sort((a, b) => a.country.localeCompare(b.country));
  return [...present, ...missing];
}

export function windowPeriods(ranking: Ranking, s: ViewState): string[] {
  return s.period === "latest" ? [] : ranking.windows[s.period];
}
