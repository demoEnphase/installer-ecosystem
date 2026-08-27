"""Tab 1 — Installer List (All Devices)."""
import io
import pandas as pd
import streamlit as st
from utils.helpers import sort_quarters, quarter_label
from src.db import save_override, save_comment, get_comments, save_message
from src.views.inbox import _render_actions_table


_ASP_REGION = {
    "Euro": {
        "2025-Q2": 166, "2025-Q3": 161, "2025-Q4": 167,
        "2026-Q1": 168, "2026-Q2": 177,
    },
    "ANZP": {
        "2025-Q2": 112, "2025-Q3": 124, "2025-Q4": 126,
        "2026-Q1": 129, "2026-Q2": 126,
    },
}
_ASP_DEFAULT = {
    "2025-Q2": 166, "2025-Q3": 161, "2025-Q4": 167,
    "2026-Q1": 168, "2026-Q2": 177,
}


def _kpi_rev(subset: pd.DataFrame, q: str) -> float:
    """Region-aware revenue: splits subset by Region and applies correct ASP."""
    if q not in subset.columns or subset.empty:
        return 0.0
    total = 0.0
    if "Region" in subset.columns:
        for region, grp in subset.groupby("Region"):
            asp = _ASP_REGION.get(region, _ASP_DEFAULT).get(q, 0)
            total += float(pd.to_numeric(grp[q], errors="coerce").fillna(0).sum()) * asp
    else:
        asp = _ASP_DEFAULT.get(q, 0)
        total = float(pd.to_numeric(subset[q], errors="coerce").fillna(0).sum()) * asp
    return total


