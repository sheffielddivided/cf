// Diverging horizontal bar chart for the ranking (hand-built SVG: one zero baseline,
// 4px rounded data-ends, value at the tip, a labelled row for missing data).
import { scaleLinear } from "d3";
import type { Bar } from "./ranking";
import type { Lang, MetaCountry } from "./types";
import { num, pct, quarter, usd } from "./format";
import { countryName, t } from "./i18n";
import { esc, hideTip, showTip, showTipAt } from "./tooltip";

const SVG = "http://www.w3.org/2000/svg";
const ROW = 28;
const BAR = 16;
const TOP = 26;

function node<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>) {
  const n = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
  return n;
}

/** A bar with a 4px rounded data-end and a square baseline end. */
export function barPath(x0: number, x1: number, y: number, h: number, r = 4): string {
  const w = Math.abs(x1 - x0);
  const rr = Math.min(r, w / 2, h / 2);
  if (x1 >= x0) {
    return `M${x0},${y}H${x1 - rr}Q${x1},${y} ${x1},${y + rr}V${y + h - rr}Q${x1},${y + h} ${x1 - rr},${y + h}H${x0}Z`;
  }
  return `M${x0},${y}H${x1 + rr}Q${x1},${y} ${x1},${y + rr}V${y + h - rr}Q${x1},${y + h} ${x1 + rr},${y + h}H${x0}Z`;
}

export interface RankingChartOptions {
  bars: Bar[];
  countries: Map<string, MetaCountry>;
  lang: Lang;
  unit: "usd" | "pct";
  href: (iso: string) => string;
  title: string;
}

export function renderRanking(container: HTMLElement, o: RankingChartOptions): void {
  const d = t[o.lang];
  const width = Math.max(320, container.clientWidth);
  const narrow = width < 560;
  const labelW = narrow ? 112 : 150;
  const valW = narrow ? 52 : 64;
  const height = TOP + o.bars.length * ROW + 8;
  const present = o.bars.filter((b) => b.value !== null).map((b) => b.value as number);
  const lo = Math.min(0, ...present);
  const hi = Math.max(0, ...present);
  const x = scaleLinear()
    .domain([lo, hi])
    .range([labelW + (lo < 0 ? valW : 8), width - (hi > 0 ? valW : 8)])
    .nice();
  const x0 = x(0);

  const svg = node("svg", {
    width,
    height,
    viewBox: `0 0 ${width} ${height}`,
    role: "group",
    "aria-label": o.title,
    style: "display:block;max-width:100%;font:13px var(--font)",
  });

  // gridlines + ticks (recessive hairlines)
  const ticks = x.ticks(Math.max(2, Math.floor((x.range()[1] - x.range()[0]) / 70)));
  const grid = node("g", { "aria-hidden": "true" });
  for (const tv of ticks) {
    const tx = Math.round(x(tv)) + 0.5;
    grid.append(node("line", { x1: tx, x2: tx, y1: TOP - 6, y2: height - 6, stroke: tv === 0 ? "var(--axis)" : "var(--grid)" }));
    const label = node("text", {
      x: tx, y: TOP - 12, "text-anchor": "middle", fill: "var(--ink-2)",
      style: "font-size:11px;font-variant-numeric:tabular-nums",
    });
    label.textContent = new Intl.NumberFormat(o.lang === "nb" ? "nb-NO" : "en-GB", { maximumFractionDigits: 0 }).format(tv);
    grid.append(label);
  }
  svg.append(grid);

  o.bars.forEach((b, i) => {
    const c = o.countries.get(b.country);
    const name = c ? countryName(c, o.lang) : b.country;
    const y = TOP + i * ROW;
    const a = node("a", { href: o.href(b.country) });
    const shown = name + (b.status === "derived" ? " †" : "");
    const valueText = b.value === null ? d.notReported : o.unit === "usd" ? usd(b.value, o.lang) : pct(b.value, o.lang);
    a.setAttribute("aria-label", `${shown} ${valueText}${b.status === "derived" ? ` (${d.derivedMark})` : ""}`);

    a.append(node("rect", { x: 0, y, width, height: ROW, fill: "transparent", class: "row-hit" }));
    const label = node("text", {
      x: labelW - 10, y: y + ROW / 2 + 4.5, "text-anchor": "end", fill: "var(--ink)",
      style: b.aggregate ? "font-style:italic" : "",
    });
    label.textContent = name + (b.status === "derived" ? " †" : "");
    a.append(label);

    if (b.value === null) {
      const roomRight = width - x0 > 110;
      const miss = node("text", {
        x: roomRight ? x0 + 6 : x0 - 6, y: y + ROW / 2 + 4.5, "text-anchor": roomRight ? "start" : "end",
        fill: "var(--ink-2)", style: "font-size:12px;font-style:italic",
      });
      miss.textContent = d.notReported;
      a.append(miss);
    } else {
      const xv = x(b.value);
      const positive = b.value >= 0;
      a.append(node("path", {
        d: barPath(x0, xv, y + (ROW - BAR) / 2, BAR),
        fill: positive ? "var(--inflow)" : "var(--outflow)",
      }));
      const val = node("text", {
        x: positive ? xv + 5 : xv - 5, y: y + ROW / 2 + 4.5, "text-anchor": positive ? "start" : "end",
        fill: "var(--ink)", style: "font-size:12px;font-variant-numeric:tabular-nums",
      });
      val.textContent = num(b.value, o.lang);
      a.append(val);
    }

    const html = () => {
      const lines = [`<strong>${esc(name)}</strong>`];
      if (b.value === null) lines.push(esc(d.notReported));
      else {
        lines.push(`<div class="tip-row"><span>${esc(o.lang === "nb" ? "Mrd. USD" : "USD bn")}</span><span>${num(b.usd, o.lang)}</span></div>`);
        lines.push(`<div class="tip-row"><span>${esc(d.unitPct)}</span><span>${num(b.pct, o.lang)}</span></div>`);
        if (b.period) lines.push(`<div class="muted">${esc(quarter(b.period, o.lang))}</div>`);
        if (b.status === "derived") lines.push(`<div class="muted">† ${esc(d.derivedMark)}</div>`);
      }
      return lines.join("");
    };
    a.addEventListener("pointermove", (e) => showTip(html(), (e as PointerEvent).clientX, (e as PointerEvent).clientY));
    a.addEventListener("pointerleave", hideTip);
    a.addEventListener("focus", () => showTipAt(html(), a));
    a.addEventListener("blur", hideTip);
    svg.append(a);
  });

  container.replaceChildren(svg);
}
