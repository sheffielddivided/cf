// Build-time access to data files that may not exist yet (written by newer pipeline versions).
const files = import.meta.glob<{ default: unknown }>(
  "../../public/data/{nowcast,crosscheck,revisions}.json",
  { eager: true },
);

export function optionalData<T>(name: "nowcast" | "crosscheck" | "revisions"): T | null {
  const hit = Object.entries(files).find(([path]) => path.endsWith(`/${name}.json`));
  return hit ? (hit[1].default as T) : null;
}
