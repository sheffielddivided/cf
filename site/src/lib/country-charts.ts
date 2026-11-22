// Country page charts (Observable Plot). Colors are resolved from the theme's CSS variables.
import * as Plot from "@observablehq/plot";
import { themeColors } from "./colors";
import { num, quarter } from "./format";
import type { CountryData, EpisodeSeries, Lang } from "./types";

export const COMPONENTS = ["fdi", "portfolio", "other_inv", "derivatives", "reserves"] as const;

export interface Point { period: string; value: number }

/** Values for a measure/side, aligned with `periods`; nulls dropped (never drawn as zero). */
export function points(c: CountryData, measure: string, side: "net" | "assets" | "liabilities" = "net"): Point[] {
  const vals = c.series[measure]?.[side] ?? [];
  return c.periods.flatMap((p, i) => (vals[i] === null || vals[i] === undefined ? [] : [{ period: p, value: vals[i] as number }]));
}

/** Trailing 4-quarter moving average; null unless all four quarters exist. */
export function movingAverage(c: CountryData, measure: string, side: "net" | "assets" | "liabilities" = "net"): Point[] {
  const vals = c.series[measure]?.[side] ?? [];
  const out: Point[] = [];
  for (let i = 3; i < c.periods.length; i++) {
    const w = vals.slice(i - 3, i + 1);
    if (w.every((v) => v !== null && v !== undefined)) {
      out.push({ period: c.periods[i], value: (w as number[]).reduce((a, b) => a + b, 0) / 4 });
    }
  }
  return out;
}

const xAxis = (periods: string[], lang: Lang, every: number) => ({
  type: "band" as const,
  domain: periods,
  label: null,
  tickSize: 0,
  tickFormat: (p: string) => (p.endsWith("Q1") && Number(p.slice(0, 4)) % every === 0 ? p.slice(0, 4) : ""),
  padding: 0.18,
  ariaLabel: lang === "nb" ? "kvartal" : "quarter",
});

const yAxis = (lang: Lang) => ({
  label: lang === "nb" ? "mrd. USD" : "USD bn",
  grid: true,
  tickFormat: (v: number) => new Intl.NumberFormat(lang === "nb" ? "nb-NO" : "en-GB").format(v),
  labelArrow: "none" as const,
});

const base = (width: number) => ({
  width,
  height: width < 560 ? 240 : 300,
  marginLeft: 56,
  marginRight: 8,
  marginTop: 24,
  style: { fontSize: "12px", fontFamily: "var(--font)", background: "transparent", color: "var(--ink-2)", overflow: "visible" },
});

export function mainChart(c: CountryData, lang: Lang, width: number, labels: { quarterLbl: string; avgLbl: string }) {
  const col = themeColors();
  const data = points(c, "fa_ex_reserves");
  const ma = movingAverage(c, "fa_ex_reserves");
  const derived = new Set(c.derived_periods);
  return Plot.plot({
    ...base(width),
    x: xAxis(c.periods, lang, width < 560 ? 4 : 2),
    y: yAxis(lang),
    marks: [
      Plot.barY(data, {
        x: "period", y: "value",
        fill: (d: Point) => (d.value >= 0 ? col.inflow : col.outflow),
        rx: 2,
        fillOpacity: (d: Point) => (derived.has(d.period) ? 0.55 : 1),
      }),
      Plot.ruleY([0], { stroke: col.axis }),
      Plot.lineY(ma, { x: "period", y: "value", stroke: col.ink, strokeWidth: 2, curve: "monotone-x" }),
      Plot.tip(data, Plot.pointerX({
        x: "period", y: "value",
        title: (d: Point) => {
          const avg = ma.find((m) => m.period === d.period);
          return `${quarter(d.period, lang)}\n${labels.quarterLbl}: ${num(d.value, lang)}` +
            (avg ? `\n${labels.avgLbl}: ${num(avg.value, lang)}` : "") +
            (derived.has(d.period) ? `\n† ${lang === "nb" ? "beregnet" : "derived"}` : "");
        },
      })),
    ],
  });
}

export function componentsChart(c: CountryData, lang: Lang, width: number, names: Record<string, string>, last = 40) {
  const col = themeColors();
  const periods = c.periods.slice(-last);
  const data = COMPONENTS.flatMap((m) =>
    points(c, m).filter((p) => periods.includes(p.period)).map((p) => ({ ...p, component: names[m] })),
  );
  return Plot.plot({
    ...base(width),
    x: xAxis(periods, lang, width < 560 ? 4 : 2),
    y: yAxis(lang),
    color: { domain: COMPONENTS.map((m) => names[m]), range: col.series },
    marks: [
      // 1px surface stroke on each segment = 2px surface gap between stacked parts
      Plot.barY(data, Plot.stackY({ x: "period", y: "value", fill: "component", stroke: col.surface, strokeWidth: 1, order: COMPONENTS.map((m) => names[m]) })),
      Plot.ruleY([0], { stroke: col.axis }),
      Plot.tip(data, Plot.pointerX(Plot.stackY({
        x: "period", y: "value", fill: "component", order: COMPONENTS.map((m) => names[m]),
        title: (d: Point & { component: string }) => `${quarter(d.period, lang)}\n${d.component}: ${num(d.value, lang)}`,
      }))),
    ],
  });
}

