"""Quality checks (docs/DESIGN.md, Metoderegler og datakvalitet).

Errors stop the run (nothing is committed). Warnings are published with the data and
reported in a GitHub Issue.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .coverage import QUARTER_RE, q_index
from .model import COMPONENTS, MAIN, OBS_COLUMNS
from .normalize import FINANCIAL_ACCOUNT_MEASURES, SIDES

TOL_ABS_BN = 0.5
TOL_REL = 0.01


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def extend(self, other: CheckResult) -> None:
        self.errors += other.errors
        self.warnings += other.warnings


def _tol(x: float) -> float:
    return max(TOL_ABS_BN, TOL_REL * abs(x))


def check_schema(df: pd.DataFrame, measures: set[str]) -> CheckResult:
    r = CheckResult()
    missing = [c for c in OBS_COLUMNS if c not in df.columns]
    if missing:
        r.errors.append(f"skjema: mangler kolonner {missing}")
        return r
    if df.duplicated(["country", "measure", "side", "period"]).any():
        r.errors.append("skjema: dupliserte observasjoner")
    bad_m = set(df.measure) - measures
    if bad_m:
        r.errors.append(f"skjema: ukjente måltall {sorted(bad_m)}")
    bad_s = set(df.side) - SIDES
    if bad_s:
        r.errors.append(f"skjema: ukjente sider {sorted(bad_s)}")
    q = df[df.freq == "Q"]
    bad_p = sorted({p for p in q.period if not QUARTER_RE.match(p)})
    if bad_p:
        r.errors.append(f"skjema: ugyldige kvartaler {bad_p[:5]}")
    if (df.value_raw.isna() != df.value.isna()).any():
        r.errors.append("skjema: value og value_raw er ikke null samtidig")
    if (df.value_raw.isna() & (df.obs_status != "missing")).any():
        r.errors.append("skjema: manglende verdi uten obs_status=missing")
    return r


def check_sign(df: pd.DataFrame) -> CheckResult:
    """Independent re-statement of the sign rule: net FA value == -raw / 1e9."""
    r = CheckResult()
    sub = df[df.measure.isin(FINANCIAL_ACCOUNT_MEASURES) & (df.side != "liabilities")
             & df.value.notna()]
    bad = sub[(sub.value + sub.value_raw / 1e9).abs() > 1e-6]
    if not bad.empty:
        r.errors.append(f"fortegn: {len(bad)} observasjoner bryter fortegnsregelen, "
                        f"f.eks. {bad.iloc[0].country} {bad.iloc[0].measure} {bad.iloc[0].period}")
    return r


def _wide(df: pd.DataFrame, measure: str) -> pd.DataFrame:
    """One net measure in BPM6 sign, USD bn, indexed by (country, period)."""
    sub = df[(df.measure == measure) & (df.side == "net") & (df.freq == "Q")]
    return sub.set_index(["country", "period"])["value_raw"] / 1e9


def check_identity(df: pd.DataFrame, periods: set[str]) -> CheckResult:
    """D + P + F7 + O + R = FAB (BPM6), within tolerance, for the given periods."""
    r = CheckResult()
    fab = _wide(df, "fa_total")
    parts = pd.concat([_wide(df, m).rename(m) for m in COMPONENTS], axis=1)
    joined = parts.join(fab.rename("fab"), how="inner")
    for (country, period), row in joined.iterrows():
        if period not in periods or pd.isna(row.fab):
            continue
        total = row[COMPONENTS].sum(skipna=True)
        if abs(total - row.fab) > _tol(row.fab):
            r.warnings.append(f"identitet: {country} {period}: komponenter {total:.1f} ≠ "
                              f"finansregnskap {row.fab:.1f} mrd. USD")
    return r


def check_mirror(df: pd.DataFrame, periods: set[str]) -> CheckResult:
    """CA + KA + E&O = FA (BPM6), within tolerance."""
    r = CheckResult()
    cols = {m: _wide(df, m) for m in ("current_account", "capital_account",
                                      "errors_omissions", "fa_total")}
    joined = pd.concat([v.rename(k) for k, v in cols.items()], axis=1).dropna()
    for (country, period), row in joined.iterrows():
        if period not in periods:
            continue
        lhs = row.current_account + row.capital_account + row.errors_omissions
        if abs(lhs - row.fa_total) > _tol(row.fa_total):
            r.warnings.append(f"speiling: {country} {period}: DB+KK+FU {lhs:.1f} ≠ "
                              f"FA {row.fa_total:.1f} mrd. USD")
    return r


def check_freshness(latest: dict[str, str | None], today: date, days: int = 200) -> CheckResult:
    r = CheckResult()
    for country, q in sorted(latest.items()):
        if q is None:
            r.warnings.append(f"ferskhet: {country} har ingen verdier for hovedmålet")
            continue
        year, quarter = int(q[:4]), int(q[-1])
        end_month = quarter * 3
        end = date(year + (end_month // 12), end_month % 12 + 1, 1)  # first day after quarter
        if (today - end).days > days:
            r.warnings.append(
                f"ferskhet: {country} siste kvartal {q} er mer enn {days} dager gammelt"
            )
    return r


def check_outliers(df: pd.DataFrame, periods: set[str], z: float = 4.0) -> CheckResult:
    r = CheckResult()
    main = df[(df.measure == MAIN) & (df.side == "net") & df.value.notna()]
    for country, g in main.groupby("country"):
        g = g.sort_values("period", key=lambda s: s.map(q_index))
        if len(g) < 12:
            continue
        mu, sd = g.value.mean(), g.value.std()
        if not sd or math.isnan(sd):
            continue
        for row in g[g.period.isin(periods)].itertuples():
            if abs(row.value - mu) / sd > z:
                r.warnings.append(f"ekstremverdi: {country} {row.period}: {row.value:.1f} mrd. USD "
                                  f"er mer enn {z:g} standardavvik fra landets historikk")
    return r


def compare_revisions(
    old: pd.DataFrame | None, new: pd.DataFrame, rel: float = 0.10
) -> tuple[dict[str, int], list[str]]:
    """Count new/revised observations; list large revisions (> rel and > TOL_ABS_BN)."""
    stats = {"new": 0, "revised": 0, "removed": 0}
    if old is None or old.empty:
        stats["new"] = int(new.value.notna().sum())
        return stats, []
    key = ["country", "measure", "side", "period"]
    m = old[key + ["value"]].merge(new[key + ["value"]], on=key, how="outer",
                                   suffixes=("_old", "_new"), indicator=True)
    stats["new"] = int(((m._merge == "right_only") & m.value_new.notna()).sum()
                       + (m.value_old.isna() & m.value_new.notna() & (m._merge == "both")).sum())
    stats["removed"] = int(((m._merge == "left_only") & m.value_old.notna()).sum())
    both = m[(m._merge == "both") & m.value_old.notna() & m.value_new.notna()]
    changed = both[(both.value_old - both.value_new).abs() > 1e-9]
    stats["revised"] = len(changed)
    big = changed[((changed.value_old - changed.value_new).abs() > TOL_ABS_BN)
                  & ((changed.value_old - changed.value_new).abs()
                     > rel * changed.value_old.abs())]
    lines = [
        f"{r.country} {r.measure}/{r.side} {r.period}: {r.value_old:.1f} → {r.value_new:.1f}"
        for r in big.itertuples()
    ]
    return stats, lines


def revision_details(old: pd.DataFrame | None, new: pd.DataFrame, limit: int = 150) -> list[dict]:
    """Revised net values (site sign, USD bn), largest absolute change first."""
    if old is None or old.empty:
        return []
    key = ["country", "measure", "side", "period"]
    m = old[key + ["value"]].merge(new[key + ["value"]], on=key, suffixes=("_old", "_new"))
    m = m[m.value_old.notna() & m.value_new.notna() & (m.side == "net")]
    m = m.assign(diff=m.value_new - m.value_old)
    m = m[m["diff"].abs() > 0.05]
    m = m.reindex(m["diff"].abs().sort_values(ascending=False).index).head(limit)
    return [
        {"country": r.country, "measure": r.measure, "period": r.period,
         "old": round(r.value_old, 2), "new": round(r.value_new, 2), "diff": round(r.diff, 2)}
        for r in m.itertuples(index=False)
    ]
