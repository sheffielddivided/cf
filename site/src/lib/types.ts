// Shapes of the JSON files written by pipeline/export.py.

export type Lang = "nb" | "en";
export type WindowKey = "q" | "4q" | "year" | "latest";
export type Status = "reported" | "derived" | "missing";

export interface MetaCountry {
  iso3: string;
  name_nb: string;
  name_en: string;
  in_top20: boolean;
  aggregate: boolean;
  financial_centre: boolean;
  iso_num?: string | null;
  latest: string | null;
}

export interface Meta {
  data_updated_at: string;
  last_common_quarter: string;
  reference_year: number;
  top20: string[];
  countries: MetaCountry[];
  sources: { id: string; citation: string; url: string }[];
  warnings: string[];
}

export interface Cell {
  usd: number | null;
  pct: number | null;
}

export interface MeasureValues {
  q: Cell;
  "4q": Cell;
  year: Cell;
  latest: Cell & { period: string | null };
}

export interface RankingRow {
  country: string;
  in_top20: boolean;
  status: Record<"q" | "4q" | "year", Status>;
  values: Record<string, MeasureValues>;
}

export interface Ranking {
  last_common_quarter: string;
  reference_year: number;
  windows: { q: string[]; "4q": string[]; year: string[] };
  rows: RankingRow[];
}

export interface CountryData {
  country: string;
  in_top20: boolean;
  periods: string[];
  latest: string | null;
  series: Record<string, Partial<Record<"net" | "assets" | "liabilities", (number | null)[]>>>;
  pct_gdp_4q: Record<string, (number | null)[]>;
  gdp_usd_bn: Record<string, number | null>;
  gdp_estimate_from: number;
  derived_periods: string[];
  series_keys: Record<string, Partial<Record<string, string>>>;
  notes: string[];
}

export interface Heatmap {
  measure: string;
  periods: string[];
  rows: { country: string; usd: (number | null)[]; pct: (number | null)[] }[];
}

export interface NowcastSource {
  country: string;
  freq: "M" | "W";
  currency: "USD" | "EUR" | "JPY" | "NOK";
  unit?: string;
  url: string;
  citation: string;
  stale: boolean;
  periods: string[];
  nonres: (number | null)[];
  res: (number | null)[];
  net: (number | null)[];
}
export interface Nowcast { sources: Record<string, NowcastSource> }

export interface CrossCheck {
  periods: string[];
  threshold: { rel: number; abs_bn: number };
  measures: string[];
  countries: { country: string; compared: number; flagged: number; max_abs_diff: number | null; missing_in_oecd: number }[];
  flagged: { country: string; measure: string; period: string; imf: number; oecd: number; diff: number }[];
  excluded?: { country: string; reason: string }[];
}

export interface RevisionEntry { date: string; last_common_quarter: string; new: number; revised: number; removed: number }
export interface Revisions {
  latest: RevisionEntry & { changes: { country: string; measure: string; period: string; old: number; new: number; diff: number }[] };
  history: RevisionEntry[];
}
