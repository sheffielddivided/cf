import type { Lang } from "./types";

const BASE = import.meta.env.BASE_URL.replace(/\/$/, ""); // "/cf"

export const routes = (lang: Lang) =>
  lang === "nb"
    ? {
        home: `${BASE}/`,
        heatmap: `${BASE}/varmekart/`,
        method: `${BASE}/metode/`,
        country: (iso: string) => `${BASE}/land/${iso}/`,
      }
    : {
        home: `${BASE}/en/`,
        heatmap: `${BASE}/en/heatmap/`,
        method: `${BASE}/en/method/`,
        country: (iso: string) => `${BASE}/en/country/${iso}/`,
      };

/** The same page in the other language. */
export function alternate(lang: Lang, page: "home" | "heatmap" | "method" | { country: string }) {
  const other: Lang = lang === "nb" ? "en" : "nb";
  const r = routes(other);
  return typeof page === "string" ? r[page] : r.country(page.country);
}

export const dataUrl = (file: string) => `${BASE}/data/${file}`;

export const t = {
  nb: {
    siteTitle: "Kapitalstrømmer",
    siteTagline: "Netto kapitalstrømmer inn og ut av verdens største økonomier",
    navOverview: "Oversikt",
    navHeatmap: "Varmekart",
    navMethod: "Metode",
    otherLang: "English",
    skip: "Hopp til innhold",
    // controls
    period: "Periode",
    periodQ: "Siste felles kvartal",
    period4q: "Siste fire kvartaler",
    periodYear: "Kalenderår",
    periodLatest: "Nyeste per land",
    unit: "Enhet",
    unitUsd: "Mrd. USD",
    unitPct: "% av BNP",
    type: "Kapitaltype",
    typeTotal: "Samlet",
    typeFdi: "Direkteinvesteringer",
    typePortfolio: "Portefølje",
    typeOther: "Annen investering",
    reserves: "Reserver",
    reservesEx: "Ekskludert",
    reservesIn: "Inkludert",
    selection: "Utvalg",
    selTop20: "Topp 20",
    selAll: "Topp 20 + Norge og euroområdet",
    showTable: "Vis som tabell",
    showChart: "Vis som graf",
    inflow: "Netto innstrømning",
    outflow: "Netto utstrømning",
    notReported: "ikke rapportert",
    derivedMark: "beregnet",
    aggregate: "aggregat",
    lessComparable: "Mindre sammenlignbart: hvert land vises med sin nyeste periode.",
    reservesOnlyTotal: "Gjelder bare «Samlet».",
    // statusline
    dataThrough: "Data til og med",
    updated: "oppdatert",
    source: "Kilde",
    readMethod: "Slik er tallene laget",
    // table
    country: "Land",
    value: "Verdi",
    periodCol: "Periode",
    status: "Status",
    // misc
    rankingTitle: (what: string, when: string) => `${what}, ${when}`,
    footnoteDerived:
      "† Beregnet som finansregnskapet minus reserver, fordi IMF ikke publiserer tallet uten reserver for denne perioden.",
    footnoteMissing: "Land uten data for perioden vises nederst og er ikke satt til null.",
    footerData:
      "Data: IMF Balance of Payments og World Economic Outlook, gjengitt etter IMFs vilkår. Kode: MIT-lisens.",
    footerRepo: "Kildekode og data på GitHub",
  },
  en: {
    siteTitle: "Capital flows",
    siteTagline: "Net capital flows into and out of the world’s largest economies",
    navOverview: "Overview",
    navHeatmap: "Heatmap",
    navMethod: "Method",
    otherLang: "Norsk",
    skip: "Skip to content",
    period: "Period",
    periodQ: "Latest common quarter",
    period4q: "Last four quarters",
    periodYear: "Calendar year",
    periodLatest: "Latest per country",
    unit: "Unit",
    unitUsd: "USD bn",
    unitPct: "% of GDP",
    type: "Capital type",
    typeTotal: "Total",
    typeFdi: "Direct investment",
    typePortfolio: "Portfolio",
    typeOther: "Other investment",
    reserves: "Reserves",
    reservesEx: "Excluded",
    reservesIn: "Included",
    selection: "Selection",
    selTop20: "Top 20",
    selAll: "Top 20 + Norway and euro area",
    showTable: "Show as table",
    showChart: "Show as chart",
    inflow: "Net inflow",
    outflow: "Net outflow",
    notReported: "not reported",
    derivedMark: "derived",
    aggregate: "aggregate",
    lessComparable: "Less comparable: each country is shown with its own latest period.",
    reservesOnlyTotal: "Applies to “Total” only.",
    dataThrough: "Data through",
    updated: "updated",
    source: "Source",
    readMethod: "How the numbers are made",
    country: "Country",
    value: "Value",
    periodCol: "Period",
    status: "Status",
    rankingTitle: (what: string, when: string) => `${what}, ${when}`,
    footnoteDerived:
      "† Derived as the financial account minus reserves, because the IMF does not publish the figure excluding reserves for this period.",
    footnoteMissing: "Countries without data for the period are listed last and are not set to zero.",
    footerData:
      "Data: IMF Balance of Payments and World Economic Outlook, reproduced under the IMF’s terms. Code: MIT licence.",
    footerRepo: "Source code and data on GitHub",
  },
} as const;

export type Dict = (typeof t)[Lang];

export const countryName = (c: { name_nb: string; name_en: string }, lang: Lang) =>
  lang === "nb" ? c.name_nb : c.name_en;
