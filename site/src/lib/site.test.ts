import { describe, expect, it } from "vitest";
import { num, pct, quarter, usd } from "./format";
import { rankingBars } from "./ranking";
import { DEFAULTS, measureFor, parseState, serializeState } from "./state";
import { barPath } from "./ranking-chart";
import { colorLimit } from "./heatmap-chart";
import type { Meta, Ranking } from "./types";

const cell = (usd: number | null, pct: number | null) => ({ usd, pct });
const mv = (v: number | null) => ({ q: cell(v, v), "4q": cell(v, v), year: cell(v, v), latest: { period: "2026-Q2", ...cell(v, v) } });

const meta = {
  countries: [
    { iso3: "USA", name_nb: "USA", name_en: "United States", in_top20: true, aggregate: false, financial_centre: false, latest: "2026-Q2" },
    { iso3: "CHN", name_nb: "Kina", name_en: "China", in_top20: true, aggregate: false, financial_centre: false, latest: "2026-Q2" },
    { iso3: "RUS", name_nb: "Russland", name_en: "Russia", in_top20: true, aggregate: false, financial_centre: false, latest: "2026-Q1" },
    { iso3: "NOR", name_nb: "Norge", name_en: "Norway", in_top20: false, aggregate: false, financial_centre: false, latest: "2026-Q2" },
  ],
} as unknown as Meta;

const ranking = {
  last_common_quarter: "2026-Q2",
  reference_year: 2025,
  windows: { q: ["2026-Q2"], "4q": ["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"], year: [] },
  rows: [
    { country: "CHN", in_top20: true, status: { q: "reported", "4q": "reported", year: "reported" }, values: { fa_ex_reserves: mv(-714), fa_total: mv(-700) } },
    { country: "RUS", in_top20: true, status: { q: "missing", "4q": "missing", year: "derived" }, values: { fa_ex_reserves: mv(null), fa_total: mv(-10) } },
    { country: "USA", in_top20: true, status: { q: "reported", "4q": "reported", year: "reported" }, values: { fa_ex_reserves: mv(1271), fa_total: mv(1262) } },
    { country: "NOR", in_top20: false, status: { q: "reported", "4q": "reported", year: "reported" }, values: { fa_ex_reserves: mv(-104), fa_total: mv(-104) } },
  ],
} as unknown as Ranking;

describe("state", () => {
  it("defaults to last four quarters, excluding reserves, USD", () => {
    expect(parseState("")).toEqual(DEFAULTS);
    expect(DEFAULTS).toMatchObject({ period: "4q", reserves: "ex", unit: "usd" });
  });
  it("ignores invalid values and round-trips", () => {
    const s = parseState("?period=year&unit=pct&type=bogus");
    expect(s).toMatchObject({ period: "year", unit: "pct", type: "total" });
    expect(serializeState(s)).toBe("?period=year&unit=pct");
    expect(serializeState(DEFAULTS)).toBe("");
  });
  it("maps the reserves toggle only for the total", () => {
    expect(measureFor({ ...DEFAULTS })).toBe("fa_ex_reserves");
    expect(measureFor({ ...DEFAULTS, reserves: "in" })).toBe("fa_total");
    expect(measureFor({ ...DEFAULTS, type: "fdi", reserves: "in" })).toBe("fdi");
  });
});

describe("rankingBars", () => {
  it("sorts high to low, puts missing last and never turns missing into zero", () => {
    const bars = rankingBars(meta, ranking, DEFAULTS);
    expect(bars.map((b) => b.country)).toEqual(["USA", "CHN", "RUS"]);
    expect(bars[2]).toMatchObject({ value: null, status: "missing" });
  });
  it("adds non-top-20 countries only for the wider selection", () => {
    expect(rankingBars(meta, ranking, { ...DEFAULTS, sel: "all" }).map((b) => b.country)).toEqual(["USA", "NOR", "CHN", "RUS"]);
  });
  it("marks derived values for the main measure", () => {
    const bars = rankingBars(meta, { ...ranking, rows: ranking.rows.map((r) => r.country === "RUS" ? { ...r, values: { ...r.values, fa_ex_reserves: mv(-5) } } : r) }, { ...DEFAULTS, period: "year" });
    expect(bars.find((b) => b.country === "RUS")?.status).toBe("derived");
  });
});

describe("format", () => {
  it("formats Norwegian and English numbers with explicit sign", () => {
    expect(num(1270.87, "nb")).toBe("+1 270,9");
    expect(num(-714.2, "en")).toBe("-714.2");
    expect(usd(null, "nb")).toBe("–");
    expect(pct(4, "en")).toBe("+4.0% of GDP");
    expect(quarter("2026-Q2", "nb")).toBe("2. kv. 2026");
    expect(quarter("2026-Q2", "en")).toBe("Q2 2026");
  });
});

describe("charts", () => {
  it("rounds only the data end of a bar", () => {
    expect(barPath(100, 200, 0, 16)).toMatch(/^M100,0H196Q200,0 200,4/);
    expect(barPath(100, 40, 0, 16)).toMatch(/^M100,0H44Q40,0 40,4/);
  });
  it("uses a clean symmetric color limit", () => {
    const rows = [{ country: "A", values: Array.from({ length: 100 }, (_, i) => i - 50 + 0.5) }];
    expect(colorLimit(rows)).toBe(50);
  });
});
