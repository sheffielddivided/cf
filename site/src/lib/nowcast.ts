import { nowcastChart } from "./nowcast-chart";
import { onThemeChange } from "./colors";
import { t } from "./i18n";
import type { Lang, Nowcast } from "./types";

export function initNowcast(root: HTMLElement): void {
  const lang = (root.dataset.lang ?? "nb") as Lang;
  const d = t[lang];
  const data = JSON.parse(document.getElementById("nowcast-data")!.textContent!) as Nowcast;
  const panels = [...root.querySelectorAll<HTMLElement>("section[data-source]")];

  function render() {
    for (const panel of panels) {
      const s = data.sources[panel.dataset.source!];
      const chart = panel.querySelector<HTMLElement>(".nowcast-chart")!;
      if (!s || chart.hidden) continue;
      const svg = nowcastChart(s, lang, chart.clientWidth || 900, panel.dataset.unit!, Number(panel.dataset.avg));
      svg.querySelectorAll("[aria-label]").forEach((e) => e.removeAttribute("aria-label"));
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", chart.dataset.name ?? "");
      chart.replaceChildren(svg);
    }
  }
  for (const panel of panels) {
    const btn = panel.querySelector<HTMLButtonElement>("[data-toggle]")!;
    btn.setAttribute("aria-pressed", "false");
    btn.addEventListener("click", () => {
      const chart = panel.querySelector<HTMLElement>(".nowcast-chart")!;
      const table = panel.querySelector<HTMLElement>(".nowcast-table")!;
      const showTable = table.hidden;
      table.hidden = !showTable;
      chart.hidden = showTable;
      panel.querySelector<HTMLElement>(".legend")!.hidden = showTable;
      btn.setAttribute("aria-pressed", String(showTable));
      btn.textContent = showTable ? d.showChart : d.showTable;
      render();
    });
  }
  onThemeChange(render);
  let w = root.clientWidth;
  new ResizeObserver(() => {
    if (Math.abs(root.clientWidth - w) > 4) { w = root.clientWidth; render(); }
  }).observe(root);
  render();
}
