"""
Core installer classification logic.
Produces one row per installer × country with all segment, tier, and overview fields.
"""
import pandas as pd
import numpy as np
from utils.helpers import quarter_to_int, int_to_quarter, sort_quarters
from utils.state_lookup import get_state_full

META_COLS = [
    "join_key", "Installer_Country", "Installer_Mapped",
    "RSMs", "Installer State", "Installer City",
    "Support Emai", "Account Phone", "Installer-Zip", "Commercial Y/N",
]


def get_current_quarter(df: pd.DataFrame) -> str:
    quarters = df["Quarter"].dropna().unique()
    return max(quarters, key=quarter_to_int)


def build_installer_master(df: pd.DataFrame, current_q: str, all_5q: list) -> pd.DataFrame:
    """
    Returns one-row-per-installer DataFrame with:
    - metadata (RSM, state, city, contact)
    - quarterly activation columns
    - weekly activation pivot
    - run-rate columns
    - segment + tier + overview (filled by caller)
    """
    df_5q = df[df["Quarter"].isin(all_5q)].copy()

    # ── Quarterly aggregation ──────────────────────────────────────────────
    q_agg = (
        df_5q.groupby(["join_key", "Quarter"])["Number of devices"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    # Ensure all 5Q columns exist
    for q in all_5q:
        if q not in q_agg.columns:
            q_agg[q] = 0

    # ── Metadata (latest per installer) ────────────────────────────────────
    meta = (
        df_5q.sort_values("Year-week", ascending=False)
        .drop_duplicates(subset=["join_key"])
        [META_COLS]
        .copy()
    )
    meta["Installer_State_X"] = meta["Installer State"].apply(get_state_full)

    # ── Merge ───────────────────────────────────────────────────────────────
    master = meta.merge(q_agg, on="join_key", how="left")
    for q in all_5q:
        if q not in master.columns:
            master[q] = 0
        master[q] = master[q].fillna(0)

    # ── Grand Total (5Q all devices) ────────────────────────────────────────
    master["Grand_Total_5Q"] = master[all_5q].sum(axis=1)
    master["Current_Q_Acts"] = master[current_q].fillna(0)

    return master


def compute_weekly_pivot(df: pd.DataFrame, all_5q: list) -> pd.DataFrame:
    """Returns pivot: join_key × Year-week → sum(Number of devices)."""
    df_5q = df[df["Quarter"].isin(all_5q)].copy()
    return (
        df_5q.groupby(["join_key", "Year-week"])["Number of devices"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )


def compute_week_counts_per_quarter(df: pd.DataFrame, all_5q: list) -> pd.DataFrame:
    """Count distinct Year-week values per installer per quarter."""
    df_5q = df[df["Quarter"].isin(all_5q)].copy()
    return (
        df_5q.groupby(["join_key", "Quarter"])["Year-week"]
        .nunique()
        .reset_index()
        .rename(columns={"Year-week": "week_count"})
    )


def compute_run_rates(master: pd.DataFrame, wk_counts: pd.DataFrame,
                      current_q: str, prior_2q: list) -> pd.DataFrame:
    """Attach run-rate columns (activations / distinct weeks) for current and prior 2 quarters."""
    for q in [current_q] + prior_2q:
        wk = wk_counts[wk_counts["Quarter"] == q][["join_key", "week_count"]].rename(
            columns={"week_count": f"wk_{q}"}
        )
        master = master.merge(wk, on="join_key", how="left")
        master[f"wk_{q}"] = master[f"wk_{q}"].fillna(1).clip(lower=1)
        acts = master[q].fillna(0) if q in master.columns else 0
        master[f"rr_{q}"] = acts / master[f"wk_{q}"]
    return master


def classify_segment(row: pd.Series, current_q: str, prior_4q: list, prior_2q: list,
                     decline_pct: float = 25.0, growth_pct: float = 15.0) -> str:
    """
    decline_pct: run-rate must drop by this % vs prior avg to be Declining (default 25%)
    growth_pct : run-rate must rise  by this % vs prior avg to be Growing   (default 15%)
    """
    cur_acts = row.get(current_q, 0) or 0
    if cur_acts == 0:
        return "Lost"
    prior_acts = sum(row.get(q, 0) or 0 for q in prior_4q)
    if prior_acts == 0:
        return "New"
    rr_cur = row.get(f"rr_{current_q}", 0) or 0
    rr_p1 = row.get(f"rr_{prior_2q[0]}", 0) or 0
    rr_p2 = row.get(f"rr_{prior_2q[1]}", 0) or 0
    rr_prior_avg = (rr_p1 + rr_p2) / 2 if (rr_p1 + rr_p2) > 0 else 0
    if rr_prior_avg > 0:
        if rr_cur < rr_prior_avg * (1 - decline_pct / 100):
            return "Declining"
        if rr_cur > rr_prior_avg * (1 + growth_pct / 100):
            return "Growing"
    return "Stable"


def assign_tier(rank: int) -> str:
    if rank <= 0:
        return "Silver"
    if rank <= 20:
        return "Diamond"
    elif rank <= 70:
        return "Platinum"
    elif rank <= 170:
        return "Golden"
    return "Silver"


def installer_overview(device_set: set) -> str:
    has_micro = "Microinverter" in device_set
    has_storage = "IQ Battery" in device_set
    has_evse = "EVSE" in device_set
    if has_micro and has_storage and has_evse:
        return "PV+Storage+EVSE"
    if has_micro and has_storage:
        return "Micros+Storage"
    if has_micro and has_evse:
        return "PV+EVSE"
    if has_micro:
        return "PV Only"
    if has_storage and has_evse:
        return "Storage+EVSE"
    if has_storage:
        return "Storage Only"
    if has_evse:
        return "EVSE Only"
    return "Unknown"


def run_full_classification(df: pd.DataFrame,
                            decline_pct: float = 25.0,
                            growth_pct: float = 15.0):
    """
    Main entry point.
    Returns (master_df, current_q, all_5q, prior_4q, weekly_pivot_df)
    decline_pct / growth_pct: configurable thresholds (%)
    """
    current_q = get_current_quarter(df)
    curr_int = quarter_to_int(current_q)
    all_5q = sort_quarters([int_to_quarter(curr_int - i) for i in range(4, -1, -1)])
    prior_4q = [int_to_quarter(curr_int - i) for i in range(1, 5)]
    prior_2q = [int_to_quarter(curr_int - 1), int_to_quarter(curr_int - 2)]

    # ── Master table ────────────────────────────────────────────────────────
    master = build_installer_master(df, current_q, all_5q)

    # ── Run rates ───────────────────────────────────────────────────────────
    wk_counts = compute_week_counts_per_quarter(df, all_5q)
    master = compute_run_rates(master, wk_counts, current_q, prior_2q)

    # ── Segment (vectorized) ────────────────────────────────────────────────
    _cur = master[current_q].fillna(0)
    _prior_cols = [q for q in prior_4q if q in master.columns]
    _prior_sum = master[_prior_cols].fillna(0).sum(axis=1) if _prior_cols else pd.Series(0, index=master.index)
    _rr_cur = master.get(f"rr_{current_q}", pd.Series(0.0, index=master.index)).fillna(0)
    _rr_p1  = master.get(f"rr_{prior_2q[0]}", pd.Series(0.0, index=master.index)).fillna(0)
    _rr_p2  = master.get(f"rr_{prior_2q[1]}", pd.Series(0.0, index=master.index)).fillna(0)
    _rr_avg = (_rr_p1 + _rr_p2) / 2
    _seg = pd.Series("Stable", index=master.index)
    _seg[_cur == 0] = "Lost"
    _seg[(_cur > 0) & (_prior_sum == 0)] = "New"
    _active = (_cur > 0) & (_prior_sum > 0) & (_rr_avg > 0)
    _seg[_active & (_rr_cur < _rr_avg * (1 - decline_pct / 100))] = "Declining"
    _seg[_active & (_rr_cur > _rr_avg * (1 + growth_pct / 100)) & (_seg != "Declining")] = "Growing"
    master["Installer_Category"] = _seg

    # ── Volume Tier (ALL installers ranked per country by Grand_Total_5Q) ────
    # Top 20 per country → Diamond, next 50 → Platinum, next 100 → Golden, rest → Silver
    master["Grand_Total_5Q"] = pd.to_numeric(master["Grand_Total_5Q"], errors="coerce").fillna(0)
    _rank = (
        master.groupby("Installer_Country")["Grand_Total_5Q"]
        .rank(ascending=False, method="first")
        .fillna(999)
    )
    master["country_rank"] = _rank.astype(float).round(0).astype(int)
    master["Installer_Group"] = master["country_rank"].apply(assign_tier)
    master.loc[master["Installer_Category"] == "Lost", "Installer_Group"] = ""

    # ── Installer Overview (vectorized pivot) ─────────────────────────────
    df_5q = df[df["Quarter"].isin(all_5q)]
    _dev_dedup = df_5q[["join_key", "Device Type"]].dropna().drop_duplicates()
    _dev_pivot = (
        _dev_dedup.assign(_v=1)
        .pivot_table(index="join_key", columns="Device Type", values="_v", aggfunc="max", fill_value=0)
        .reset_index()
    )
    _has_micro   = _dev_pivot.get("Microinverter", pd.Series(0, index=_dev_pivot.index)).astype(bool)
    _has_storage = _dev_pivot.get("IQ Battery",    pd.Series(0, index=_dev_pivot.index)).astype(bool)
    _has_evse    = _dev_pivot.get("EVSE",           pd.Series(0, index=_dev_pivot.index)).astype(bool)
    import numpy as np
    _overview = np.select(
        [
            _has_micro & _has_storage & _has_evse,
            _has_micro & _has_storage,
            _has_micro & _has_evse,
            _has_micro,
            _has_storage & _has_evse,
            _has_storage,
            _has_evse,
        ],
        ["PV+Storage+EVSE", "Micros+Storage", "PV+EVSE", "PV Only",
         "Storage+EVSE", "Storage Only", "EVSE Only"],
        default="Unknown"
    )
    _dev_pivot["Installer_Overview"] = _overview
    master = master.merge(_dev_pivot[["join_key", "Installer_Overview"]], on="join_key", how="left")
    master["Installer_Overview"] = master["Installer_Overview"].fillna("Unknown")

    # ── Weekly pivot ────────────────────────────────────────────────────────
    weekly_pivot = compute_weekly_pivot(df, all_5q)

    return master, current_q, all_5q, prior_4q, weekly_pivot
