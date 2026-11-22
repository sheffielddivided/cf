// "Who owns what": helpers shared by the holdings page (build time) and its script.
import type { Holder, Lang } from "./types";

/** Country name from ISO2 via the platform's CLDR data (counterparts outside the top 20). */
export function regionName(iso2: string | null, iso3: string, lang: Lang): string {
  if (!iso2) return iso3;
  try {
    const dn = new Intl.DisplayNames([lang === "nb" ? "nb" : "en"], { type: "region" });
    return dn.of(iso2) ?? iso3;
  } catch {
    return iso3;
  }
}

/** Bar width in percent of the largest value in the list (lists are sorted, largest first). */
export function barWidths(rows: Holder[]): number[] {
  const max = Math.max(0, ...rows.map((r) => r.usd_bn));
  return rows.map((r) => (max > 0 ? Math.max(0.5, (r.usd_bn / max) * 100) : 0));
}

/** Sequential bins for the holder × issuer matrix (USD bn); index 0..4, or null for missing. */
export const MATRIX_BINS = [10, 50, 200, 1000] as const;

export function matrixBin(v: number | null): number | null {
  if (v === null || v === undefined) return null;
  let i = 0;
  while (i < MATRIX_BINS.length && v >= MATRIX_BINS[i]) i++;
  return i;
}

/** End-of-period date of a position, to follow "per" / "as of":
 *  "2025-S2" -> "desember 2025" / "December 2025", "2024" -> "utgangen av 2024" / "end-2024". */
export function positionPeriod(p: string | undefined, lang: Lang): string {
  if (!p) return "–";
  const month = (y: string, m: number) =>
    new Intl.DateTimeFormat(lang === "nb" ? "nb-NO" : "en-GB", { month: "long", year: "numeric", timeZone: "UTC" })
      .format(new Date(Date.UTC(Number(y), m - 1, 1)));
  const s = /^(\d{4})-S([12])$/.exec(p);
  if (s) return month(s[1], s[2] === "1" ? 6 : 12);
  const q = /^(\d{4})-Q([1-4])$/.exec(p);
  if (q) return month(q[1], Number(q[2]) * 3);
  return lang === "nb" ? `utgangen av ${p}` : `end-${p}`;
}

/** Unsigned amount (stocks have no direction): 0 decimals from 100 bn, otherwise 1. */
export function amount(v: number | null | undefined, lang: Lang): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const digits = Math.abs(v) >= 100 ? 0 : 1;
  return new Intl.NumberFormat(lang === "nb" ? "nb-NO" : "en-GB", {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  }).format(v);
}
