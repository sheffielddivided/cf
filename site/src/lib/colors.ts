// Resolve the theme's CSS custom properties to concrete colors (for scales and Plot).
export function cssVar(name: string, el: Element = document.documentElement): string {
  return getComputedStyle(el).getPropertyValue(name).trim();
}

export function themeColors() {
  return {
    inflow: cssVar("--inflow"),
    outflow: cssVar("--outflow"),
    inflowDeep: cssVar("--inflow-deep"),
    outflowDeep: cssVar("--outflow-deep"),
    mid: cssVar("--mid"),
    ink: cssVar("--ink"),
    ink2: cssVar("--ink-2"),
    grid: cssVar("--grid"),
    axis: cssVar("--axis"),
    surface: cssVar("--surface"),
    series: ["--s1", "--s2", "--s3", "--s4", "--s5"].map((v) => cssVar(v)),
  };
}

/** Re-run `fn` when the OS color scheme changes (dark mode is selected, not flipped). */
export function onThemeChange(fn: () => void): void {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", fn);
}
