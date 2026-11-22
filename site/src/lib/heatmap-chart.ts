// Country × quarter heatmap, diverging around zero: orange (outflow) – gray – blue (inflow).
import { interpolateLab, piecewise, quantile, scaleDiverging } from "d3";
import { num, quarter } from "./format";
import { countryName, t } from "./i18n";
import { themeColors } from "./colors";
import { esc, hideTip, showTip } from "./tooltip";
import type { Lang, MetaCountry } from "./types";

const SVG = "http://www.w3.org/2000/svg";
const n = <K extends keyof SVGElementTagNameMap>(tag: K, a: Record<string, string | number>) => {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(a)) e.setAttribute(k, String(v));
  return e;
};

export interface HeatRow {
  country: string;
  values: (number | null)[];
}

/** Symmetric color limit: the 90th percentile of |value|, rounded to a clean number. */
export function colorLimit(rows: HeatRow[]): number {
  const abs = rows.flatMap((r) => r.values.filter((v): v is number => v !== null).map(Math.abs));
  if (!abs.length) return 1;
  const q = quantile(abs.sort((a, b) => a - b), 0.9) ?? 1;
  const mag = 10 ** Math.floor(Math.log10(q));
  return Math.ceil(q / mag) * mag;
}

export function renderHeatmap(
  container: HTMLElement,
  legend: HTMLElement,
  o: {
    rows: HeatRow[];
    periods: string[];
    countries: Map<string, MetaCountry>;
    lang: Lang;
    unit: "usd" | "pct";
    href: (iso: string) => string;
    title: string;
  },
): void {
  const d = t[o.lang];
  const c = themeColors();
  const limit = colorLimit(o.rows);
  const color = scaleDiverging(piecewise(interpolateLab, [c.outflowDeep, c.outflow, c.mid, c.inflow, c.inflowDeep]))
    .domain([-limit, 0, limit])
    .clamp(true);

  const width = Math.max(320, container.clientWidth);
  const labelW = width < 560 ? 104 : 140;
  const cw = Math.max(9, Math.floor((width - labelW - 4) / o.periods.length));
  const rh = 22;
  const top = 22;
  const svgW = labelW + cw * o.periods.length + 4;
  const svgH = top + rh * o.rows.length + 4;
  const svg = n("svg", {
    width: svgW, height: svgH, viewBox: `0 0 ${svgW} ${svgH}`, role: "img", "aria-label": o.title,
    style: "display:block;font:12px var(--font)",
  });

  // year labels at Q1 (every second year when cells are narrow)
  const step = cw < 14 ? 2 : 1;
  o.periods.forEach((p, j) => {
    if (!p.endsWith("Q1") || Number(p.slice(0, 4)) % step) return;
    const tx = n("text", { x: labelW + j * cw, y: top - 8, fill: "var(--ink-2)", style: "font-size:11px" });
    tx.textContent = p.slice(0, 4);
    svg.append(tx);
  });

  o.rows.forEach((row, i) => {
    const meta = o.countries.get(row.country);
    const name = meta ? countryName(meta, o.lang) : row.country;
    const y = top + i * rh;
    const a = n("a", { href: o.href(row.country), "aria-label": name });
    const label = n("text", {
      x: labelW - 8, y: y + rh / 2 + 4, "text-anchor": "end", fill: "var(--ink)",
      style: meta?.aggregate ? "font-style:italic" : "",
    });
    label.textContent = name;
    a.append(label);
    row.values.forEach((v, j) => {
      const x = labelW + j * cw;
      // 1px surface gap on each side = 2px between neighbouring cells
      a.append(n("rect", {
        x: x + 1, y: y + 1, width: cw - 2, height: rh - 2, rx: 2,
        fill: v === null ? "none" : color(v),
        stroke: v === null ? "var(--grid)" : "none",
        "data-i": i, "data-j": j,
      }));
    });
    svg.append(a);
  });
  // one delegated tooltip handler for all cells
  svg.addEventListener("pointermove", (e) => {
    const cell = (e.target as Element).closest("rect[data-i]");
    if (!cell) return hideTip();
    const row = o.rows[Number(cell.getAttribute("data-i"))];
    const j = Number(cell.getAttribute("data-j"));
    const v = row.values[j];
    const meta = o.countries.get(row.country);
    const name = meta ? countryName(meta, o.lang) : row.country;
    const html =
      `<strong>${esc(name)}</strong><div class="muted">${esc(quarter(o.periods[j], o.lang))}</div>` +
      (v === null
        ? esc(d.notReported)
        : `<div class="tip-row"><span>${esc(v >= 0 ? d.inflow : d.outflow)}</span><span>${num(v, o.lang)}${o.unit === "pct" ? " %" : ""}</span></div>`);
    showTip(html, e.clientX, e.clientY);
  });
  svg.addEventListener("pointerleave", hideTip);
  container.replaceChildren(svg);

  // legend: gradient bar with ticks, plus the "not reported" key
  const lw = 220;
  const lsvg = n("svg", { width: lw + 140, height: 34, "aria-hidden": "true", style: "display:block;font:11px var(--font)" });
  const defs = n("defs", {});
  const grad = n("linearGradient", { id: "hm-grad" });
  for (let k = 0; k <= 10; k++) {
    grad.append(n("stop", { offset: `${k * 10}%`, "stop-color": color(-limit + (2 * limit * k) / 10) }));
  }
  defs.append(grad);
  lsvg.append(defs, n("rect", { x: 0, y: 2, width: lw, height: 10, rx: 2, fill: "url(#hm-grad)" }));
  for (const [v, anchor] of [[-limit, "start"], [0, "middle"], [limit, "end"]] as const) {
    const tx = n("text", { x: ((v + limit) / (2 * limit)) * lw, y: 26, "text-anchor": anchor, fill: "var(--ink-2)" });
    tx.textContent = `${v === 0 ? "0" : num(v, o.lang, 0)}${v === limit || v === -limit ? (o.unit === "pct" ? " %" : "") : ""}`;
    lsvg.append(tx);
  }
  lsvg.append(n("rect", { x: lw + 20, y: 2, width: 10, height: 10, rx: 2, fill: "none", stroke: "var(--grid)" }));
  const nr = n("text", { x: lw + 36, y: 11, fill: "var(--ink-2)" });
  nr.textContent = d.notReported;
  lsvg.append(nr);
  legend.replaceChildren(lsvg);
}