def _fmt_rev(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


SEGMENT_COLORS = {
    "Lost": "#FF4B4B",
    "Declining": "#FF914D",
    "Growing": "#21C55D",
    "New": "#3B82F6",
    "Stable": "#94A3B8",
}
TIER_COLORS = {
    "Diamond": "#A855F7",
    "Platinum": "#64748B",
    "Golden": "#F59E0B",
    "Silver": "#6B7280",
    "Lost": "#EF4444",
}


def _color_segment(val):
    c = SEGMENT_COLORS.get(val, "")
    return f"background-color:{c}22; color:{c}; font-weight:600" if c else ""


def _color_tier(val):
    c = TIER_COLORS.get(val, "")
    return f"background-color:{c}22; color:{c}; font-weight:600" if c else ""


def render_installer_list(master: pd.DataFrame, weekly_pivot: pd.DataFrame,
                          df_raw: pd.DataFrame, all_5q: list, role: str, username: str,
                          user_country: str = "", user_rsm: str = ""):
    if st.session_state.get("ins_from_insights", False):
        _back_c, _info_c = st.columns([1, 5])
        with _back_c:
            if st.button("← Back to Insights", key="il_back_insights"):
                st.session_state["active_tab"] = "Insights"
                st.session_state.pop("il_seg",               None)
                st.session_state.pop("il_priority",          None)
                st.session_state.pop("ins_from_insights",    None)
                st.session_state.pop("ins_lost_tier_keys",   None)
                st.session_state.pop("ins_lost_tier_label",  None)
                st.rerun()
        _tier_label = st.session_state.get("ins_lost_tier_label")
        if _tier_label:
            with _info_c:
                st.info(f"🔴 Showing Lost — **{_tier_label}** installers")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.subheader("📱 All Devices")

    # ── Filters — Row 1 ─────────────────────────────────────────────────────
    all_countries = sorted(master["Installer_Country"].dropna().unique())
    all_rsms      = sorted(master["RSMs"].dropna().unique())
    _r1c1, _r1c2, _r1c3, _r1c4, _r1c5 = st.columns([2, 2, 1, 1, 1])

    if role == "country_manager" and user_country:
        sel_countries = _r1c1.multiselect("Country", all_countries,
                                          default=[user_country], key="il_country")
    else:
        sel_countries = _r1c1.multiselect("Country", all_countries,
                                          default=[user_country] if user_country else [],
                                          key="il_country")
    if role == "rsm" and user_rsm:
        sel_rsms = _r1c2.multiselect("RSM", all_rsms,
                                     default=[user_rsm], key="il_rsm")
    else:
        sel_rsms = _r1c2.multiselect("RSM", all_rsms,
                                     default=[user_rsm] if user_rsm else [],
                                     key="il_rsm")

    _dev_opts = ["All", "Microinverter", "IQ Battery", "EVSE"]
    sel_device  = _r1c3.selectbox("Device Type", _dev_opts, key="il_device")
    seg_opts    = ["All"] + sorted(master["Installer_Category"].dropna().unique())
    sel_seg     = _r1c4.selectbox("Segment", seg_opts, key="il_seg")
    tier_opts   = ["All"] + sorted(master["Installer_Group"].dropna().unique())
    sel_tier    = _r1c5.selectbox("Tier", tier_opts, key="il_tier")

    # ── Filters — Row 2 ─────────────────────────────────────────────────────
    _r2c1, _r2c2, _r2c3, _r2c4 = st.columns([1, 1, 2, 3])
    _region_opts = ["All"] + sorted(master["Region"].dropna().unique().tolist()) if "Region" in master.columns else ["All"]
    sel_region  = _r2c1.selectbox("Region", _region_opts, key="il_region")
    sel_pri     = _r2c2.selectbox("Priority", ["All", "P1", "P2"], key="il_priority")
    ov_opts     = (["All"] + sorted(master["Installer_Overview"].dropna().unique().tolist())
                   if "Installer_Overview" in master.columns else ["All"])
    sel_overview = _r2c3.selectbox("Overview", ov_opts, key="il_overview")

    # Apply filters
    df = master.copy()
    if sel_countries:
        df = df[df["Installer_Country"].isin(sel_countries)]
    if sel_rsms:
        df = df[df["RSMs"].isin(sel_rsms)]
    if sel_seg != "All":
        df = df[df["Installer_Category"] == sel_seg]
    if sel_tier != "All":
        df = df[df["Installer_Group"] == sel_tier]
    if sel_pri != "All":
        df = df[df["Priority"] == sel_pri]
    if sel_region != "All" and "Region" in df.columns:
        df = df[df["Region"] == sel_region]
    # Lost tier drill-down from Insights tab
    _tier_jkeys = st.session_state.get("ins_lost_tier_keys")
    if _tier_jkeys:
        df = df[df["join_key"].isin(_tier_jkeys)]
    if sel_overview != "All" and "Installer_Overview" in df.columns:
        df = df[df["Installer_Overview"] == sel_overview]

    # ── Device-type filter: recompute quarterly totals from df_raw ──────────────
    if sel_device != "All":
        _df_dev = df_raw[
            (df_raw["Quarter"].isin(all_5q)) &
            (df_raw["Device Type"] == sel_device) &
            (df_raw["join_key"].isin(df["join_key"]))
        ]
        _q_dev = (
            _df_dev.groupby(["join_key", "Quarter"])["Number of devices"]
            .sum().unstack(fill_value=0).reset_index()
        )
        for _q in all_5q:
            if _q not in _q_dev.columns:
                _q_dev[_q] = 0
        _q_dev["Grand_Total_5Q"] = _q_dev[all_5q].sum(axis=1)
        _q_dev["Current_Q_Acts"] = _q_dev[all_5q[-1]]
        # Drop old quarterly cols from df before merging device-specific ones
        _drop = [c for c in all_5q + ["Grand_Total_5Q", "Current_Q_Acts"]
                 if c in df.columns]
        df = df.drop(columns=_drop)
        df = df.merge(_q_dev[["join_key"] + all_5q + ["Grand_Total_5Q", "Current_Q_Acts"]],
                      on="join_key", how="inner")
        # Filter to installers that actually had activations for this device
        df = df[df["Grand_Total_5Q"] > 0]

    # Sort: country by total activations desc, then installer by activations desc
    if "Grand_Total_5Q" in df.columns:
        _ctry_rank = (
            df.groupby("Installer_Country")["Grand_Total_5Q"]
            .sum().rename("_ctry_total")
        )
        df = df.join(_ctry_rank, on="Installer_Country")
        df = df.sort_values(["_ctry_total", "Grand_Total_5Q"], ascending=[False, False])
        df = df.drop(columns=["_ctry_total"])

    # ── Merge weekly pivot (current quarter only to keep table narrow) ──────
    all_wk_cols = sorted([c for c in weekly_pivot.columns if c != "join_key"])
    cur_q_year, cur_q_num = all_5q[-1].split("-Q")
    q_num = int(cur_q_num)
    # Quarter → approximate ISO week range  Q1:1-13  Q2:14-26  Q3:27-39  Q4:40-53
    wk_ranges = {1: (1, 13), 2: (14, 26), 3: (27, 39), 4: (40, 53)}
    wk_lo, wk_hi = wk_ranges.get(q_num, (1, 53))
    def _wk_in_cur_q(col):
        # col format: "YYYY-WNN"
        parts = col.split("-W")
        return len(parts) == 2 and parts[0] == cur_q_year and wk_lo <= int(parts[1]) <= wk_hi
    cur_wk_cols = [c for c in all_wk_cols if _wk_in_cur_q(c)]
    _seen = set()
    wk_display = {c: f"WW{int(c.split('-W')[1])}" for c in cur_wk_cols
                  if f"WW{int(c.split('-W')[1])}" not in _seen and not _seen.add(f"WW{int(c.split('-W')[1])}")}
    cur_wk_cols = list(wk_display.keys())
    wk_renamed = weekly_pivot[["join_key"] + cur_wk_cols].rename(columns=wk_display)
    wk_display_cols = list(wk_display.values())

    df = df.merge(wk_renamed, on="join_key", how="left")

    # ── Build display table ──────────────────────────────────────────────────
    q_labels = {q: quarter_label(q) for q in all_5q}
    q_display_cols = list(q_labels.values())

    # ── Add per-quarter revenue columns (region-aware) ───────────────────────
    _has_region = "Region" in df.columns
    _rev_col_map = {}   # raw_q -> display rev col name
    for _q in all_5q:
        _ql = q_labels[_q]
        _rev_col = f"Rev {_ql}"
        _rev_col_map[_q] = _rev_col
        if _has_region:
            _asp_series = df["Region"].map(
                {r: _ASP_REGION.get(r, _ASP_DEFAULT).get(_q, 0)
                 for r in df["Region"].unique()}
            ).fillna(0)
        else:
            _asp_series = _ASP_DEFAULT.get(_q, 0)
        df[_rev_col] = (pd.to_numeric(df[_q], errors="coerce").fillna(0)
                        * _asp_series).round(0).astype(int)
    rev_display_cols = list(_rev_col_map.values())

    df_display = df.rename(columns=q_labels)

    display_cols = (
        ["Installer_Country", "Installer_Mapped", "RSMs",
         "Installer State", "Installer_State_X", "Installer City",
         "Top_Disti_1", "Top_Disti_2"]
        + q_display_cols
        + rev_display_cols
        + wk_display_cols
        + ["Grand_Total_5Q", "Current_Q_Acts", "Lost_Regained",
           "Installer_Category", "Installer_Group", "Priority",
           "ABCXYZ", "Installer_Overview",
           "Account Phone", "Support Emai"]
    )
    display_cols = [c for c in display_cols if c in df_display.columns]
    df_show = df_display[display_cols].copy()

    # ── Weekly toggle ────────────────────────────────────────────────────────
    show_weekly = st.toggle("📅 Show weekly columns", value=False, key="il_weekly_toggle")
    if not show_weekly:
        wk_cols_to_drop = [c for c in df_show.columns
                           if c.startswith("WW") and c[2:].isdigit()]
        df_show = df_show.drop(columns=wk_cols_to_drop)
    # Carry join_key alongside df_show for override mapping (reset index for alignment)
    join_keys = df["join_key"].reset_index(drop=True)

    rename_map = {
        "Installer_Country": "Country",
        "Installer_Mapped": "Installer Name",
        "RSMs": "RSM",
        "Installer State": "State",
        "Installer_State_X": "State (Full)",
        "Installer City": "City",
        "Top_Disti_1": "Top Disti 1",
        "Top_Disti_2": "Top Disti 2",
        "Grand_Total_5Q": "Grand Total",
        "Current_Q_Acts": f"Current Q",
        "Lost_Regained": "Lost Regained",
        "Installer_Category": "Category",
        "Installer_Group": "Group",
        "Installer_Overview": "Overview",
        "Support Emai": "Email",
        "Account Phone": "Phone",
    }
    df_show = df_show.rename(columns=rename_map)

    # Make emails clickable
    if "Email" in df_show.columns:
        df_show["Email"] = df_show["Email"].apply(
            lambda x: f"mailto:{x}" if pd.notna(x) and "@" in str(x) else "")

    # ── KPI strip ─────────────────────────────────────────────────────────
    _cq = all_5q[-1]
    _lq = all_5q[-2] if len(all_5q) >= 2 else _cq
    _df_lost     = df[df["Installer_Category"] == "Lost"]
    _df_dec      = df[df["Installer_Category"] == "Declining"]
    _df_grow     = df[df["Installer_Category"] == "Growing"]
    _df_new      = df[df["Installer_Category"] == "New"]
    _df_diamond  = df[df["Installer_Group"]    == "Diamond"]
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Installers", f"{len(df):,}",
              _fmt_rev(_kpi_rev(df, _cq)), delta_color="off")
    k2.metric("💎 Diamond", f"{len(_df_diamond):,}",
              _fmt_rev(_kpi_rev(_df_diamond, _cq)), delta_color="off")
    k3.metric("🔴 Lost", f"{len(_df_lost):,}",
              _fmt_rev(_kpi_rev(_df_lost, _lq)), delta_color="off")
    k4.metric("📉 Declining", f"{len(_df_dec):,}",
              _fmt_rev(_kpi_rev(_df_dec, _cq)), delta_color="off")
    k5.metric("📈 Growing", f"{len(_df_grow):,}",
              _fmt_rev(_kpi_rev(_df_grow, _cq)), delta_color="off")
    k6.metric("🆕 New", f"{len(_df_new):,}",
              _fmt_rev(_kpi_rev(_df_new, _cq)), delta_color="off")

    # ── Main table ───────────────────────────────────────────────────────────
    st.caption(f"Showing {len(df_show):,} installers  ·  Country | Installer | RSM are first columns")

    # Build shared column_config for both editor and read-only view
    _col_cfg = {
        "Country":        st.column_config.TextColumn("Country",        width="small", pinned=True),
        "Installer Name": st.column_config.TextColumn("Installer Name", width="large", pinned=True),
        "RSM":            st.column_config.TextColumn("RSM",            width="medium"),
        "State":          st.column_config.TextColumn("State",          width="small"),
        "State (Full)":   st.column_config.TextColumn("State (Full)",   width="medium"),
        "City":           st.column_config.TextColumn("City",           width="medium"),
        "Top Disti 1":    st.column_config.TextColumn("Top Disti 1",    width="medium"),
        "Top Disti 2":    st.column_config.TextColumn("Top Disti 2",    width="medium"),
        **{f"Rev {quarter_label(q)}": st.column_config.NumberColumn(
               f"Rev {quarter_label(q)}", format="$%,d", width="small")
           for q in all_5q},
        "Grand Total":    st.column_config.NumberColumn("Grand Total",  format="%,d", width="small"),
        "Current Q":      st.column_config.NumberColumn("Current Q",    format="%,d", width="small"),
        "Lost Regained":  st.column_config.TextColumn("Lost Regained",  width="small"),
        "Category":       st.column_config.SelectboxColumn(
                              "Category", width="medium",
                              options=["Lost", "Declining", "Growing", "New", "Stable"]
                          ),
        "Group":          st.column_config.SelectboxColumn(
                              "Group", width="medium",
                              options=["Diamond", "Platinum", "Golden", "Silver", "Lost"]
                          ),
        "Priority":       st.column_config.SelectboxColumn(
                              "Priority", width="small", options=["P1", "P2"]
                          ),
        "ABCXYZ":         st.column_config.TextColumn("ABC-XYZ",        width="small"),
        "Overview":       st.column_config.TextColumn("Overview",       width="medium"),
        "Email":          st.column_config.LinkColumn("Email",          display_text=r"mailto:(.*)", width="large"),
        "Phone":          st.column_config.TextColumn("Phone",          width="medium"),
    }
    # Quarter and week columns: narrow number format
    for c in df_show.columns:
        if c.startswith("Q") and "'" in c:
            _col_cfg[c] = st.column_config.NumberColumn(c, format="%,d", width="small")
        elif c.startswith("WW"):
            _col_cfg[c] = st.column_config.NumberColumn(c, format="%,d", width="small")

    # ── Export (top — visible without scrolling) ─────────────────────────────
    _xl_buf_top = io.BytesIO()
    df_show.to_excel(_xl_buf_top, index=False, engine="openpyxl")
    _t1, _t2, _t3 = st.columns([2, 1, 1])
    with _t2:
        st.download_button("⬇️ CSV",
            df_show.to_csv(index=False).encode("utf-8"),
            "installer_list.csv", "text/csv", key="il_dl_csv_top")
    with _t3:
        st.download_button("⬇️ Excel",
            _xl_buf_top.getvalue(),
            "installer_list.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="il_dl_xlsx_top")

    # Editable columns for admin/CM
    can_edit = role in ("admin", "country_manager")
    if can_edit:
        st.info("✏️ Edit **Category**, **Group**, or **Priority** cells directly. Click **Save Overrides** to persist.")

        edited = st.data_editor(
            df_show,
            use_container_width=True,
            height=520,
            column_config=_col_cfg,
            disabled=[c for c in df_show.columns
                      if c not in ("Category", "Group", "Priority")],
            key="installer_table_edit_v2",
        )

        if st.button("💾 Save Overrides", type="primary"):
            changed = 0
            orig_reset = df_show.reset_index(drop=True)
            edit_reset = edited.reset_index(drop=True)
            for i in range(len(orig_reset)):
                if i >= len(join_keys):
                    break
                jk = join_keys[i]
                for db_field, col_name in [
                    ("Installer_Category", "Category"),
                    ("Installer_Group", "Group"),
                    ("Priority", "Priority"),
                ]:
                    if col_name not in orig_reset.columns:
                        continue
                    ov = orig_reset.at[i, col_name]
                    ev = edit_reset.at[i, col_name]
                    if ov != ev and pd.notna(ev):
                        save_override(jk, db_field, str(ov), str(ev), username)
                        changed += 1
            st.success(f"✓ Saved {changed} override(s)")
    else:
        st.dataframe(df_show, use_container_width=True, height=520,
                     column_config=_col_cfg, hide_index=True)

    # ── Export ──────────────────────────────────────────────────────────────────────────
    _dl1, _dl2 = st.columns(2)
    with _dl1:
        st.download_button("⬇️ Download CSV",
            df_show.to_csv(index=False).encode("utf-8"),
            "installer_list.csv", "text/csv", key="il_dl_csv")
    with _dl2:
        _xl_buf = io.BytesIO()
        df_show.to_excel(_xl_buf, index=False, engine="openpyxl")
        st.download_button("⬇️ Download Excel",
            _xl_buf.getvalue(),
            "installer_list.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="il_dl_xlsx")
