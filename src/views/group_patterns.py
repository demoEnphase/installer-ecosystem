"""Tab 4 — Installer Group Patterns (Country × Group × Segment × Priority)."""
import pandas as pd
import streamlit as st
from utils.helpers import quarter_label, sort_quarters


DEVICE_TYPES  = ["Microinverter", "IQ Battery", "EVSE"]
DEVICE_TABS   = ["⚡ Microinverter", "☀️ Storage (KWh)", "🔌 EVSE"]
TIERS         = ["Diamond", "Platinum", "Golden", "Silver"]
SEGS          = ["Lost", "Declining", "Growing", "New", "Stable"]

TIER_COLORS = {
    "Diamond": "#A855F7", "Platinum": "#64748B",
    "Golden": "#F59E0B",  "Silver":   "#94A3B8",
}

SEG_LABEL = {"Declining": "📉 Declining", "Growing": "📈 Growing", "New": "🆕 New"}


def _build_group_pattern_table(df_raw: pd.DataFrame, master: pd.DataFrame,
                                all_5q: list, device: str) -> pd.DataFrame:
    """
    Rows = Installer_Country × Installer_Group × Installer_Category × Priority
    Columns = P1/P2 counts, total IC, quarterly, weekly
    """
    df_5q = df_raw[df_raw["Quarter"].isin(all_5q)].copy()
    if device != "All":
        df_5q = df_5q[df_5q["Device Type"] == device]

    # Merge classification (drop overlap first to avoid _x/_y)
    class_cols = ["join_key", "Installer_Country", "Installer_Category",
                  "Installer_Group", "Priority"]
    overlap = [c for c in class_cols if c != "join_key" and c in df_5q.columns]
    df_5q = df_5q.drop(columns=overlap, errors="ignore")
    df_5q = df_5q.merge(master[class_cols], on="join_key", how="left")

    # Filter to actionable segments only (exclude Lost + Stable for group patterns)
    df_5q = df_5q[df_5q["Installer_Category"].isin(SEGS)]
    df_5q = df_5q[df_5q["Installer_Group"].isin(TIERS)]

    if df_5q.empty:
        return pd.DataFrame()

    # Group keys
    grp = ["Installer_Country", "Installer_Group", "Installer_Category", "Priority"]

    # P1/P2 installer counts
    ic_agg = (
        df_5q.drop_duplicates(subset=["join_key"] + grp)
        .groupby(grp)["join_key"].count()
        .reset_index()
        .rename(columns={"join_key": "IC_Count"})
    )

    # Quarterly units
    q_agg = (
        df_5q.groupby(grp + ["Quarter"])["Number of devices"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    for q in all_5q:
        if q not in q_agg.columns:
            q_agg[q] = 0

    # Weekly units — current quarter only to avoid duplicate WW names across years
    cur_q_year = all_5q[-1].split("-Q")[0]
    q_num = int(all_5q[-1].split("-Q")[1])
    wk_lo, wk_hi = {1:(1,13),2:(14,26),3:(27,39),4:(40,53)}.get(q_num,(1,53))
    def _in_cur_q(yw):
        p = str(yw).split("-W")
        return len(p)==2 and p[0]==cur_q_year and wk_lo<=int(p[1])<=wk_hi
    cur_wks = [w for w in df_5q["Year-week"].dropna().unique() if _in_cur_q(w)]
    wk_agg = (
        df_5q[df_5q["Year-week"].isin(cur_wks)]
        .groupby(grp + ["Year-week"])["Number of devices"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Merge all
    result = ic_agg.merge(q_agg, on=grp, how="left")
    result = result.merge(wk_agg, on=grp, how="left")
    result = result.fillna(0)

    # Grand total
    q_cols = [c for c in result.columns if c in all_5q]
    result["Total_IC_prior"] = result[q_cols[:-1]].sum(axis=1) if len(q_cols) > 1 else 0
    result["Total_Current_Q"] = result[q_cols[-1]] if q_cols else 0

    return result


def _build_detail_pivot(df_raw: pd.DataFrame, master: pd.DataFrame,
                        all_5q, device: str,
                        sel_tier: str, sel_seg: str) -> pd.DataFrame:
    """
    One row per Country × Group.
    Columns: Declining P1/P2, Growing P1/P2, New P1/P2,
             Total P1, Total P2, Total IC,
             Prior 4Q acts, Current Q acts,
             per-quarter acts, per-week acts (current Q only).
    """
    all_5q = list(all_5q)  # convert from tuple (cache key) back to list
    _sorted_5q = sort_quarters(all_5q)
    cur_q   = _sorted_5q[-1]
    prior_4q = _sorted_5q[:-1]

    df_5q = df_raw[df_raw["Quarter"].isin(all_5q)].copy()
    if device != "All":
        df_5q = df_5q[df_5q["Device Type"] == device]

    units_col = "KWh" if (device == "IQ Battery" and "KWh" in df_5q.columns) else "Number of devices"

    class_cols = ["join_key", "Installer_Country", "Installer_Category",
                  "Installer_Group", "Priority"]
    overlap = [c for c in class_cols if c != "join_key" and c in df_5q.columns]
    df_5q = df_5q.drop(columns=overlap, errors="ignore")
    df_5q = df_5q.merge(master[class_cols], on="join_key", how="left")
    df_5q = df_5q[df_5q["Installer_Group"].isin(TIERS)]
    if sel_tier != "All":
        df_5q = df_5q[df_5q["Installer_Group"] == sel_tier]
    if sel_seg != "All":
        df_5q = df_5q[df_5q["Installer_Category"] == sel_seg]
    else:
        df_5q = df_5q[df_5q["Installer_Category"].isin(SEGS)]
    if df_5q.empty:
        return pd.DataFrame()

    idx = ["Installer_Country", "Installer_Group"]

    # ── Installer counts per Segment × Priority ──────────────────────────────
    ic_base = (
        df_5q.drop_duplicates(subset=["join_key", "Installer_Country",
                                       "Installer_Group", "Installer_Category", "Priority"])
        .groupby(idx + ["Installer_Category", "Priority"])["join_key"]
        .count().reset_index().rename(columns={"join_key": "_n"})
    )
    ic_base["_col"] = ic_base["Installer_Category"] + " " + ic_base["Priority"]
    ic_piv = ic_base.pivot_table(index=idx, columns="_col", values="_n",
                                  aggfunc="sum", fill_value=0).reset_index()
    ic_piv.columns.name = None
    for seg in SEGS:
        for pri in ["P1", "P2"]:
            c = f"{seg} {pri}"
            if c not in ic_piv.columns:
                ic_piv[c] = 0

    # Totals
    ic_total = (
        df_5q.drop_duplicates(subset=["join_key", "Installer_Country",
                                       "Installer_Group", "Priority"])
        .groupby(idx + ["Priority"])["join_key"].count()
        .unstack(fill_value=0).reset_index()
    )
    ic_total.columns.name = None
    if "P1" not in ic_total.columns: ic_total["P1"] = 0
    if "P2" not in ic_total.columns: ic_total["P2"] = 0
    ic_total = ic_total.rename(columns={"P1": "Total P1", "P2": "Total P2"})
    ic_total["Total IC"] = ic_total["Total P1"] + ic_total["Total P2"]

    # ── Quarterly activations ────────────────────────────────────────────────
    q_agg = (
        df_5q.groupby(idx + ["Quarter"])[units_col]
        .sum().unstack(fill_value=0).reset_index()
    )
    q_agg.columns.name = None
    for q in all_5q:
        if q not in q_agg.columns:
            q_agg[q] = 0
    q_agg["Prior 4Q"] = q_agg[[q for q in prior_4q if q in q_agg.columns]].sum(axis=1)
    q_agg["Current Q"] = q_agg.get(cur_q, 0)
    q_lbl = {q: quarter_label(q) for q in all_5q}
    q_agg = q_agg.rename(columns=q_lbl)

    # ── Weekly activations (current quarter only) ────────────────────────────
    cur_yr  = cur_q.split("-Q")[0]
    q_num   = int(cur_q.split("-Q")[1])
    wk_lo, wk_hi = {1:(1,13),2:(14,26),3:(27,39),4:(40,53)}.get(q_num,(1,53))
    def _in_q(yw):
        p = str(yw).split("-W")
        return len(p)==2 and p[0]==cur_yr and wk_lo<=int(p[1])<=wk_hi
    cur_wks = [w for w in df_5q["Year-week"].dropna().unique() if _in_q(w)]
    wk_agg = (
        df_5q[df_5q["Year-week"].isin(cur_wks)]
        .groupby(idx + ["Year-week"])[units_col]
        .sum().unstack(fill_value=0).reset_index()
    )
    wk_agg.columns.name = None
    _seen = set()
    wk_rename = {}
    for c in wk_agg.columns:
        if "-W" in str(c):
            lbl = f"WW{int(str(c).split('-W')[1])}"
            if lbl not in _seen:
                wk_rename[c] = lbl
                _seen.add(lbl)
    wk_agg = wk_agg.rename(columns=wk_rename)

    # ── Merge all ────────────────────────────────────────────────────────────
    result = ic_piv.merge(ic_total[idx + ["Total P1", "Total P2", "Total IC"]],
                          on=idx, how="left")
    result = result.merge(q_agg, on=idx, how="left")
    result = result.merge(wk_agg, on=idx, how="left")
    result = result.fillna(0)

    # Column order
    seg_pri_cols = [f"{s} {p}" for s in ["Lost", "Declining", "Growing", "New", "Stable"]
                    for p in ["P1", "P2"]]
    q_lbl_cols   = [quarter_label(q) for q in _sorted_5q]
    wk_cols      = sorted([c for c in result.columns if c.startswith("WW")],
                          key=lambda x: int(x[2:]))
    ordered = (idx + seg_pri_cols +
               ["Total P1", "Total P2", "Total IC",
                "Prior 4Q", "Current Q"] +
               q_lbl_cols + wk_cols)
    ordered = [c for c in ordered if c in result.columns]
    result = result[ordered].copy()

    # Sort: country total desc → tier order → Total IC desc within tier
    _tier_order = {t: i for i, t in enumerate(TIERS)}
    result["_ctry_total"] = result.groupby("Installer_Country")["Total IC"].transform("sum")
    result["_tier_ord"]   = result["Installer_Group"].map(_tier_order).fillna(99)
    result = result.sort_values(
        ["_ctry_total", "Installer_Country", "_tier_ord", "Total IC"],
        ascending=[False, True, True, False]
    ).drop(columns=["_ctry_total", "_tier_ord"])
    result = result.rename(columns={
        "Installer_Country": "Country",
        "Installer_Group":   "Group",
    })
    return result.reset_index(drop=True)


def _build_summary_pivots(df_raw: pd.DataFrame, master: pd.DataFrame,
                           all_5q: list, sel_tier: str,
                           sel_seg: str) -> tuple:
    """
    Returns (units_df, count_df) — two summary pivot tables.
    Rows = Country × Group × Segment; Columns = device type icons.
    Sorted by Total (units / count) descending.
    """
    df_5q = df_raw[df_raw["Quarter"].isin(all_5q)].copy()
    class_cols = ["join_key", "Installer_Country", "Installer_Category",
                  "Installer_Group", "Priority"]
    overlap = [c for c in class_cols if c != "join_key" and c in df_5q.columns]
    df_5q = df_5q.drop(columns=overlap, errors="ignore")
    df_5q = df_5q.merge(master[class_cols], on="join_key", how="left")
    df_5q = df_5q[df_5q["Installer_Category"].isin(SEGS)]
    df_5q = df_5q[df_5q["Installer_Group"].isin(TIERS)]
    df_5q = df_5q[df_5q["Device Type"].isin(DEVICE_TYPES)]
    if sel_tier != "All":
        df_5q = df_5q[df_5q["Installer_Group"] == sel_tier]
    if sel_seg != "All":
        df_5q = df_5q[df_5q["Installer_Category"] == sel_seg]
    if df_5q.empty:
        return pd.DataFrame(), pd.DataFrame()

    grp_keys = ["Installer_Country", "Installer_Group", "Installer_Category", "Device Type"]

    # ── Units pivot ──────────────────────────────────────────────────────────
    units = (
        df_5q.groupby(grp_keys)["Number of devices"]
        .sum().reset_index()
        .rename(columns={"Number of devices": "_units"})
    )
    units["_dev_label"] = units["Device Type"].map(DEVICE_ICONS)
    units_piv = units.pivot_table(
        index=["Installer_Country", "Installer_Group", "Installer_Category"],
        columns="_dev_label", values="_units", aggfunc="sum", fill_value=0
    ).reset_index()
    units_piv.columns.name = None
    for col in DEVICE_ICONS.values():
        if col not in units_piv.columns:
            units_piv[col] = 0
    icon_cols = [c for c in DEVICE_ICONS.values() if c in units_piv.columns]
    units_piv["Total"] = units_piv[icon_cols].sum(axis=1)
    units_piv = units_piv.sort_values("Total", ascending=False).reset_index(drop=True)
    units_piv = units_piv.rename(columns={
        "Installer_Country": "Country",
        "Installer_Group":   "Group",
        "Installer_Category": "Segment",
    })

    # ── Installer count pivot ────────────────────────────────────────────────
    counts = (
        df_5q.drop_duplicates(subset=["join_key", "Installer_Group",
                                       "Installer_Category", "Device Type"])
        .groupby(grp_keys)["join_key"].count().reset_index()
        .rename(columns={"join_key": "_cnt"})
    )
    counts["_dev_label"] = counts["Device Type"].map(DEVICE_ICONS)
    count_piv = counts.pivot_table(
        index=["Installer_Country", "Installer_Group", "Installer_Category"],
        columns="_dev_label", values="_cnt", aggfunc="sum", fill_value=0
    ).reset_index()
    count_piv.columns.name = None
    for col in DEVICE_ICONS.values():
        if col not in count_piv.columns:
            count_piv[col] = 0
    count_piv["Total"] = count_piv[icon_cols].sum(axis=1)
    count_piv = count_piv.sort_values("Total", ascending=False).reset_index(drop=True)
    count_piv = count_piv.rename(columns={
        "Installer_Country": "Country",
        "Installer_Group":   "Group",
        "Installer_Category": "Segment",
    })

    return units_piv, count_piv


_DEV_ICON = {"Microinverter": "⚡", "IQ Battery": "🔋", "EVSE": "🔌"}
_DEV_UNIT = {"Microinverter": "units", "IQ Battery": "KWh", "EVSE": "units"}


def _build_unified_tables(df_raw: pd.DataFrame, master: pd.DataFrame,
                           all_5q, sel_tier: str, sel_seg: str):
    """
    Returns (acts_df, count_df):
    Both have rows Country × Group.
    acts_df  columns: ⚡/🔋/🔌 per quarter + Total
    count_df columns: ⚡/🔋/🔌 installer counts (Seg×Priority) + Total IC
    Sort: country total desc → Diamond→Platinum→Golden→Silver → Total IC desc
    """
    from utils.helpers import sort_quarters as _sq
    all_5q = list(all_5q)  # convert from tuple (cache key) back to list
    _sorted_5q = _sq(all_5q)
    cur_q    = _sorted_5q[-1]
    prior_4q = _sorted_5q[:-1]

    df_5q = df_raw[df_raw["Quarter"].isin(all_5q)].copy()
    class_cols = ["join_key", "Installer_Country", "Installer_Category",
                  "Installer_Group", "Priority"]
    overlap = [c for c in class_cols if c != "join_key" and c in df_5q.columns]
    df_5q = df_5q.drop(columns=overlap, errors="ignore")
    df_5q = df_5q.merge(master[class_cols], on="join_key", how="left")
    df_5q = df_5q[df_5q["Installer_Group"].isin(TIERS)]
    if sel_tier != "All":
        df_5q = df_5q[df_5q["Installer_Group"] == sel_tier]
    if sel_seg != "All":
        df_5q = df_5q[df_5q["Installer_Category"] == sel_seg]
    else:
        df_5q = df_5q[df_5q["Installer_Category"].isin(SEGS)]
    if df_5q.empty:
        return pd.DataFrame(), pd.DataFrame()

    idx = ["Installer_Country", "Installer_Group"]
    q_lbl = {q: quarter_label(q) for q in _sorted_5q}

    # ── Activation table ──────────────────────────────────────────────────────
    act_frames = []
    for dev in DEVICE_TYPES:
        icon = _DEV_ICON[dev]
        unit = _DEV_UNIT[dev]
        df_dev = df_5q[df_5q["Device Type"] == dev]
        vc = "KWh" if (dev == "IQ Battery" and "KWh" in df_dev.columns) else "Number of devices"
        if df_dev.empty:
            continue
        qa = (df_dev.groupby(idx + ["Quarter"])[vc]
              .sum().unstack(fill_value=0).reset_index())
        qa.columns.name = None
        for q in all_5q:
            if q not in qa.columns:
                qa[q] = 0
        qa[f"{icon} Prior 4Q ({unit})"] = qa[[q for q in prior_4q if q in qa.columns]].sum(axis=1)
        qa[f"{icon} Cur Q ({unit})"]    = qa.get(cur_q, 0)
        for q in _sorted_5q:
            qa[f"{icon} {q_lbl[q]}"] = qa.get(q, 0)
        keep = [f"{icon} Prior 4Q ({unit})", f"{icon} Cur Q ({unit})"] + \
               [f"{icon} {q_lbl[q]}" for q in _sorted_5q]
        qa = qa[idx + keep]
        act_frames.append(qa)

    if not act_frames:
        acts_df = pd.DataFrame()
    else:
        acts_df = act_frames[0]
        for f in act_frames[1:]:
            acts_df = acts_df.merge(f, on=idx, how="outer")
        acts_df = acts_df.fillna(0)
        # Sort
        acts_df = acts_df.copy()
        _to = {t: i for i, t in enumerate(TIERS)}
        acts_df["_ct"] = acts_df.groupby("Installer_Country")[
            [c for c in acts_df.columns if "Cur Q" in c or "Prior 4Q" in c]
        ].transform("sum").sum(axis=1)
        acts_df["_to"] = acts_df["Installer_Group"].map(_to).fillna(99)
        acts_df = acts_df.sort_values(["_ct", "Installer_Country", "_to"],
                                      ascending=[False, True, True]
                                      ).drop(columns=["_ct", "_to"])
        acts_df = acts_df.rename(columns={"Installer_Country": "Country",
                                           "Installer_Group": "Group"})

    # ── Installer count table ─────────────────────────────────────────────────
    cnt_frames = []
    for dev in DEVICE_TYPES:
        icon = _DEV_ICON[dev]
        df_dev = df_5q[df_5q["Device Type"] == dev]
        if df_dev.empty:
            continue
        ic = (df_dev.drop_duplicates(subset=["join_key"] + idx)
              .groupby(idx)["join_key"].count().reset_index()
              .rename(columns={"join_key": f"{icon} IC"}))
        cnt_frames.append(ic)

    if not cnt_frames:
        count_df = pd.DataFrame()
    else:
        count_df = cnt_frames[0]
        for f in cnt_frames[1:]:
            count_df = count_df.merge(f, on=idx, how="outer")
        count_df = count_df.fillna(0).astype(
            {c: int for c in count_df.columns if c not in idx})
        ic_cols = [c for c in count_df.columns if c not in idx]
        count_df["Total IC"] = count_df[ic_cols].sum(axis=1)
        count_df = count_df.copy()
        _to = {t: i for i, t in enumerate(TIERS)}
        count_df["_ct"] = count_df.groupby("Installer_Country")["Total IC"].transform("sum")
        count_df["_to"] = count_df["Installer_Group"].map(_to).fillna(99)
        count_df = count_df.sort_values(["_ct", "Installer_Country", "_to"],
                                         ascending=[False, True, True]
                                         ).drop(columns=["_ct", "_to"])
        count_df = count_df.rename(columns={"Installer_Country": "Country",
                                             "Installer_Group": "Group"})

    return acts_df, count_df


def render_group_patterns(df_raw: pd.DataFrame, master: pd.DataFrame,
                           all_5q: list, role: str,
                           user_country: str = ""):
    st.subheader("🏆 Installer Group Patterns")

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 2])
    all_countries = sorted(master["Installer_Country"].dropna().unique())
    with col1:
        sel_country = st.selectbox(
            "Country", ["All"] + list(all_countries),
            index=(["All"] + list(all_countries)).index(user_country)
            if user_country in (["All"] + list(all_countries)) else 0,
            key="gp_country"
        )
    with col2:
        sel_tier = st.selectbox("Installer Group", ["All"] + TIERS, key="gp_tier")
    with col3:
        sel_seg = st.selectbox("Segment", ["All"] + SEGS, key="gp_seg")

    show_wk = st.toggle("📅 Show weekly columns", value=False, key="gp_wk_toggle")

    if sel_country != "All":
        master_f = master[master["Installer_Country"] == sel_country]
        df_raw_f = df_raw[df_raw["join_key"].isin(master_f["join_key"])]
    else:
        master_f = master
        df_raw_f = df_raw

    _gp_key = f"gp_{len(df_raw_f)}_{len(master_f)}_{str(all_5q)}_{sel_tier}_{sel_seg}"
    if st.session_state.get("_gp_key") != _gp_key:
        st.session_state["_gp_key"] = _gp_key
        st.session_state["_gp_tables"] = _build_unified_tables(
            df_raw_f, master_f, all_5q, sel_tier, sel_seg)
    acts_df, count_df = st.session_state["_gp_tables"]

    def _num_cfg(df):
        return {c: st.column_config.NumberColumn(c, format="%,d")
                for c in df.columns if c not in ("Country", "Group")}

    # ── Table 1: Activations ───────────────────────────────────────────────────
    st.markdown("#### 📊 Activations — ⚡ Micros (units) · 🔋 Storage (KWh) · 🔌 EVSE (units)")
    if acts_df.empty:
        st.info("No activation data for selected filters.")
    else:
        st.caption(f"{len(acts_df):,} rows · country grouped, highest first")
        st.dataframe(acts_df, use_container_width=True,
                     height=min(600, (len(acts_df) + 1) * 35 + 40),
                     hide_index=True, column_config=_num_cfg(acts_df))
        st.download_button("⬇️ Export Activations", acts_df.to_csv(index=False).encode(),
                           "gp_activations.csv", key=f"gp_dl_acts_{sel_country}")

    st.divider()

    # ── Table 2: Installer Count ───────────────────────────────────────────────
    st.markdown("#### 👷 Installer Count — ⚡ Micros · 🔋 Storage · 🔌 EVSE")
    if count_df.empty:
        st.info("No installer data for selected filters.")
    else:
        st.caption(f"{len(count_df):,} rows · country grouped, highest first")
        st.dataframe(count_df, use_container_width=True,
                     height=min(600, (len(count_df) + 1) * 35 + 40),
                     hide_index=True, column_config=_num_cfg(count_df))
        st.download_button("⬇️ Export Installer Count", count_df.to_csv(index=False).encode(),
                           "gp_count.csv", key=f"gp_dl_cnt_{sel_country}")
