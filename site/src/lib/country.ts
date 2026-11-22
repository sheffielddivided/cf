import { componentsChart, COMPONENTS, mainChart, movingAverage, points, sidesChart } from "./country-charts";
import { onThemeChange } from "./colors";
import { num, quarter } from "./format";
import { t } from "./i18n";
import type { CountryData, Lang } from "./types";
import { esc } from "./tooltip";

interface Labels {
  quarterLbl: string; avgLbl: string; liab: string; assets: string; components: Record<string, string>;
}

/** Plot labels inner <g> elements; make the chart one image named by its figure instead. */
function asImage(svg: Element, name: string): Element {
  svg.querySelectorAll("[aria-label]").forEach((e) => e.removeAttribute("aria-label"));
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", name);
  return svg;
}

function table(head: string[], rows: (string | number | null)[][], lang: Lang): string {
  return `<table class="data"><thead><tr>${head
    .map((h, i) => `<th scope="col"${i ? ' class="num"' : ""}>${esc(h)}</th>`)
    .join("")}</tr></thead><tbody>${rows
    .map((r) => `<tr><th scope="row">${esc(String(r[0]))}</th>${r
      .slice(1)
      .map((v) => `<td class="num">${typeof v === "number" || v === null ? num(v as number | null, lang) : esc(v)}</td>`)
      .join("")}</tr>`)
    .join("")}</tbody></table>`;
}

export function initCountry(root: HTMLElement): void {
  const lang = (root.dataset.lang ?? "nb") as Lang;
  const d = t[lang];
  const { data, labels } = JSON.parse(document.getElementById("country-data")!.textContent!) as {
    data: CountryData; labels: Labels;
  };
  const el = (id: string) => root.querySelector<HTMLElement>(`#${id}`)!;
  const showTable: Record<string, boolean> = { main: false, comp: false, sides: false };

  function render() {
    const w = el("chart-main").clientWidth || 900;
    if (data.periods.length === 0) {
      el("chart-main").textContent = d.notReported;
      return;
    }
    const name = (id: string) => el(id).dataset.name ?? "";
    el("chart-main").replaceChildren(asImage(mainChart(data, lang, w, labels), name("chart-main")));
    el("chart-comp").replaceChildren(asImage(componentsChart(data, lang, w, labels.components), name("chart-comp")));
    const sides = sidesChart(data, lang, w, { liabilities: labels.liab, assets: labels.assets });
    el("chart-sides").replaceChildren(asImage(sides.plot, name("chart-sides")));

    // table views (newest first)
    const ma = new Map(movingAverage(data, "fa_ex_reserves").map((p) => [p.period, p.value]));
    const main = points(data, "fa_ex_reserves").reverse();
    el("table-main").innerHTML = table(
      [d.periodCol, labels.quarterLbl, labels.avgLbl],
      main.map((p) => [quarter(p.period, lang) + (data.derived_periods.includes(p.period) ? " †" : ""), p.value, ma.get(p.period) ?? null]),
      lang,
    );
    const last = data.periods.slice(-40).reverse();
    const comp = Object.fromEntries(COMPONENTS.map((m) => [m, new Map(points(data, m).map((p) => [p.period, p.value]))]));
    el("table-comp").innerHTML = table(
      [d.periodCol, ...COMPONENTS.map((m) => labels.components[m])],
      last.map((p) => [quarter(p, lang), ...COMPONENTS.map((m) => comp[m].get(p) ?? null)]),
      lang,
    );
    const byP = new Map<string, { l?: number; a?: number }>();
    for (const r of sides.data) {
      const e = byP.get(r.period) ?? {};
      if (r.series === labels.liab) e.l = r.value; else e.a = r.value;
      byP.set(r.period, e);
    }
    el("table-sides").innerHTML = table(
      [d.periodCol, labels.liab, labels.assets],
      [...byP.entries()].reverse().map(([p, v]) => [quarter(p, lang), v.l ?? null, v.a ?? null]),
      lang,
    );
    for (const k of Object.keys(showTable)) {
      el(`chart-${k}`).hidden = showTable[k];
      el(`table-${k}`).hidden = !showTable[k];
    }
  }

  root.querySelectorAll<HTMLButtonElement>("button[data-table]").forEach((b) => {
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => {
      const k = b.dataset.table!;
      showTable[k] = !showTable[k];
      b.setAttribute("aria-pressed", String(showTable[k]));
      b.textContent = showTable[k] ? d.showChart : d.showTable;
      render();
    });
  });
  onThemeChange(render);
  let w = el("chart-main").clientWidth;
  new ResizeObserver(() => {
    const nw = el("chart-main").clientWidth;
    if (Math.abs(nw - w) > 4) { w = nw; render(); }
  }).observe(root);
  render();
}
