import { countryName, routes, t } from "./i18n";
import { num, quarterShort } from "./format";
import { renderHeatmap, type HeatRow } from "./heatmap-chart";
import { onThemeChange } from "./colors";
import type { Heatmap, Lang, Meta, Ranking } from "./types";
import { esc } from "./tooltip";

type Unit = "usd" | "pct";
type Sel = "all" | "top20";

export function heatmapRows(hm: Heatmap, ranking: Ranking, meta: Meta, unit: Unit, sel: Sel): HeatRow[] {
  const order = new Map<string, number>();
  for (const r of ranking.rows) {
    const v = r.values.fa_ex_reserves?.["4q"]?.[unit];
    order.set(r.country, v ?? Number.NEGATIVE_INFINITY);
  }
  const top = new Set(meta.top20);
  return hm.rows
    .filter((r) => sel === "all" || top.has(r.country))
    .map((r) => ({ country: r.country, values: r[unit] }))
    .sort((a, b) => (order.get(b.country) ?? -Infinity) - (order.get(a.country) ?? -Infinity));
}

export function initHeatmap(root: HTMLElement): void {
  const lang = (root.dataset.lang ?? "nb") as Lang;
  const d = t[lang];
  const { meta, heatmap, ranking } = JSON.parse(document.getElementById("heatmap-data")!.textContent!) as {
    meta: Meta; heatmap: Heatmap; ranking: Ranking;
  };
  const countries = new Map(meta.countries.map((c) => [c.iso3, c]));
  const form = root.querySelector("form")!;
  const chart = root.querySelector<HTMLElement>("#heatmap-chart")!;
  const table = root.querySelector<HTMLElement>("#heatmap-table")!;
  const legend = root.querySelector<HTMLElement>("#heatmap-legend")!;
  const toggle = root.querySelector<HTMLButtonElement>("#table-toggle")!;
  const params = new URLSearchParams(location.search);
  let unit: Unit = params.get("unit") === "usd" ? "usd" : "pct";
  let sel: Sel = params.get("sel") === "top20" ? "top20" : "all";
  let showTable = false;
  (form.elements.namedItem("unit") as HTMLSelectElement).value = unit;
  (form.elements.namedItem("sel") as HTMLSelectElement).value = sel;

  function render() {
    const rows = heatmapRows(heatmap, ranking, meta, unit, sel);
    const title = lang === "nb" ? "Varmekart, netto kapitalstrøm ekskl. reserver" : "Heatmap, net capital flow excl. reserves";
    renderHeatmap(chart, legend, {
      rows, periods: heatmap.periods, countries, lang, unit, href: routes(lang).country, title,
    });
    table.innerHTML = `<table class="data"><thead><tr><th scope="col">${esc(d.country)}</th>${heatmap.periods
      .map((p) => `<th scope="col" class="num">${esc(quarterShort(p, lang))}</th>`)
      .join("")}</tr></thead><tbody>${rows
      .map((r) => {
        const c = countries.get(r.country);
        return `<tr><th scope="row">${esc(c ? countryName(c, lang) : r.country)}</th>${r.values
          .map((v) => `<td class="num">${num(v, lang)}</td>`)
          .join("")}</tr>`;
      })
      .join("")}</tbody></table>`;
    chart.hidden = showTable;
    table.hidden = !showTable;
  }
  form.addEventListener("change", (e) => {
    const el = e.target as HTMLSelectElement;
    if (el.name === "unit") unit = el.value as Unit;
    if (el.name === "sel") sel = el.value as Sel;
    const q = new URLSearchParams();
    if (unit !== "pct") q.set("unit", unit);
    if (sel !== "all") q.set("sel", sel);
    history.replaceState(null, "", `${location.pathname}${q.size ? `?${q}` : ""}`);
    render();
  });
  toggle.addEventListener("click", () => {
    showTable = !showTable;
    toggle.setAttribute("aria-pressed", String(showTable));
    toggle.textContent = showTable ? d.showChart : d.showTable;
    render();
  });
  onThemeChange(render);
  let w = chart.clientWidth;
  new ResizeObserver(() => {
    if (Math.abs(chart.clientWidth - w) > 4) { w = chart.clientWidth; render(); }
  }).observe(chart);
  render();
}
