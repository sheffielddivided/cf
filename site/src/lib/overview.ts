import { countryName, routes, t } from "./i18n";
import { num, quarter, windowLabel } from "./format";
import { rankingBars, windowPeriods } from "./ranking";
import { renderRanking } from "./ranking-chart";
import { renderMap } from "./map-chart";
import { onThemeChange } from "./colors";
import { parseState, serializeState, type ViewState } from "./state";
import type { Lang, Meta, Ranking } from "./types";
import { esc } from "./tooltip";

export function initOverview(root: HTMLElement): void {
  const lang = (root.dataset.lang ?? "nb") as Lang;
  const d = t[lang];
  const { meta, ranking } = JSON.parse(document.getElementById("overview-data")!.textContent!) as {
    meta: Meta;
    ranking: Ranking;
  };
  const countries = new Map(meta.countries.map((c) => [c.iso3, c]));
  const form = root.querySelector("form")!;
  const chart = root.querySelector<HTMLElement>("#ranking-chart")!;
  const table = root.querySelector<HTMLElement>("#ranking-table")!;
  const toggle = root.querySelector<HTMLButtonElement>("#table-toggle")!;
  const title = root.querySelector<HTMLElement>("#ranking-title")!;
  let state = parseState(location.search);
  let showTable = false;

  for (const [k, v] of Object.entries(state)) {
    const sel = form.elements.namedItem(k) as HTMLSelectElement | null;
    if (sel) sel.value = v;
  }

  const typeLabel = (s: ViewState) =>
    ({ total: d.typeTotal, fdi: d.typeFdi, portfolio: d.typePortfolio, other: d.typeOther })[s.type];

  function heading(s: ViewState): string {
    const what =
      s.type === "total"
        ? lang === "nb"
          ? `Netto kapitalstrøm ${s.reserves === "ex" ? "ekskl." : "inkl."} reserver`
          : `Net capital flow ${s.reserves === "ex" ? "excl." : "incl."} reserves`
        : lang === "nb"
          ? `Netto ${typeLabel(s).toLowerCase()}`
          : `Net ${typeLabel(s).toLowerCase()}`;
    const unit = s.unit === "usd" ? d.unitUsd : d.unitPct;
    const when =
      s.period === "latest"
        ? d.periodLatest.toLowerCase()
        : s.period === "year"
          ? `${ranking.reference_year}`
          : windowLabel(windowPeriods(ranking, s), lang);
    return `${what}, ${when} (${unit})`;
  }

  function render(): void {
    const bars = rankingBars(meta, ranking, state);
    const h = heading(state);
    title.textContent = h;
    root.querySelector<HTMLElement>("#latest-hint")!.hidden = state.period !== "latest";
    root.querySelector<HTMLElement>("#reserves-hint")!.hidden = state.type === "total";
    (form.elements.namedItem("reserves") as HTMLSelectElement).disabled = state.type !== "total";
    root.querySelector<HTMLElement>("#fn-derived")!.hidden = !bars.some((b) => b.status === "derived");

    const isMap = state.view === "map";
    if (isMap) {
      // the map leaves out aggregates; bars keep them for the table
      renderMap(root.querySelector<HTMLElement>("#map-chart")!, root.querySelector<HTMLElement>("#map-legend")!, {
        geoUrl: root.dataset.geo!, bars: bars.filter((b) => !b.aggregate), countries, lang,
        unit: state.unit, href: routes(lang).country, title: h,
      }).catch(() => {
        root.querySelector<HTMLElement>("#map-chart")!.textContent = d.notReported;
      });
    } else {
      renderRanking(chart, {
        bars, countries, lang, unit: state.unit, title: h, href: routes(lang).country,
      });
    }

    const periodCol = state.period === "latest";
    table.innerHTML = `<table class="data"><caption class="visually-hidden">${esc(h)}</caption>
      <thead><tr><th scope="col">#</th><th scope="col">${esc(d.country)}</th>
      ${periodCol ? `<th scope="col">${esc(d.periodCol)}</th>` : ""}
      <th scope="col" class="num">${esc(d.unitUsd)}</th><th scope="col" class="num">${esc(d.unitPct)}</th>
      <th scope="col">${esc(d.status)}</th></tr></thead><tbody>${bars
        .map((b, i) => {
          const c = countries.get(b.country);
          const name = c ? countryName(c, lang) : b.country;
          const status = b.value === null ? d.notReported : b.status === "derived" ? `† ${d.derivedMark}` : "";
          return `<tr><td>${b.value === null ? "" : i + 1}</td>
            <td><a href="${routes(lang).country(b.country)}">${esc(name)}</a></td>
            ${periodCol ? `<td>${esc(quarter(b.period, lang))}</td>` : ""}
            <td class="num">${num(b.usd, lang)}</td><td class="num">${num(b.pct, lang)}</td>
            <td>${esc(status)}</td></tr>`;
        })
        .join("")}</tbody></table>`;
    chart.hidden = showTable || isMap;
    table.hidden = !showTable;
    root.querySelector<HTMLElement>("#ranking-legend")!.hidden = showTable || isMap;
    root.querySelector<HTMLElement>("#map-wrap")!.hidden = showTable || !isMap;
    root.querySelector<HTMLElement>("#fn-missing")!.hidden = isMap && !showTable;
  }

  const viewButtons = [...root.querySelectorAll<HTMLButtonElement>(".segmented button[data-view]")];
  const syncButtons = () =>
    viewButtons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === state.view)));

  function update(next: ViewState) {
    state = next;
    history.replaceState(null, "", `${location.pathname}${serializeState(state)}`);
    syncButtons();
    render();
  }

  form.addEventListener("change", (e) => {
    const target = e.target as HTMLSelectElement;
    update({ ...state, [target.name]: target.value } as ViewState);
  });
  for (const b of viewButtons) {
    b.addEventListener("click", () => {
      const view = b.dataset.view as ViewState["view"];
      if (view === state.view) return;
      const next = { ...state, view };
      // switching to the map without having chosen a unit: the map defaults to % of GDP
      if (!location.search.includes("unit=")) {
        next.unit = view === "map" ? "pct" : "usd";
        (form.elements.namedItem("unit") as HTMLSelectElement).value = next.unit;
      }
      update(next);
    });
  }
  syncButtons();
  toggle.addEventListener("click", () => {
    showTable = !showTable;
    toggle.setAttribute("aria-pressed", String(showTable));
    toggle.textContent = showTable ? d.showChart : d.showTable;
    render();
  });
  let w = root.clientWidth;
  new ResizeObserver(() => {
    if (Math.abs(root.clientWidth - w) > 4 && !showTable) {
      w = root.clientWidth;
      render();
    }
  }).observe(root);
  onThemeChange(render);
  render();
}
