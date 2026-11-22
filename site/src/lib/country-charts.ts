// Country page charts (Observable Plot). Colors are resolved from the theme's CSS variables.
import * as Plot from "@observablehq/plot";
import { themeColors } from "./colors";
import { num, quarter } from "./format";
import type { CountryData, Lang } from "./types";

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

