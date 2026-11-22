// Nowcast charts: net inflow per period as bars (blue/orange) with a moving-average line.
import * as Plot from "@observablehq/plot";
import { themeColors } from "./colors";
import { num } from "./format";
import type { Lang, NowcastSource } from "./types";

export interface NPoint { period: string; value: number }

const MONTHS = {
  nb: ["jan.", "feb.", "mars", "apr.", "mai", "juni", "juli", "aug.", "sep.", "okt.", "nov.", "des."],
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
};

/** "2026-09" -> "sep. 2026"; "2026-11-14" -> "uke t.o.m. 14. nov. 2026". */
export function periodLabel(p: string, lang: Lang): string {
  const [y, m, d] = p.split("-").map(Number);
  const mon = MONTHS[lang][m - 1];
  if (d === undefined) return `${mon} ${y}`;
  return lang === "nb" ? `uke t.o.m. ${d}. ${mon} ${y}` : `week to ${d} ${mon} ${y}`;
}

export function movingAverage(s: NowcastSource, n: number): NPoint[] {
  const out: NPoint[] = [];
  for (let i = n - 1; i < s.periods.length; i++) {
    const w = s.net.slice(i - n + 1, i + 1);
    if (w.every((v) => v !== null)) out.push({ period: s.periods[i], value: (w as number[]).reduce((a, b) => a + b, 0) / n });
  }
  return out;
}

export function nowcastChart(s: NowcastSource, lang: Lang, width: number, unitLabel: string, avgN: number) {
  const c = themeColors();
  const data = s.periods.flatMap((p, i) => (s.net[i] === null ? [] : [{ period: p, value: s.net[i] as number }]));
  const ma = movingAverage(s, avgN);
  const firstOfYear = new Set(
    s.periods.filter((p, i) => i > 0 && p.slice(0, 4) !== s.periods[i - 1].slice(0, 4)),
  );
  return Plot.plot({
    width,
    height: width < 560 ? 220 : 260,
    marginLeft: 56,
    marginRight: 8,
    marginTop: 20,
    style: { fontSize: "12px", fontFamily: "var(--font)", background: "transparent", color: "var(--ink-2)", overflow: "visible" },
    x: {
      type: "band", domain: s.periods, label: null, tickSize: 0, padding: 0.2,
      tickFormat: (p: string) => (firstOfYear.has(p) ? p.slice(0, 4) : ""),
    },
    y: {
      label: unitLabel, grid: true, labelArrow: "none",
      tickFormat: (v: number) => new Intl.NumberFormat(lang === "nb" ? "nb-NO" : "en-GB").format(v),
    },
    marks: [
      Plot.barY(data, { x: "period", y: "value", fill: (d: NPoint) => (d.value >= 0 ? c.inflow : c.outflow), rx: 1.5 }),
      Plot.ruleY([0], { stroke: c.axis }),
      Plot.lineY(ma, { x: "period", y: "value", stroke: c.ink, strokeWidth: 2, curve: "monotone-x" }),
      Plot.tip(data, Plot.pointerX({
        x: "period", y: "value",
        title: (d: NPoint) => {
          const avg = ma.find((m) => m.period === d.period);
          return `${periodLabel(d.period, lang)}\n${num(d.value, lang)} ${unitLabel}` + (avg ? `\n${lang === "nb" ? "Snitt" : "Average"}: ${num(avg.value, lang)}` : "");
        },
      })),
    ],
  });
}
