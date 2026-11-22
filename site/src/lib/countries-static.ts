// Build-time access to every country JSON file (for getStaticPaths).
import type { CountryData } from "./types";

const files = import.meta.glob<{ default: CountryData }>("../../public/data/country/*.json", { eager: true });

export function allCountries(): CountryData[] {
  return Object.values(files).map((f) => f.default);
}
