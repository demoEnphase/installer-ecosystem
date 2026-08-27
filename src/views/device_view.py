"""Tab 2 — Installer View by Device Type."""
import pandas as pd
import plotly.express as px
import streamlit as st
from utils.helpers import sort_quarters, quarter_label
from src.views.inbox import _render_actions_table


DEVICE_COLORS = {
    "Microinverter": "#F59E0B",
    "IQ Battery": "#3B82F6",
    "EVSE": "#10B981",
}


def _build_device_master(df_raw: pd.DataFrame, master: pd.DataFrame,
                         all_5q, weekly_pivot: pd.DataFrame) -> pd.DataFrame:
    """One row per installer × device type with quarterly + weekly activations."""
    all_5q = list(all_5q)  # ensure list
    df_5q = df_raw[df_raw["Quarter"].isin(all_5q)].copy()

    # Quarterly agg by device type
    q_dev = (
        df_5q.groupby(["join_key", "Device Type", "Quarter"])["Number of devices"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    for q in all_5q:
        if q not in q_dev.columns:
            q_dev[q] = 0

    # KWh agg (storage only) — per quarter + total
    # Handle different column names across basedata versions
    _kwh_col = next((c for c in ["KWh", "Battery Kwh", "Battery KWh"] if c in df_5q.columns), None)
    if _kwh_col and _kwh_col != "KWh":
        df_5q = df_5q.rename(columns={_kwh_col: "KWh"})
    if "KWh" not in df_5q.columns:
        df_5q["KWh"] = 0
    q_kwh = (
        df_5q.groupby(["join_key", "Device Type", "Quarter"])["KWh"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    q_kwh = q_kwh.rename(columns={q: f"{q}_kwh" for q in all_5q if q in q_kwh.columns})
    kwh_agg = q_kwh.copy()
    kwh_cols = [f"{q}_kwh" for q in all_5q if f"{q}_kwh" in kwh_agg.columns]
    kwh_agg["Total_KWh"] = kwh_agg[kwh_cols].sum(axis=1).round(0).astype(int)
    for kc in kwh_cols:
        kwh_agg[kc] = kwh_agg[kc].fillna(0).round(0).astype(int)

    # Commercial Y/N: Y if ANY site for that installer+device is commercial
    comm = (
        df_5q.groupby(["join_key", "Device Type"])["Commercial Y/N"]
        .apply(lambda x: "Y" if "Y" in x.values else "N")
        .reset_index()
    )

    # Merge
    dev_master = q_dev.merge(kwh_agg[["join_key", "Device Type", "Total_KWh"] + kwh_cols],
                             on=["join_key", "Device Type"], how="left")
    for kc in kwh_cols:
        if kc not in dev_master.columns:
            dev_master[kc] = 0
        else:
            dev_master[kc] = dev_master[kc].fillna(0).astype(int)
    dev_master["Total_KWh"] = dev_master["Total_KWh"].fillna(0).astype(int)
    dev_master = dev_master.merge(comm, on=["join_key", "Device Type"], how="left")

    # Grand total per device type
    dev_master["Device_Total_5Q"] = dev_master[all_5q].sum(axis=1)

    # Join installer classification columns
    class_cols = ["join_key", "Installer_Country", "Installer_Mapped", "RSMs",
                  "Installer State", "Installer_State_X", "Installer City",
                  "Top_Disti_1", "Top_Disti_2",
                  "Installer_Category", "Installer_Group", "Priority",
                  "ABCXYZ", "Installer_Overview",
                  "Support Emai", "Account Phone", "Lost_Regained"]
    class_cols = [c for c in class_cols if c in master.columns]
    dev_master = dev_master.merge(master[class_cols], on="join_key", how="left")

    # Weekly pivot by device — current quarter only to avoid duplicate WW names
    cur_q_year = all_5q[-1].split("-Q")[0]
    q_num = int(all_5q[-1].split("-Q")[1])
    wk_ranges = {1: (1, 13), 2: (14, 26), 3: (27, 39), 4: (40, 53)}
    wk_lo, wk_hi = wk_ranges.get(q_num, (1, 53))
    def _in_cur_q(yw):
        parts = str(yw).split("-W")
        return len(parts) == 2 and parts[0] == cur_q_year and wk_lo <= int(parts[1]) <= wk_hi
    cur_q_weeks = [yw for yw in df_5q["Year-week"].dropna().unique() if _in_cur_q(yw)]
    df_wk = (
        df_5q[df_5q["Year-week"].isin(cur_q_weeks)]
        .groupby(["join_key", "Device Type", "Year-week"])["Number of devices"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    dev_master = dev_master.merge(df_wk, on=["join_key", "Device Type"], how="left")

    return dev_master


def render_device_view(df_raw: pd.DataFrame, master: pd.DataFrame,
                       weekly_pivot: pd.DataFrame, all_5q: list,
                       role: str, username: str = "",
                       user_country: str = "", user_rsm: str = ""):
    st.subheader("📋 Installers List — By Device")

    # ── Drill-down from Summary tab ───────────────────────────────────────────
    _drill_active    = st.session_state.get("drill_active", False)
    _drill_group_col = st.session_state.get("drill_group_col", "")
    _drill_group_val = st.session_state.get("drill_group_val", "")
    _drill_tier      = st.session_state.get("drill_tier")
    _drill_seg       = st.session_state.get("drill_seg")
    _drill_pri       = st.session_state.get("drill_pri")
    _drill_device    = st.session_state.get("drill_device", "All")

    _all_c_dv     = sorted(master["Installer_Country"].dropna().unique())
    _all_r_dv     = sorted(master["RSMs"].dropna().unique())
    _tier_opts_dv = ["All"] + sorted(master["Installer_Group"].dropna().unique())

    if _drill_active and not st.session_state.get("drill_applied_dv", False):
        if _drill_group_col == "Installer_Country" and _drill_group_val in _all_c_dv:
            st.session_state["dv_country"] = [_drill_group_val]
        elif _drill_group_col == "RSMs" and _drill_group_val in _all_r_dv:
            st.session_state["dv_rsm"] = [_drill_group_val]
        if _drill_device in ["Microinverter", "IQ Battery", "EVSE"]:
            st.session_state["dv_device"] = _drill_device
        if _drill_seg:
            _seg_init = ["All"] + sorted(master["Installer_Category"].dropna().unique().tolist())
            if _drill_seg in _seg_init:
                st.session_state["dv_seg"] = _drill_seg
        if _drill_tier and _drill_tier in _tier_opts_dv:
            st.session_state["dv_tier"] = _drill_tier
        if _drill_pri in ["P1", "P2"]:
            st.session_state["dv_priority"] = _drill_pri
        st.session_state["drill_applied_dv"] = True

    if _drill_active:
        _parts = [_drill_group_val or "All"]
        if _drill_tier:
            _parts.append(f"Tier: {_drill_tier}")
        if _drill_seg:
            _parts.append(f"Seg: {_drill_seg}" + (f" {_drill_pri}" if _drill_pri else ""))
        if _drill_device and _drill_device != "All":
            _parts.append(_drill_device)
        _bc1, _bc2 = st.columns([6, 1])
        with _bc1:
            _sep = " \u00b7 "
            st.success(f"\U0001f50d Drilled from Summary \u2192 **{_sep.join(_parts)}**")
        with _bc2:
            if st.button("\u2715 Clear filter", key="dv_drill_clear"):
                for _k in ["drill_active", "drill_group_col", "drill_group_val",
                           "drill_tier", "drill_seg", "drill_pri", "drill_device",
                           "drill_applied_dv", "goto_installer_list", "_last_drill_key"]:
                    st.session_state.pop(_k, None)
                st.rerun()

    # ── Build device master before layout (overview filter depends on it) ────
    _dm_key = f"dm_{len(df_raw)}_{len(master)}_{str(all_5q)}"
    if st.session_state.get("_dm_key") != _dm_key:
        st.session_state["_dm_key"] = _dm_key
        st.session_state["_dev_master"] = _build_device_master(df_raw, master, all_5q, weekly_pivot)
    dev_master = st.session_state["_dev_master"]

    # ── Horizontal filter bar (top) ──────────────────────────────────────────
    _f1, _f2, _f3, _f4, _f5 = st.columns([2, 2, 1, 1, 1])
    default_c = [user_country] if user_country and user_country in _all_c_dv else []
    sel_countries = _f1.multiselect("Country", _all_c_dv, default=default_c, key="dv_country")
    default_r = [user_rsm] if user_rsm and user_rsm in _all_r_dv else []
    sel_rsms    = _f2.multiselect("RSM", _all_r_dv, default=default_r, key="dv_rsm")
    seg_opts    = ["All"] + sorted(master["Installer_Category"].dropna().unique())
    sel_seg     = _f3.selectbox("Segment", seg_opts, key="dv_seg")
    sel_pri     = _f4.selectbox("Priority", ["All", "P1", "P2"], key="dv_priority")
    sel_device  = _f5.selectbox("Device Type", ["All", "Microinverter", "IQ Battery", "EVSE"], key="dv_device")

    _f6, _f7, _f8 = st.columns([1, 2, 4])
    sel_tier    = _f6.selectbox("Group / Tier", _tier_opts_dv, key="dv_tier")
    ov_opts     = (["All"] + sorted(dev_master["Installer_Overview"].dropna().unique().tolist())
                   if "Installer_Overview" in dev_master.columns else ["All"])
    sel_overview = _f7.selectbox("Overview", ov_opts, key="dv_overview")

    st.divider()

    # ── Apply filters (mask-based, no copy) ───────────────────────────────────
    _mask = pd.Series(True, index=dev_master.index)
    if sel_countries:
        _mask &= dev_master["Installer_Country"].isin(sel_countries)
    if sel_rsms:
        _mask &= dev_master["RSMs"].isin(sel_rsms)
    if sel_device != "All":
        _mask &= dev_master["Device Type"] == sel_device
    if sel_seg != "All":
        _mask &= dev_master["Installer_Category"] == sel_seg
    if sel_tier != "All":
        _mask &= dev_master["Installer_Group"] == sel_tier
    if sel_pri != "All":
        _mask &= dev_master["Priority"] == sel_pri
    if sel_overview != "All":
        _mask &= dev_master["Installer_Overview"] == sel_overview
    dm = dev_master[_mask]

    # Sort: cached by filter signature — only recomputes when filters change
    _filter_sig = (tuple(sel_countries), tuple(sel_rsms), sel_device,
                   sel_seg, sel_tier, sel_pri, sel_overview)
    if st.session_state.get("_dv_filter_sig") != _filter_sig:
        _ctry_rank = dm.groupby("Installer_Country")["Device_Total_5Q"].sum().rename("_ctry_total")
        dm = (dm.join(_ctry_rank, on="Installer_Country")
                .sort_values(["_ctry_total", "Device_Total_5Q"], ascending=[False, False])
                .drop(columns=["_ctry_total"]))
        st.session_state["_dv_filter_sig"] = _filter_sig
        st.session_state["_dv_sorted"] = dm
    else:
        dm = st.session_state["_dv_sorted"]

    # ── KPI strip ────────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    k1.metric("Micro Installers", f"{len(dm[dm['Device Type'] == 'Microinverter']['join_key'].unique()):,}")
    k2.metric("Storage Installers", f"{len(dm[dm['Device Type'] == 'IQ Battery']['join_key'].unique()):,}")
    k3.metric("EVSE Installers", f"{len(dm[dm['Device Type'] == 'EVSE']['join_key'].unique()):,}")

    st.divider()

    # ── Build display columns ─────────────────────────────────────────────────
    is_storage = (sel_device == "IQ Battery")
    if is_storage:
        for q in all_5q:
            kc = f"{q}_kwh"
            if kc in dm.columns:
                dm[q] = dm[kc]
        dm["Device_Total_5Q"] = dm["Total_KWh"]

    total_col_label = "Total KWh (5Q)" if is_storage else "Total (5Q)"

    q_labels = {q: quarter_label(q) for q in all_5q}
    wk_raw_cols = sorted([c for c in dm.columns if "-W" in str(c)], key=lambda x: x)
    wk_display = {c: f"WW{int(c.split('-W')[1])}" for c in wk_raw_cols}
    seen_wk = set()
    wk_display = {c: v for c, v in wk_display.items() if not (v in seen_wk or seen_wk.add(v))}
    dm = dm.rename(columns={**q_labels, **wk_display})

    display_cols = (
        ["Installer_Country", "Installer_Mapped", "RSMs", "Device Type",
         "Commercial Y/N", "Installer State", "Installer City",
         "Top_Disti_1", "Top_Disti_2"]
        + list(q_labels.values())
        + list(wk_display.values())
        + ["Device_Total_5Q",
           "Installer_Category", "Installer_Group", "Priority", "Installer_Overview",
           "Support Emai", "Account Phone"]
    )
    display_cols = [c for c in display_cols if c in dm.columns]
    df_show = dm[display_cols].rename(columns={
        "Installer_Country": "Country",
        "Installer_Mapped": "Installer Name",
        "RSMs": "RSM",
        "Top_Disti_1": "Top Disti 1",
        "Top_Disti_2": "Top Disti 2",
        "Device_Total_5Q": total_col_label,
        "Installer_Category": "Category",
        "Installer_Group": "Group",
        "Installer_Overview": "Overview",
        "Support Emai": "Email",
        "Account Phone": "Phone",
    })

    show_weekly = st.toggle("📅 Show weekly columns", value=False, key="dv_weekly_toggle")
    if not show_weekly:
        wk_drop = [c for c in df_show.columns if c.startswith("WW") and c[2:].isdigit()]
        df_show = df_show.drop(columns=wk_drop)

    _dv_col_cfg = {
        "Country":        st.column_config.TextColumn("Country",        width="small", pinned=True),
        "Installer Name": st.column_config.TextColumn("Installer Name", width="large", pinned=True),
        total_col_label:  st.column_config.NumberColumn(total_col_label, format="%,d", width="small"),
        "Email":          st.column_config.LinkColumn("✉️ Email", display_text=r"mailto:(.*)", width="medium"),
    }
    for _c in df_show.columns:
        if (_c.startswith("Q") and "'" in _c) or _c.startswith("WW"):
            _dv_col_cfg[_c] = st.column_config.NumberColumn(_c, format="%,d", width="small")
    st.caption(f"Showing {len(df_show):,} rows · highest country activations first, then highest installer first")
    st.dataframe(df_show, use_container_width=True, height=520, column_config=_dv_col_cfg,
                 hide_index=True)

    if "Email" in df_show.columns:
        df_show["Email"] = df_show["Email"].apply(
            lambda x: f"mailto:{x}" if pd.notna(x) and "@" in str(x) else "")

    csv = df_show.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export to CSV", csv, "device_view.csv", "text/csv", key="dv_export")

    st.divider()

    # ── Lost Installer Tracking ───────────────────────────────────────────────
    st.markdown("### 🔴 Lost Installer Tracking")
    st.caption("Track action notes for Lost installers. Pending rows appear first.")

    lost_keys = master[master["Installer_Category"] == "Lost"]["join_key"].unique()
    if len(lost_keys) > 0:
        from utils.helpers import sort_quarters as _sq
        _sorted_5q = _sq(all_5q)
        _current_q  = _sorted_5q[-1]
        _prior_4q   = _sorted_5q[:-1]

        df_lost_raw = df_raw[
            df_raw["join_key"].isin(lost_keys) &
            df_raw["Quarter"].isin(_prior_4q) &
            df_raw["Device Type"].isin(["Microinverter", "IQ Battery", "EVSE"])
        ].copy()

        if not df_lost_raw.empty:
            from utils.helpers import quarter_label as _ql
            trend_rows = []
            for dev in ["Microinverter", "IQ Battery", "EVSE"]:
                df_d = df_lost_raw[df_lost_raw["Device Type"] == dev]
                if dev == "IQ Battery":
                    val_col = "KWh" if "KWh" in df_d.columns else "Number of devices"
                else:
                    val_col = "Number of devices"
                grp = df_d.groupby("Quarter")[val_col].sum().reset_index()
                grp["Device"] = "Storage (KWh)" if dev == "IQ Battery" else dev
                grp["Quarter_Label"] = grp["Quarter"].map(
                    {q: _ql(q) for q in _prior_4q})
                grp = grp.rename(columns={val_col: "Value"})
                trend_rows.append(grp)

            trend_df = pd.concat(trend_rows, ignore_index=True)
            dev_colors = {"Microinverter": "#F59E0B",
                          "Storage (KWh)": "#3B82F6", "EVSE": "#10B981"}
            fig_trend = px.bar(
                trend_df, x="Quarter_Label", y="Value",
                color="Device", barmode="group",
                color_discrete_map=dev_colors,
                title=f"Lost Installers — Historical Activation Trend ({len(lost_keys):,} installers, prior quarters only)",
                labels={"Value": "Volume", "Quarter_Label": "Quarter"},
                height=300,
            )
            fig_trend.update_layout(margin=dict(t=40, b=0, l=0, r=0),
                                    legend=dict(orientation="h", y=-0.28))
            st.plotly_chart(fig_trend, width="stretch", key="dv_lost_trend")

    _render_actions_table(master, role, username, user_country, user_rsm,
                          caller_key="dv_lost", segments=["Lost"],
                          df_raw=df_raw, all_5q=all_5q)
