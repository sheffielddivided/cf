// Client script for "Who owns what": country selector and the BIS position chart.
import * as Plot from "@observablehq/plot";
import { onThemeChange, themeColors } from "./colors";
import { amount, positionPeriod } from "./holdings";
import { t } from "./i18n";
import type { HoldingsCountry, Lang } from "./types";

type Bis = NonNullable<HoldingsCountry["bis"]>;
interface Row { period: string; value: number; series: string }

export function bisRows(b: Bis, labels: { claims: string; liabilities: string }): Row[] {
  const out: Row[] = [];
  b.periods.forEach((p, i) => {
    // missing stays missing (a gap in the line), never zero
    if (b.claims[i] !== null) out.push({ period: p, value: b.claims[i] as number, series: labels.claims });
    if (b.liabilities[i] !== null) out.push({ period: p, value: b.liabilities[i] as number, series: labels.liabilities });
  });
  return out;
}

function bisChart(b: Bis, lang: Lang, width: number, labels: { claims: string; liabilities: string }) {
  const col = themeColors();
  const data = bisRows(b, labels);
  const last = b.periods[b.periods.length - 1];
  return Plot.plot({
    width,
    height: width < 560 ? 220 : 260,
    marginLeft: 56,
    marginRight: width < 560 ? 8 : 120,
    marginTop: 20,
    style: { fontSize: "12px", fontFamily: "var(--font)", background: "transparent", color: "var(--ink-2)", overflow: "visible" },
    x: {
      type: "point", domain: b.periods, label: null, tickSize: 0,
      tickFormat: (p: string) => (p.endsWith("Q4") ? p.slice(0, 4) : ""),
    },
    // stocks: the axis starts at zero
    y: {
      label: lang === "nb" ? "mrd. USD" : "USD bn", grid: true, zero: true, labelArrow: "none",
      tickFormat: (v: number) => new Intl.NumberFormat(lang === "nb" ? "nb-NO" : "en-GB").format(v),
    },
    color: { domain: [labels.claims, labels.liabilities], range: [col.series[4], col.series[0]] },
    marks: [
      Plot.ruleY([0], { stroke: col.axis }),
      Plot.lineY(data, { x: "period", y: "value", stroke: "series", strokeWidth: 2 }),
      Plot.dot(data.filter((d) => d.period === last), { x: "period", y: "value", fill: "series", r: 4, stroke: col.surface, strokeWidth: 2 }),
      ...(width < 560 ? [] : [Plot.text(data.filter((d) => d.period === last), {
        x: "period", y: "value", text: (d: Row) => `${d.series.split(" ")[0]} ${amount(d.value, lang)}`,
        dx: 8, textAnchor: "start", fill: col.ink2,
      })]),
      Plot.tip(data, Plot.pointerX({
        x: "period", y: "value", stroke: "series",
        title: (d: Row) => `${positionPeriod(d.period, lang)}\n${d.series}: ${amount(d.value, lang)}`,
      })),
    ],
  });
}

export function initHoldings(root: HTMLElement): void {
  const lang = (root.dataset.lang ?? "nb") as Lang;
  const d = t[lang];
  const { bis, labels } = JSON.parse(document.getElementById("holdings-data")!.textContent!) as {
    bis: Record<string, Bis>; labels: { claims: string; liabilities: string };
  };
  const select = root.querySelector<HTMLSelectElement>("#holdings-country")!;
  const showTable: Record<string, boolean> = {};

  const fromHash = location.hash.slice(1).toUpperCase();
  if (fromHash && [...select.options].some((o) => o.value === fromHash)) select.value = fromHash;

  function render() {
    const c = select.value;
    root.querySelectorAll<HTMLElement>(".holdings-country").forEach((el) => { el.hidden = el.dataset.country !== c; });
    const box = root.querySelector<HTMLElement>(`[data-bis="${c}"]`);
    if (!box || !bis[c]) return;
    const chart = box.querySelector<HTMLElement>(".bis-chart")!;
    const table = box.querySelector<HTMLElement>(".bis-table")!;
    chart.hidden = !!showTable[c];
    table.hidden = !showTable[c];
    if (showTable[c]) return;
    const svg = bisChart(bis[c], lang, chart.clientWidth || 800, labels);
    svg.querySelectorAll("[aria-label]").forEach((e) => e.removeAttribute("aria-label"));
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", chart.dataset.name ?? "");
    chart.replaceChildren(svg);
  }

  select.addEventListener("change", () => {
    history.replaceState(null, "", `#${select.value.toLowerCase()}`);
    render();
  });
  root.querySelectorAll<HTMLButtonElement>("[data-toggle]").forEach((b) => {
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => {
      const c = select.value;
      showTable[c] = !showTable[c];
      b.setAttribute("aria-pressed", String(showTable[c]));
      b.textContent = showTable[c] ? d.showChart : d.showTable;
      render();
    });
  });
  onThemeChange(render);
  let w = root.clientWidth;
  new ResizeObserver(() => {
    if (Math.abs(root.clientWidth - w) > 4) { w = root.clientWidth; render(); }
  }).observe(root);
  render();
}
