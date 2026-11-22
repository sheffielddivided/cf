// Build-time access to data files that may not exist yet (written by newer pipeline versions).
import type { CrossCheck, Episodes, Holdings, Nowcast, Revisions } from "./types";

const files = import.meta.glob<{ default: unknown }>(
  "../../public/data/{nowcast,crosscheck,revisions,holdings,episodes}.json",
  { eager: true },
);

interface Files { nowcast: Nowcast; crosscheck: CrossCheck; revisions: Revisions; holdings: Holdings; episodes: Episodes }

export function optionalData<K extends keyof Files>(name: K): Files[K] | null;
export function optionalData<T>(name: keyof Files): T | null;
export function optionalData(name: keyof Files): unknown {
  const hit = Object.entries(files).find(([path]) => path.endsWith(`/${name}.json`));
  return hit ? hit[1].default : null;
}
