import type { Lang } from "./types";

const locale = (lang: Lang) => (lang === "nb" ? "nb-NO" : "en-GB");

export function num(v: number | null | undefined, lang: Lang, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return new Intl.NumberFormat(locale(lang), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: "exceptZero",
  }).format(v);
}

export function usd(v: number | null | undefined, lang: Lang): string {
  if (v === null || v === undefined) return "–";
  return lang === "nb" ? `${num(v, lang)} mrd. USD` : `USD ${num(v, lang)} bn`;
}

export function pct(v: number | null | undefined, lang: Lang): string {
  if (v === null || v === undefined) return "–";
  return lang === "nb" ? `${num(v, lang)} % av BNP` : `${num(v, lang)}% of GDP`;
}

export const value = (v: number | null | undefined, unit: "usd" | "pct", lang: Lang) =>
  unit === "usd" ? usd(v, lang) : pct(v, lang);

/** "2026-Q2" -> "2. kv. 2026" / "Q2 2026". */
export function quarter(p: string | null | undefined, lang: Lang): string {
  if (!p) return "–";
  const m = /^(\d{4})-Q([1-4])$/.exec(p);
  if (!m) return p;
  return lang === "nb" ? `${m[2]}. kv. ${m[1]}` : `Q${m[2]} ${m[1]}`;
}

/** Compact quarter label for axes: "K2 26" / "Q2 26". */
export function quarterShort(p: string, lang: Lang): string {
  const m = /^(\d{4})-Q([1-4])$/.exec(p);
  if (!m) return p;
  return `${lang === "nb" ? "K" : "Q"}${m[2]} ${m[1].slice(2)}`;
}

export function windowLabel(periods: string[], lang: Lang): string {
  if (periods.length === 1) return quarter(periods[0], lang);
  return `${quarter(periods[0], lang)} – ${quarter(periods[periods.length - 1], lang)}`;
}

export function date(iso: string, lang: Lang): string {
  const d = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat(locale(lang), {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}