export function sidesChart(c: CountryData, lang: Lang, width: number, names: { liabilities: string; assets: string }, last = 40) {
  const col = themeColors();
  const periods = c.periods.slice(-last);
  const keep = (p: Point) => periods.includes(p.period);
  const sum = (side: "assets" | "liabilities") => {
    // Gross sides of the financial account excl. reserves: FDI + portfolio + other investment.
    const parts = ["fdi", "portfolio", "other_inv"].map((m) => c.series[m]?.[side] ?? []);
    const vals = c.periods.map((_, i) => (parts.every((p) => p[i] !== null && p[i] !== undefined) ? parts.reduce((a, p) => a + (p[i] as number), 0) : null));
    const out: Point[] = [];
    for (let i = 3; i < c.periods.length; i++) {
      const w = vals.slice(i - 3, i + 1);
      if (w.every((v) => v !== null)) out.push({ period: c.periods[i], value: (w as number[]).reduce((a, b) => a + b, 0) / 4 });
    }
    return out.filter(keep);
  };
  // In the site's sign, assets are negative (outflow); plot magnitudes of purchases instead.
  const liab = sum("liabilities").map((p) => ({ ...p, series: names.liabilities }));
  const assets = sum("assets").map((p) => ({ ...p, value: -p.value, series: names.assets }));
  const data = [...liab, ...assets];
  return {
    data,
    plot: Plot.plot({
      ...base(width),
      x: xAxis(periods, lang, width < 560 ? 4 : 2),
      y: yAxis(lang),
      color: { domain: [names.liabilities, names.assets], range: [col.inflow, col.outflow] },
      marks: [
        Plot.ruleY([0], { stroke: col.axis }),
        Plot.lineY(data, { x: "period", y: "value", stroke: "series", strokeWidth: 2, curve: "monotone-x" }),
        Plot.dot(data.filter((d) => d.period === periods[periods.length - 1]), { x: "period", y: "value", fill: "series", r: 4, stroke: col.surface, strokeWidth: 2 }),
        Plot.tip(data, Plot.pointerX({ x: "period", y: "value", stroke: "series", title: (d: Point & { series: string }) => `${quarter(d.period, lang)}\n${d.series}: ${num(d.value, lang)}` })),
      ],
    }),
  };
}


// ---------------------------------------------------------------- episodes (phase 3)

/** Middle of a quarter as a UTC date, for a continuous time axis. */
export const qDate = (p: string) => {
  const y = Number(p.slice(0, 4));
  const q = Number(p.slice(-1));
  return new Date(Date.UTC(y, (q - 1) * 3 + 1, 15));
};

export interface EpisodeRow { period: string; date: Date; dC: number | null; lo1: number | null; hi1: number | null; lo2: number | null; hi2: number | null }

export function episodeRows(s: EpisodeSeries): EpisodeRow[] {
  return s.periods.map((p, i) => {
    const mu = s.mu[i];
    const sd = s.sd[i];
    const band = (k: number) => (mu === null || sd === null ? null : mu + k * sd);
    return { period: p, date: qDate(p), dC: s.dC[i], lo1: band(-1), hi1: band(1), lo2: band(-2), hi2: band(2) };
  });
}

export function episodeChart(
  s: EpisodeSeries, lang: Lang, width: number, stroke: "inflow" | "outflow",
  typeName: Record<string, string>, label: string,
) {
  const col = themeColors();
  const rows = episodeRows(s);
  const banded = rows.filter((r) => r.lo2 !== null);
  const line = rows.filter((r) => r.dC !== null);
  const first = rows[0]?.period;
  const eps = s.episodes
    .filter((e) => first && e.end >= first)
    .map((e) => ({
      ...e,
      x1: new Date(qDate(e.start < first! ? first! : e.start).getTime() - 45 * 864e5),
      x2: new Date(qDate(e.end).getTime() + 45 * 864e5),
      name: typeName[e.type],
    }));
  const ys = rows.flatMap((r) => [r.dC, r.lo2, r.hi2]).filter((v): v is number => v !== null);
  const [ymin, ymax] = [Math.min(0, ...ys), Math.max(0, ...ys)];
  return Plot.plot({
    ...base(width),
    height: width < 560 ? 220 : 260,
    x: { type: "utc", label: null, tickSize: 0, ticks: width < 560 ? 5 : 10 },
    y: yAxis(lang),
    marks: [
      Plot.rect(eps, { x1: "x1", x2: "x2", y1: () => ymin, y2: () => ymax, fill: col.ink, fillOpacity: 0.08 }),
      Plot.areaY(banded, { x: "date", y1: "lo2", y2: "hi2", fill: col.grid, fillOpacity: 0.6 }),
      Plot.areaY(banded, { x: "date", y1: "lo1", y2: "hi1", fill: col.axis, fillOpacity: 0.45 }),
      Plot.ruleY([0], { stroke: col.axis }),
      Plot.lineY(line, { x: "date", y: "dC", stroke: col[stroke], strokeWidth: 2 }),
      Plot.tip(line, Plot.pointerX({
        x: "date", y: "dC",
        title: (r: EpisodeRow) => {
          const e = eps.find((x) => x.start <= r.period && r.period <= x.end);
          return `${quarter(r.period, lang)}\n${label}: ${num(r.dC, lang)}` +
            (r.lo2 !== null ? `\n±2 sd: ${num(r.lo2, lang)} – ${num(r.hi2, lang)}` : "") +
            (e ? `\n${e.name}` : "");
        },
      })),
    ],
  });
}
