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
