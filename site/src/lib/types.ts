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

// ---------------------------------------------------------------- phase 3

export interface Holder { iso3: string; iso2: string | null; usd_bn: number }

export interface HoldingsCountry {
  pip_assets?: { period: string; world: number; top: Holder[] };
  pip_held_by?: { period: string; reporters_total: number; top: Holder[] };
  dip_out?: { period: string; world: number; top: Holder[] };
  dip_in?: { period: string; world: number; top: Holder[] };
  bis?: { periods: string[]; claims: (number | null)[]; liabilities: (number | null)[] };
}

export interface Holdings {
  countries: Record<string, HoldingsCountry>;
  pip_matrix?: { period: string; holders: string[]; issuers: string[]; usd_bn: (number | null)[][] };
}

export type EpisodeType = "inflow_surge" | "inflow_stop" | "outflow_surge" | "outflow_retrenchment";

export interface Episode { type: EpisodeType; start: string; end: string; peak: string; peak_z: number }

export interface EpisodeSeries {
  periods: string[];
  dC: (number | null)[];
  mu: (number | null)[];
  sd: (number | null)[];
  episodes: Episode[];
}

export interface Episodes {
  method: { window_quarters: number; threshold_sd: number; bounds_sd: number; min_quarters: number; components: string[] };
  countries: Record<string, { inflows?: EpisodeSeries; outflows?: EpisodeSeries }>;
  active: (Episode & { country: string })[];
}
