// Choropleth of the ranking values: diverging orange – gray – blue around zero, no arrows.
// Countries outside the selection are drawn as quiet land; selected countries without data
// are hatched gray ("not reported"). Aggregates (euro area) are not drawn.
import { geoEqualEarth, geoPath, interpolateLab, piecewise, scaleDiverging } from "d3";
import { feature } from "topojson-client";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { GeometryCollection, Topology } from "topojson-specification";
import type { Bar } from "./ranking";
import type { Lang, MetaCountry } from "./types";
import { countryName, t } from "./i18n";
import { num, pct, usd } from "./format";
import { themeColors } from "./colors";
import { esc, hideTip, showTip, showTipAt } from "./tooltip";

const SVG = "http://www.w3.org/2000/svg";
const n = <K extends keyof SVGElementTagNameMap>(tag: K, a: Record<string, string | number>) => {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(a)) e.setAttribute(k, String(v));
  return e;
};

let world: Promise<FeatureCollection> | null = null;
export function loadWorld(url: string): Promise<FeatureCollection> {
  world ??= fetch(url)
    .then((r) => r.json() as Promise<Topology>)
    .then((topo) => {
      const fc = feature(topo, topo.objects.countries as GeometryCollection) as FeatureCollection;
      fc.features = fc.features.filter((f) => f.id !== "010"); // drop Antarctica
      return fc;
    });
  return world;
}

const NICE = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];

/** Symmetric color limit: the smallest clean number (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8 × 10ⁿ)
 *  that covers the largest |value|, so the strongest country gets the deepest color. */
export function mapLimit(values: number[]): number {
  const m = Math.max(1e-9, ...values.map(Math.abs));
  const mag = 10 ** Math.floor(Math.log10(m));
  return (NICE.find((s) => s * mag >= m) ?? 10) * mag;
}

export async function renderMap(
  container: HTMLElement,
  legend: HTMLElement,
  o: {
    geoUrl: string;
    bars: Bar[];
    countries: Map<string, MetaCountry>;
    lang: Lang;
    unit: "usd" | "pct";
    href: (iso: string) => string;
    title: string;
  },
): Promise<void> {
  const d = t[o.lang];
  const fc = await loadWorld(o.geoUrl);
  const c = themeColors();
  const byNum = new Map<string, Bar>();
  for (const b of o.bars) {
    const num3 = o.countries.get(b.country)?.iso_num;
    if (num3) byNum.set(num3, b);
  }
  const vals = o.bars.filter((b) => b.value !== null).map((b) => b.value as number);
  const limit = mapLimit(vals);
  const color = scaleDiverging(piecewise(interpolateLab, [c.outflowDeep, c.outflow, c.mid, c.inflow, c.inflowDeep]))
    .domain([-limit, 0, limit]);

  const width = Math.max(320, container.clientWidth);
  const height = Math.round(width * 0.5);
  const projection = geoEqualEarth().fitSize([width, height], fc);
  const path = geoPath(projection);
  const svg = n("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "group", "aria-label": o.title, style: "display:block;max-width:100%" });
  const defs = n("defs", {});
  const hatch = n("pattern", { id: "map-missing", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
  hatch.append(n("rect", { width: 6, height: 6, fill: c.grid }), n("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: c.axis, "stroke-width": 2 }));
  defs.append(hatch);
  svg.append(defs);

  const land = n("g", { "aria-hidden": "true" });
  const selected = n("g", {});
  for (const f of fc.features as Feature<Geometry>[]) {
    const b = byNum.get(String(f.id));
    const dAttr = path(f) ?? "";
    if (!b) {
      land.append(n("path", { d: dAttr, fill: c.grid, stroke: c.surface, "stroke-width": 0.5 }));
      continue;
    }
    const meta = o.countries.get(b.country);
    const name = meta ? countryName(meta, o.lang) : b.country;
    const valueText = b.value === null ? d.notReported : o.unit === "usd" ? usd(b.value, o.lang) : pct(b.value, o.lang);
    const a = n("a", { href: o.href(b.country), "aria-label": `${name} ${valueText}` });
    a.append(n("path", {
      d: dAttr, fill: b.value === null ? "url(#map-missing)" : color(b.value),
      stroke: c.surface, "stroke-width": 0.75, class: "map-country",
    }));
    const html = () =>
      `<strong>${esc(name)}</strong>` +
      (b.value === null
        ? `<div>${esc(d.notReported)}</div>`
        : `<div class="tip-row"><span>${esc(o.lang === "nb" ? "Mrd. USD" : "USD bn")}</span><span>${num(b.usd, o.lang)}</span></div>` +
          `<div class="tip-row"><span>${esc(d.unitPct)}</span><span>${num(b.pct, o.lang)}</span></div>`);
    a.addEventListener("pointermove", (e) => showTip(html(), (e as PointerEvent).clientX, (e as PointerEvent).clientY));
    a.addEventListener("pointerleave", hideTip);
    a.addEventListener("focus", () => showTipAt(html(), a));
    a.addEventListener("blur", hideTip);
    selected.append(a);
  }
  svg.append(land, selected);
  container.replaceChildren(svg);

  // legend: gradient, plus "not reported" and "not in selection"
  const lw = 220;
  const lsvg = n("svg", { width: lw + 300, height: 34, "aria-hidden": "true", style: "display:block;max-width:100%;font:11px var(--font)" });
  const ldefs = n("defs", {});
  const grad = n("linearGradient", { id: "map-grad" });
  for (let k = 0; k <= 10; k++) grad.append(n("stop", { offset: `${k * 10}%`, "stop-color": color(-limit + (2 * limit * k) / 10) }));
  ldefs.append(grad, hatch.cloneNode(true) as Element);
  (ldefs.lastChild as Element).setAttribute("id", "map-missing-legend");
  lsvg.append(ldefs, n("rect", { x: 0, y: 2, width: lw, height: 10, rx: 2, fill: "url(#map-grad)" }));
  const unitSuffix = o.unit === "pct" ? " %" : "";
  for (const [v, anchor] of [[-limit, "start"], [0, "middle"], [limit, "end"]] as const) {
    const tx = n("text", { x: ((v + limit) / (2 * limit)) * lw, y: 26, "text-anchor": anchor, fill: "var(--ink-2)" });
    tx.textContent = v === 0 ? "0" : `${num(v, o.lang, 0)}${unitSuffix}`;
    lsvg.append(tx);
  }
  const key = (x: number, fill: string, label: string) => {
    lsvg.append(n("rect", { x, y: 2, width: 10, height: 10, rx: 2, fill }));
    const tx = n("text", { x: x + 16, y: 11, fill: "var(--ink-2)" });
    tx.textContent = label;
    lsvg.append(tx);
  };
  key(lw + 20, "url(#map-missing-legend)", d.notReported);
  key(lw + 130, c.grid, o.lang === "nb" ? "ikke i utvalget" : "not in selection");
  legend.replaceChildren(lsvg);
}
