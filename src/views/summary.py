"""Tab 3 — Summary View (Country-level & RSM-level)."""
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils.helpers import quarter_label, sort_quarters


def _sticky_table(df: pd.DataFrame, height: int = 460, key: str = "") -> None:
    """Render df as an HTML table with the first column frozen (sticky left)."""
    num_cols = set(df.select_dtypes("number").columns)

    def _fmt(val, col):
        if col in num_cols:
            try:
                return f"{int(val):,}" if pd.notna(val) else ""
            except Exception:
                return str(val) if pd.notna(val) else ""
        return str(val) if pd.notna(val) else ""

    # Build header
    th_style_first = (
        "position:sticky;left:0;top:0;z-index:3;"
        "background:#F0EFEB;padding:6px 10px;text-align:left;"
        "font-size:12px;font-weight:600;border-bottom:2px solid #DCDCD6;"
        "border-right:1px solid #DCDCD6;white-space:nowrap;"
    )
    th_style = (
        "position:sticky;top:0;background:#F0EFEB;padding:6px 10px;"
        "text-align:right;font-size:12px;font-weight:600;"
        "border-bottom:2px solid #DCDCD6;white-space:nowrap;"
    )
    cols = list(df.columns)
    header = "".join(
        f"<th style='{th_style_first}'>{cols[0]}</th>" if i == 0
        else f"<th style='{th_style}'>{c}</th>"
        for i, c in enumerate(cols)
    )

    # Build rows
    td_style_first = (
        "position:sticky;left:0;z-index:1;"
        "background:#FFFFFF;padding:5px 10px;text-align:left;"
        "font-size:12px;border-bottom:1px solid #EEEEEE;"
        "border-right:1px solid #DCDCD6;white-space:nowrap;"
        "font-weight:500;"
    )
    td_style_first_alt = td_style_first.replace("#FFFFFF", "#FAFAF8")
    td_style = (
        "padding:5px 10px;text-align:right;font-size:12px;"
        "border-bottom:1px solid #EEEEEE;white-space:nowrap;"
    )
    td_style_alt = td_style + "background:#FAFAF8;"

    rows_html = ""
    for r_idx, row in df.iterrows():
        alt = (r_idx % 2 == 1)
        row_cells = ""
        for i, c in enumerate(cols):
            val = _fmt(row[c], c)
            if i == 0:
                row_cells += f"<td style='{td_style_first_alt if alt else td_style_first}'>{val}</td>"
            else:
                row_cells += f"<td style='{td_style_alt if alt else td_style}'>{val}</td>"
        rows_html += f"<tr>{row_cells}</tr>"

    html = f"""
<div style="overflow:auto;max-height:{height}px;border:1px solid #DCDCD6;
            border-radius:8px;position:relative;">
  <table style="border-collapse:separate;border-spacing:0;width:100%;">
    <thead><tr>{header}</tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


TIERS = ["Diamond", "Platinum", "Golden", "Silver"]
SEGS = ["Lost", "Declining", "Growing", "New"]
PRIORITIES = ["P1", "P2"]
DEVICE_TYPES = ["Microinverter", "IQ Battery", "EVSE"]

TIER_COLORS = {
    "Diamond": "#A855F7", "Platinum": "#64748B",
    "Golden": "#F59E0B", "Silver": "#94A3B8",
}
SEG_COLORS = {
    "Lost": "#EF4444", "Declining": "#F97316",
    "Growing": "#22C55E", "New": "#3B82F6", "Stable": "#94A3B8",
}


@st.cache_data(show_spinner=False, ttl=3600)
def _pivot_summary(df_raw: pd.DataFrame, master: pd.DataFrame,
                   all_5q, group_col: str,
                   device_filter: str = None) -> tuple:
    """
    Returns (units_df, count_df) pivoted by group_col.
    Uses vectorized groupby+unstack — no per-row loops.
    Cached via @st.cache_data so repeated tab switches are instant.
    """
    df_5q = df_raw[df_raw["Quarter"].isin(all_5q)].copy()
    if device_filter and device_filter != "All":
        df_5q = df_5q[df_5q["Device Type"] == device_filter]

    units_col = "KWh" if (device_filter == "IQ Battery" and "KWh" in df_5q.columns) else "Number of devices"

    class_cols = ["join_key", "Installer_Category", "Installer_Group", "Priority",
                  "Installer_Country", "RSMs"]
    overlap = [c for c in class_cols if c != "join_key" and c in df_5q.columns]
    df_5q = df_5q.drop(columns=overlap, errors="ignore")
    df_5q = df_5q.merge(master[class_cols], on="join_key", how="left")
    df_5q["_group"] = df_5q[group_col]

    seg_pri_cols = [f"{s}_{p}" for s in SEGS for p in PRIORITIES]

    def make_pivot(df, values_col, aggfunc):
        if df.empty:
            return pd.DataFrame()

        # ── Tier: single groupby + unstack ───────────────────────────────────
        tier_piv = (
            df.groupby(["_group", "Installer_Group"])[values_col]
            .agg(aggfunc)
            .unstack("Installer_Group")
            .reindex(columns=TIERS)
            .fillna(0)
        )

        # ── Segment × Priority: single groupby + unstack ─────────────────────
        df["_seg_pri"] = df["Installer_Category"].astype(str) + "_" + df["Priority"].astype(str)
        seg_piv = (
            df.groupby(["_group", "_seg_pri"])[values_col]
            .agg(aggfunc)
            .unstack("_seg_pri")
            .reindex(columns=seg_pri_cols)
            .fillna(0)
        )

        # ── Quarterly: single groupby + unstack ──────────────────────────────
        q_piv = (
            df.groupby(["_group", "Quarter"])[values_col]
            .agg(aggfunc)
            .unstack("Quarter")
            .reindex(columns=list(all_5q))
            .fillna(0)
        )

        # ── Weekly: single groupby + unstack (replaces 50+ per-week loops) ───
        if "Year-week" in df.columns and df["Year-week"].notna().any():
            wk_sorted = sorted(df["Year-week"].dropna().unique())
            wk_piv = (
                df.groupby(["_group", "Year-week"])[values_col]
                .agg(aggfunc)
                .unstack("Year-week")
                .reindex(columns=wk_sorted)
                .fillna(0)
            )
        else:
            wk_piv = pd.DataFrame(index=tier_piv.index)

        result = pd.concat([tier_piv, seg_piv, q_piv, wk_piv], axis=1)
        result.index.name = "_group"
        result = result.reset_index().rename(columns={"_group": group_col}).fillna(0)
        return result

    df_unique = df_5q.drop_duplicates(subset=["join_key", "_group",
                                               "Installer_Category", "Installer_Group", "Priority"])
    units_df = make_pivot(df_5q, units_col, "sum")
    count_df = make_pivot(df_unique, "join_key", "count")
    return units_df, count_df


def _style_table(df: pd.DataFrame) -> pd.DataFrame:
    return df


def _handle_drill_selection(event, df: pd.DataFrame, group_col: str,
                           device: str, key_suffix: str,
                           master_f: pd.DataFrame = None,
                           df_raw_f: pd.DataFrame = None,
                           all_5q: list = None,
                           is_count: bool = False):
    """Show inline line-level detail when a cell is selected in a summary table."""
    if not hasattr(event, "selection"):
        return
    sel = event.selection or {}
    rows = list(sel.get("rows", []) if hasattr(sel, "get") else getattr(sel, "rows", []))
    cols = list(sel.get("columns", []) if hasattr(sel, "get") else getattr(sel, "columns", []))
    if not rows or not cols:
        return
    row_idx = rows[0]
    col_name = cols[0]
    if row_idx >= len(df) - 1:
        return
    if col_name == group_col:
        return

    group_val = str(df.iloc[row_idx][group_col])

    drill_tier, drill_seg, drill_pri = None, None, None
    if col_name in TIERS:
        drill_tier = col_name
    elif col_name in SEGS:
        drill_seg = col_name
    elif any(col_name == f"{s}_{p}" for s in SEGS for p in ("P1", "P2")):
        drill_seg, drill_pri = col_name.rsplit("_", 1)

    try:
        val = int(df.iloc[row_idx].get(col_name, 0))
    except (TypeError, ValueError):
        val = 0

    g_label   = "Country" if group_col == "Installer_Country" else "RSM"
    col_label = col_name.replace("_", " ")
    unit_lbl  = "installers" if is_count else "units"

    # ── Toast + Banner ──────────────────────────────────────────────────────────
    st.toast(f"\U0001f4cb {group_val} · {col_label} · {device} — showing {val:,} {unit_lbl} below")
    st.success(
        f"\U0001f50d **{g_label}:** {group_val}  \u00b7  "
        f"**Column:** {col_label}  \u00b7  **Device:** {device}  \u00b7  "
        f"**{val:,} {unit_lbl}**"
    )

    # ── Build inline detail ───────────────────────────────────────────────────
    if master_f is not None and df_raw_f is not None:
        _m = master_f.copy()
        if group_col == "Installer_Country":
            _m = _m[_m["Installer_Country"] == group_val]
        else:
            _m = _m[_m["RSMs"] == group_val]
        if drill_tier:
            _m = _m[_m["Installer_Group"] == drill_tier]
        if drill_seg:
            _m = _m[_m["Installer_Category"] == drill_seg]
        if drill_pri:
            _m = _m[_m["Priority"] == drill_pri]

        _keep = [c for c in ["join_key", "Installer_Country", "Installer_Mapped",
                              "RSMs", "Installer_Category", "Installer_Group", "Priority"]
                 if c in _m.columns]
        _detail = _m[_keep].copy()

        # Quarterly activations per installer for this device
        _r = df_raw_f[
            df_raw_f["join_key"].isin(_m["join_key"]) &
            (df_raw_f["Device Type"] == device)
        ].copy() if df_raw_f is not None else pd.DataFrame()

        if not _r.empty and all_5q:
            _val_col = "KWh" if device == "IQ Battery" else "Number of devices"
            if _val_col not in _r.columns:
                _val_col = "Number of devices"
            _r[_val_col] = pd.to_numeric(_r[_val_col], errors="coerce").fillna(0)
            _r = _r[_r["Quarter"].isin(all_5q)]
            _qpiv = (_r.groupby(["join_key", "Quarter"])[_val_col]
                     .sum().unstack(fill_value=0).reset_index())
            _qpiv.columns = (["join_key"] +
                              [quarter_label(c) for c in _qpiv.columns[1:]])
            _qpiv["Total"] = _qpiv.iloc[:, 1:].sum(axis=1)
            _detail = _detail.merge(_qpiv, on="join_key", how="left").fillna(0)

        _detail = _detail.drop(columns=["join_key"], errors="ignore")
        _detail = _detail.rename(columns={
            "Installer_Country": "Country", "Installer_Mapped": "Installer",
            "RSMs": "RSM", "Installer_Category": "Segment",
            "Installer_Group": "Tier",
        })
        if "Total" in _detail.columns:
            _detail = _detail.sort_values("Total", ascending=False)

        _num_cfg = {c: st.column_config.NumberColumn(c, format="%,d")
                    for c in _detail.select_dtypes("number").columns}
        with st.expander(
            f"\U0001f4cb **{len(_detail):,} installers** — "
            f"{g_label}: {group_val} · {col_label} · {device}",
            expanded=True,
        ):
            st.dataframe(_detail, use_container_width=True, hide_index=True,
                         height=min(420, (len(_detail) + 1) * 35 + 50),
                         column_config=_num_cfg)


def _render_summary_tables(df_raw, master, all_5q, group_col, group_label,
                           filter_val=None, table_key_prefix=""):
    """Render activation (units/KWh) + installer count tables for 3 focus devices."""
    if filter_val:
        if group_col == "Installer_Country":
            master_f = master[master["Installer_Country"] == filter_val]
            df_raw_f = df_raw[df_raw["Installer_Country"] == filter_val]
        else:
            master_f = master[master["RSMs"] == filter_val]
            valid_keys = master_f["join_key"].unique()
            df_raw_f = df_raw[df_raw["join_key"].isin(valid_keys)]
    else:
        master_f = master
        df_raw_f = df_raw

    q_label_map = {q: quarter_label(q) for q in all_5q}
    show_wk = st.toggle("📅 Show weekly columns", value=False,
                        key=f"{table_key_prefix}_sum_wk_toggle")

    dev_tabs = st.tabs(["⚡ Microinverter", "☀️ Storage (KWh)", "🔌 EVSE"])

    for dev_tab, device in zip(dev_tabs, DEVICE_TYPES):
        with dev_tab:
            units_df, count_df = _pivot_summary(
                df_raw_f, master_f, all_5q, group_col, device)

            if units_df.empty:
                st.caption("No data for this device type.")
                continue

            def _prepare(df):
                df = df.rename(columns=q_label_map)
                wk_seen = set()
                wk_map = {}
                for c in df.columns:
                    if "-W" in str(c):
                        lbl = f"WW{int(str(c).split('-W')[1])}"
                        if lbl not in wk_seen:
                            wk_map[c] = lbl; wk_seen.add(lbl)
                df = df.rename(columns=wk_map)
                for seg in SEGS:
                    p1 = f"{seg}_P1"; p2 = f"{seg}_P2"
                    if p1 in df.columns and p2 in df.columns:
                        df.insert(df.columns.get_loc(p2)+1, seg, df[p1]+df[p2])
                if not show_wk:
                    df = df.drop(columns=[c for c in df.columns
                                          if isinstance(c, str) and (
                                              (c.startswith("WW") and c[2:].isdigit()) or
                                              ("-W" in c)
                                          )], errors="ignore")
                num_cols = df.select_dtypes(include="number").columns.tolist()
                df["_sort"] = df[num_cols].sum(axis=1)
                df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"])
                num_cols2 = df.select_dtypes(include="number").columns
                tot = df[num_cols2].sum().to_frame().T.round(0)
                tot.insert(0, group_col, "TOTAL")
                return pd.concat([df, tot], ignore_index=True)

            u_df = _prepare(units_df)
            c_df = _prepare(count_df)

            act_label = "KWh" if device == "IQ Battery" else "Units Activated"
            _dev_slug = device.replace(" ", "_")

            # ── CSS: ChannelIQ dark-themed drill buttons ─────────────────────
            st.markdown("""
<style>
div.drill-grid button {
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 6px !important;
    background: #1F2937 !important;
    color: #D1D5DB !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    min-height: 34px !important;
    padding: 4px 6px !important;
    transition: all 0.15s !important;
}
div.drill-grid button:hover {
    background: rgba(255,107,0,0.12) !important;
    color: #FF6B00 !important;
    border-color: rgba(255,107,0,0.35) !important;
}
</style>
""", unsafe_allow_html=True)

            # shared helper: build drill detail dataframe
            def _build_detail(drp_grp, drp_col):
                _dt, _ds, _dp = None, None, None
                if drp_col in TIERS:
                    _dt = drp_col
                elif drp_col in SEGS:
                    _ds = drp_col
                elif any(drp_col == f"{s}_{p}" for s in SEGS for p in ("P1","P2")):
                    _ds, _dp = drp_col.rsplit("_", 1)
                _dm = master_f.copy()
                if group_col == "Installer_Country":
                    _dm = _dm[_dm["Installer_Country"] == drp_grp]
                else:
                    _dm = _dm[_dm["RSMs"] == drp_grp]
                if _dt: _dm = _dm[_dm["Installer_Group"] == _dt]
                if _ds: _dm = _dm[_dm["Installer_Category"] == _ds]
                if _dp: _dm = _dm[_dm["Priority"] == _dp]
                _vc = "KWh" if device == "IQ Battery" else "Number of devices"
                _drd = df_raw_f[
                    df_raw_f["join_key"].isin(_dm["join_key"]) &
                    (df_raw_f["Device Type"] == device)
                ].copy() if df_raw_f is not None else pd.DataFrame()
                if not _drd.empty and _vc not in _drd.columns:
                    _vc = "Number of devices"
                _kc = [c for c in [
                    "join_key","Installer_Country","Installer_Mapped","RSMs",
                    "Installer State","Installer_State_X","Installer City",
                    "Top_Disti_1","Top_Disti_2","Installer_Category",
                    "Installer_Group","Priority","Installer_Overview",
                    "Support Emai","Account Phone",
                ] if c in _dm.columns]
                _det = _dm[_kc].copy()
                if not _drd.empty and all_5q:
                    _drd[_vc] = pd.to_numeric(_drd[_vc], errors="coerce").fillna(0)
                    _drd = _drd[_drd["Quarter"].isin(all_5q)]
                    _qpv = (_drd.groupby(["join_key","Quarter"])[_vc]
                            .sum().unstack(fill_value=0).reset_index())
                    _qpv.columns = (["join_key"] +
                                    [quarter_label(c) for c in _qpv.columns[1:]])
                    _qpv["Total"] = _qpv.iloc[:,1:].sum(axis=1)
                    _det = _det.merge(_qpv, on="join_key", how="left").fillna(0)
                    _det = _det.sort_values("Total", ascending=False)
                _det = _det.drop(columns=["join_key"], errors="ignore")
                _det = _det.rename(columns={
                    "Installer_Country":"Country","Installer_Mapped":"Installer",
                    "RSMs":"RSM","Installer State":"State Code",
                    "Installer_State_X":"State","Installer City":"City",
                    "Top_Disti_1":"Disti 1","Top_Disti_2":"Disti 2",
                    "Installer_Category":"Segment","Installer_Group":"Tier",
                    "Installer_Overview":"Overview","Support Emai":"Email",
                    "Account Phone":"Phone",
                })
                return _det

            def _render_drill_result(container, drp_grp, drp_col, tbl_key):
                _det = _build_detail(drp_grp, drp_col)
                with container:
                    st.divider()
                    _hc, _cc = st.columns([9, 1])
                    _hc.success(
                        f"\U0001f50d **{drp_grp} \u00b7 "
                        f"{drp_col.replace('_',' ')} \u00b7 {device}**"
                        f" \u2014 **{len(_det):,} installers**"
                    )
                    if _cc.button("\u2715 Clear", key=f"{tbl_key}_clr"):
                        st.session_state.pop(f"{tbl_key}_sel", None)
                        st.rerun()
                    _ncd = {c: st.column_config.NumberColumn(c, format="%,d")
                            for c in _det.select_dtypes("number").columns}
                    st.dataframe(_det.reset_index(drop=True),
                                 use_container_width=True, hide_index=True,
                                 column_config=_ncd,
                                 height=min(500,(len(_det)+1)*36+40),
                                 key=f"{tbl_key}_res")
                    _sdl1, _sdl2 = st.columns(2)
                    with _sdl1:
                        st.download_button(
                            "\u2b07\ufe0f Download CSV",
                            _det.to_csv(index=False).encode(),
                            f"drill_{drp_grp}_{drp_col}_{device}.csv",
                            key=f"{tbl_key}_resdl",
                        )
                    with _sdl2:
                        _sxl = io.BytesIO()
                        _det.to_excel(_sxl, index=False, engine="openpyxl")
                        st.download_button(
                            "\u2b07\ufe0f Download Excel",
                            _sxl.getvalue(),
                            f"drill_{drp_grp}_{drp_col}_{device}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"{tbl_key}_resdlx",
                        )

            def _fmt_k(n):
                """Format number as compact K/M with no wrapping."""
                try:
                    n = float(n)
                except (TypeError, ValueError):
                    return "0"
                if abs(n) >= 1_000_000:
                    return f"{n/1_000_000:.1f}M"
                if abs(n) >= 1_000:
                    return f"{n/1_000:.0f}K"
                return str(int(n))

            def _drill_grid(src_df, tbl_label, tbl_key, dl_fname, is_count=False):
                """Scrollable st.dataframe display + compact click grid below."""
                _click_cols = [c for c in TIERS + SEGS if c in src_df.columns]
                _body = src_df[src_df[group_col] != "TOTAL"]
                _ss_key = f"{tbl_key}_drillsel"

                # ── label + export button ─────────────────────────────────────
                _hc, _ec = st.columns([8, 1])
                _hc.markdown(f"**{tbl_label}**")
                _ec.download_button(
                    "\u2b07\ufe0f Export", src_df.to_csv(index=False).encode(),
                    dl_fname, key=f"{tbl_key}_dl")

                # ── nice scrollable table — first column frozen like Excel ──────
                _sticky_table(
                    src_df.reset_index(drop=True),
                    height=min(480, (len(src_df) + 1) * 38 + 40),
                )

                # ── collapsible click grid (Tiers + Segs, 8 cols max) ────────
                _is_expanded = st.session_state.get(_ss_key) is not None
                with st.expander(
                    "\U0001f50d **Drill down — click any number**",
                    expanded=_is_expanded,
                ):
                    _ncols = len(_click_cols)
                    _ratios = [1.5] + [1] * _ncols

                    # header
                    _hdr = st.columns(_ratios)
                    _hdr[0].markdown(
                        f"<span style='font-size:11px;font-weight:700;"
                        f"color:#6b7280'>{group_label}</span>",
                        unsafe_allow_html=True)
                    for _i, _cn in enumerate(_click_cols):
                        _hdr[_i + 1].markdown(
                            f"<div style='text-align:center;font-size:11px;"
                            f"font-weight:700;color:#374151'>{_cn}</div>",
                            unsafe_allow_html=True)

                    # rows
                    st.markdown('<div class="drill-grid">', unsafe_allow_html=True)
                    for _, _row in _body.iterrows():
                        _gv = str(_row[group_col])
                        _r = st.columns(_ratios)
                        _r[0].markdown(
                            f"<span style='font-size:13px;font-weight:700'>"
                            f"{_gv}</span>",
                            unsafe_allow_html=True)
                        for _i, _cn in enumerate(_click_cols):
                            _v = _fmt_k(_row.get(_cn, 0))
                            if _r[_i + 1].button(
                                _v,
                                key=f"{tbl_key}_{_gv}_{_cn}",
                                use_container_width=True,
                            ):
                                st.session_state[_ss_key] = {"grp": _gv, "col": _cn}
                    st.markdown('</div>', unsafe_allow_html=True)

                # Show drill result
                _sel = st.session_state.get(_ss_key)
                if _sel:
                    _det = _build_detail(_sel["grp"], _sel["col"])
                    st.divider()
                    _hc, _xc = st.columns([9, 1])
                    _hc.success(
                        f"\U0001f50d **{_sel['grp']} \u00b7 "
                        f"{_sel['col'].replace('_',' ')} \u00b7 {device}**"
                        f" \u2014 **{len(_det):,} installers**"
                    )
                    if _xc.button("\u2715 Clear", key=f"{tbl_key}_clr"):
                        st.session_state.pop(_ss_key, None)
                        st.rerun()
                    _det_disp = _det.reset_index(drop=True).copy()
                    if "Email" in _det_disp.columns:
                        _det_disp["\U0001f4e7"] = _det_disp["Email"].apply(
                            lambda e: (
                                f"mailto:{str(e).strip()}"
                                if pd.notna(e) and str(e).strip()
                                   and str(e).strip().lower() not in ("", "nan", "none")
                                else None
                            )
                        )
                    _ncd = {c: st.column_config.NumberColumn(c, format="%,d")
                            for c in _det_disp.select_dtypes("number").columns}
                    if "\U0001f4e7" in _det_disp.columns:
                        _ncd["\U0001f4e7"] = st.column_config.LinkColumn(
                            "\U0001f4e7 Mail", display_text="\U0001f4e7",
                            help="Click to open email client")
                    st.dataframe(_det_disp,
                                 use_container_width=True, hide_index=True,
                                 column_config=_ncd,
                                 height=min(500, (len(_det_disp)+1)*36+40),
                                 key=f"{tbl_key}_res")
                    st.download_button(
                        "\u2b07\ufe0f Export drill-down",
                        _det.to_csv(index=False).encode(),
                        f"drill_{_sel['grp']}_{_sel['col']}_{device}.csv",
                        key=f"{tbl_key}_resdl",
                    )

            # ── Units table + drill grid ──────────────────────────────────────
            _drill_grid(
                u_df,
                f"\U0001f4ca {act_label} \u2014 by Segment \u00d7 Priority",
                f"{table_key_prefix}_{_dev_slug}_u_tbl",
                f"acts_{device}_{group_col}_{filter_val or 'all'}.csv",
            )

            st.divider()

            # ── Count table + drill grid ──────────────────────────────────────
            _drill_grid(
                c_df,
                "\U0001f477 Installer Count \u2014 by Segment \u00d7 Priority",
                f"{table_key_prefix}_{_dev_slug}_c_tbl",
                f"cnt_{device}_{group_col}_{filter_val or 'all'}.csv",
                is_count=True,
            )



# ── Visual panel helpers ──────────────────────────────────────────────────────

def _fmt(n: float) -> str:
    """Format a number as 1.2K / 3.4M / 5.6B for display in metric cards."""
    n = float(n)
    if abs(n) >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{int(n)}"


_FOCUS_DEVICES = ["Microinverter", "IQ Battery", "EVSE"]
_DEVICE_LABEL  = {"Microinverter": "Microinverter",
                  "IQ Battery":    "Storage (KWh)",
                  "EVSE":          "EVSE"}
_DEVICE_COLOR  = {"Microinverter": "#F59E0B",
                  "Storage (KWh)": "#3B82F6",
                  "EVSE":          "#10B981"}


def _device_units_panel(df_raw: pd.DataFrame, master: pd.DataFrame, all_5q: list,
                        scope_label: str, key_suffix: str = "a"):
    """Left panel — enhanced bar+line chart with annotations and QoQ badge."""
    df_5q = df_raw[df_raw["Quarter"].isin(all_5q)].copy()
    overlap = [c for c in ["Installer_Country", "RSMs"] if c in df_5q.columns]
    df_5q = df_5q.drop(columns=overlap, errors="ignore")
    df_5q = df_5q.merge(master[["join_key"]], on="join_key", how="inner")
    df_5q = df_5q[df_5q["Device Type"].isin(_FOCUS_DEVICES)].copy()
    if df_5q.empty:
        st.info("No data for Microinverter / IQ Battery / EVSE in this scope.")
        return

    q_sorted   = sort_quarters(list(all_5q))
    q_lbl_map  = {q: quarter_label(q) for q in q_sorted}
    q_order    = [q_lbl_map[q] for q in q_sorted]
    last_idx   = len(q_order) - 1

    # ── Compute per-device quarterly values ──────────────────────────────────
    dev_vals = {}
    for dev in _FOCUS_DEVICES:
        df_dev = df_5q[df_5q["Device Type"] == dev]
        if dev == "IQ Battery":
            kwh_col = "KWh" if "KWh" in df_dev.columns else "Number of devices"
            grp = df_dev.groupby("Quarter")[kwh_col].sum().reindex(q_sorted).fillna(0)
        else:
            grp = df_dev.groupby("Quarter")["Number of devices"].sum().reindex(q_sorted).fillna(0)
        dev_vals[dev] = list(grp.values)

    # ── Total activations trend + QoQ badge ──────────────────────────────────
    total_vals = [
        a + b + c
        for a, b, c in zip(
            dev_vals["Microinverter"],
            dev_vals["IQ Battery"],
            dev_vals["EVSE"],
        )
    ]
    qoq_txt, qoq_color = "", "#34D399"
    if len(total_vals) >= 2 and total_vals[-2] > 0:
        pct = (total_vals[-1] - total_vals[-2]) / total_vals[-2] * 100
        sign = "+" if pct >= 0 else ""
        qoq_color = "#34D399" if pct >= 0 else "#F87171"
        qoq_txt = f"{sign}{pct:.1f}%"

    title_html = (
        f"Product Activations — {scope_label}"
        + (f'  <span style="font-size:12px;color:{qoq_color}"> QoQ {qoq_txt}</span>'
           if qoq_txt else "")
    )

    # ── Bar colors: fade older quarters, orange-tint latest ─────────────────
    _BAR_BASE   = {"Microinverter": "#F59E0B", "Storage (KWh)": "#3B82F6", "EVSE": "#10B981"}
    _BAR_LATEST = {"Microinverter": "#EA6100", "Storage (KWh)": "#1D4ED8", "EVSE": "#059669"}
    _BAR_OLD    = {"Microinverter": "#FCD34D", "Storage (KWh)": "#93C5FD", "EVSE": "#6EE7B7"}

    fig = go.Figure()

    for dev in _FOCUS_DEVICES:
        lbl = _DEVICE_LABEL[dev]
        vals = dev_vals[dev]
        bar_colors = [
            _BAR_LATEST[lbl] if i == last_idx
            else (_BAR_OLD[lbl] if i < last_idx - 1 else _BAR_BASE[lbl])
            for i in range(len(q_order))
        ]
        text_vals = [_fmt(v) if v > 0 else "" for v in vals]
        fig.add_trace(go.Bar(
            name=lbl, x=q_order, y=vals,
            marker_color=bar_colors, marker_line_width=0,
            text=text_vals, textposition="outside",
            textfont=dict(size=9, color="#374151",
                          family="'DM Mono',monospace"),
            hovertemplate=f"<b>{lbl}</b><br>%{{x}}: <b>%{{y:,.0f}}</b><extra></extra>",
        ))

    # Total activations trend line overlay
    fig.add_trace(go.Scatter(
        x=q_order, y=total_vals,
        mode="lines+markers",
        name="Total trend",
        line=dict(color="#7B5EA7", width=2.5, dash="dot"),
        marker=dict(size=7, color="#7B5EA7",
                    line=dict(color="#fff", width=1.5)),
        hovertemplate="<b>Total</b><br>%{x}: <b>%{y:,.0f}</b><extra></extra>",
        showlegend=True,
    ))

    # Shade latest quarter
    if q_order:
        fig.add_vrect(
            x0=last_idx - 0.45, x1=last_idx + 0.45,
            fillcolor="rgba(234,97,0,0.05)", layer="below", line_width=0,
        )

    fig.update_layout(
        barmode="group",
        title=dict(text=title_html,
                   font=dict(size=13, color="#3C3C3C",
                             family="'Enphase Visuelt','Helvetica Neue',Arial,sans-serif"),
                   x=0, xanchor="left"),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FAFAFA",
        height=330,
        margin=dict(t=44, b=0, l=0, r=0),
        legend=dict(orientation="h", y=-0.22, font=dict(size=10, color="#3C3C3C")),
        xaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(family="'DM Mono',monospace", size=11, color="#3C3C3C")),
        yaxis=dict(showgrid=True, gridcolor="#F0EFED", zeroline=False,
                   tickfont=dict(family="'DM Mono',monospace", size=10, color="#9CA3AF"),
                   tickformat=",d"),
        font=dict(family="'DM Mono',monospace"),
        bargap=0.22, bargroupgap=0.06,
    )
    st.plotly_chart(fig, use_container_width=True, key=f"dev_trend_{key_suffix}")

    # ── KPI metric cards ─────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    _card_meta = {
        "Microinverter": ("Microinverter", "#EA6100", "#FFF7ED", "#FDBA74", "units"),
        "IQ Battery":    ("Storage",       "#3B82F6", "#EFF6FF", "#93C5FD", "KWh"),
        "EVSE":          ("EVSE",          "#10B981", "#F0FDF4", "#6EE7B7", "units"),
    }
    for col, dev in zip([c1, c2, c3], _FOCUS_DEVICES):
        lbl, accent, bg, border, unit = _card_meta[dev]
        df_dev = df_5q[df_5q["Device Type"] == dev]
        if dev == "IQ Battery":
            kwh_col = "KWh" if "KWh" in df_dev.columns else "Number of devices"
            val = df_dev[kwh_col].sum()
        else:
            val = df_dev["Number of devices"].sum()
        col.markdown(
            f'<div style="background:{bg};border-radius:10px;padding:10px 12px;'
            f'border:1px solid {border};text-align:center">'
            f'<div style="color:{accent};font-size:10px;font-weight:700;'
            f'letter-spacing:0.06em;text-transform:uppercase;margin-bottom:4px">{lbl}</div>'
            f'<div style="color:#111827;font-size:1.7rem;font-weight:800;'
            f'line-height:1.1;font-family:\'DM Mono\',monospace">{_fmt(val)}</div>'
            f'<div style="color:#9CA3AF;font-size:10px;margin-top:2px">'
            f'{int(val):,} {unit}</div></div>',
            unsafe_allow_html=True,
        )


def _installer_count_panel(master: pd.DataFrame, scope_label: str, key_suffix: str = "a"):
    """Right panel: enhanced donut with center annotation + value-labelled tier bar."""
    _total  = len(master)
    _active = int((master["Installer_Category"] != "Lost").sum())
    _lost   = _total - _active

    # ── Segment donut with center annotation ─────────────────────────────────
    seg = master["Installer_Category"].value_counts().reset_index()
    seg.columns = ["Segment", "Count"]

    fig_seg = go.Figure(go.Pie(
        labels=seg["Segment"], values=seg["Count"],
        hole=0.54,
        marker=dict(
            colors=[SEG_COLORS.get(s, "#94A3B8") for s in seg["Segment"]],
            line=dict(color="#FFFFFF", width=2),
        ),
        textinfo="percent",
        textfont=dict(size=11, family="'DM Mono',monospace"),
        hovertemplate="<b>%{label}</b><br>%{value:,} installers (%{percent})<extra></extra>",
        sort=False,
    ))
    # Center annotation: total count
    fig_seg.add_annotation(
        text=f"<b>{_total:,}</b><br><span style='font-size:10px'>Total</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="#111827",
                  family="'Enphase Visuelt','Helvetica Neue',Arial,sans-serif"),
        align="center",
    )
    fig_seg.update_layout(
        title=dict(text=f"Installer Portfolio — {scope_label}",
                   font=dict(size=13, color="#3C3C3C",
                             family="'Enphase Visuelt','Helvetica Neue',Arial,sans-serif"),
                   x=0, xanchor="left"),
        paper_bgcolor="#FFFFFF", height=280,
        margin=dict(t=44, b=0, l=0, r=0),
        legend=dict(orientation="h", y=-0.12,
                    font=dict(size=10, color="#3C3C3C")),
        showlegend=True,
    )
    st.plotly_chart(fig_seg, use_container_width=True, key=f"ins_seg_{key_suffix}")

    # ── Segment health mini-cards ────────────────────────────────────────────
    _seg_meta = [
        ("Growing",  "#22C55E", "#F0FDF4", "#BBF7D0"),
        ("New",      "#3B82F6", "#EFF6FF", "#BFDBFE"),
        ("Declining","#F97316", "#FFF7ED", "#FED7AA"),
        ("Lost",     "#EF4444", "#FFF5F5", "#FCA5A5"),
    ]
    cols = st.columns(len(_seg_meta))
    for c, (seg_name, accent, bg, border) in zip(cols, _seg_meta):
        n = int((master["Installer_Category"] == seg_name).sum())
        pct = n / _total * 100 if _total else 0
        c.markdown(
            f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
            f'padding:7px 6px;text-align:center">'
            f'<div style="color:{accent};font-size:9px;font-weight:700;'
            f'letter-spacing:0.05em;text-transform:uppercase">{seg_name}</div>'
            f'<div style="color:#111827;font-size:1.1rem;font-weight:800;'
            f'line-height:1.2;font-family:\'DM Mono\',monospace">{n:,}</div>'
            f'<div style="color:#9CA3AF;font-size:9px">{pct:.0f}%</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Tier horizontal bar with value labels ────────────────────────────────
    active = master[master["Installer_Group"] != "Lost"]
    tier_order = ["Diamond", "Platinum", "Golden", "Silver"]
    tier_counts = (active["Installer_Group"]
                   .value_counts().reindex(tier_order).fillna(0).astype(int))

    fig_tier = go.Figure(go.Bar(
        x=list(tier_counts.values),
        y=tier_order,
        orientation="h",
        marker_color=[TIER_COLORS.get(t, "#94A3B8") for t in tier_order],
        marker_line_width=0,
        text=[f"{v:,}" for v in tier_counts.values],
        textposition="outside",
        textfont=dict(size=10, color="#374151",
                      family="'DM Mono',monospace"),
        hovertemplate="<b>%{y}</b>: %{x:,} installers<extra></extra>",
    ))
    fig_tier.update_layout(
        title=dict(text="Active Installers by Tier",
                   font=dict(size=12, color="#3C3C3C",
                             family="'Enphase Visuelt','Helvetica Neue',Arial,sans-serif"),
                   x=0, xanchor="left"),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FAFAFA",
        height=200,
        margin=dict(t=38, b=0, l=0, r=40),
        xaxis=dict(showgrid=True, gridcolor="#F0EFED", zeroline=False,
                   tickfont=dict(family="'DM Mono',monospace", size=9, color="#9CA3AF")),
        yaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(family="'DM Mono',monospace", size=11, color="#3C3C3C")),
        font=dict(family="'DM Mono',monospace"),
        showlegend=False,
    )
    st.plotly_chart(fig_tier, use_container_width=True, key=f"ins_tier_{key_suffix}")


def _scope_filters(master, df_raw, scope_key: str, user_country: str, user_rsm: str):
    """Returns (m_scoped, df_scoped, scope_label) based on tab filters."""
    all_countries = sorted(master["Installer_Country"].dropna().unique())
    all_rsms      = sorted(master["RSMs"].dropna().unique())

    col_c, col_r = st.columns(2)
    with col_c:
        def_c = user_country if user_country in all_countries else "All"
        sel_c = st.selectbox("Country", ["All"] + list(all_countries),
                             index=(["All"]+list(all_countries)).index(def_c),
                             key=f"sc_{scope_key}")
    with col_r:
        def_r = user_rsm if user_rsm in all_rsms else "All"
        sel_r = st.selectbox("RSM", ["All"] + list(all_rsms),
                             index=(["All"]+list(all_rsms)).index(def_r),
                             key=f"sr_{scope_key}")

    m = master.copy()
    if sel_c != "All":
        m = m[m["Installer_Country"] == sel_c]
    if sel_r != "All":
        m = m[m["RSMs"] == sel_r]

    df = df_raw[df_raw["join_key"].isin(m["join_key"])].copy()
    label = " / ".join(filter(lambda x: x != "All", [sel_c, sel_r])) or "All"
    return m, df, label


def render_summary(df_raw: pd.DataFrame, master: pd.DataFrame,
                   all_5q: list, role: str,
                   user_country: str = "", user_rsm: str = ""):
    st.subheader("📊 Summary View")

    sub1, sub2 = st.tabs(["🌍 Country Level", "👤 RSM Level"])

    # ── Country Level visual ──────────────────────────────────────────────────
    with sub1:
        all_countries = sorted(master["Installer_Country"].dropna().unique())
        default_c = [user_country] if user_country in all_countries else []
        sel_c = st.multiselect(
            "🌍 Country", all_countries, default=default_c, key="sum_c1",
            placeholder="Search and select country…"
        )
        m_c = master[master["Installer_Country"].isin(sel_c)] if sel_c else master
        df_c = df_raw[df_raw["join_key"].isin(m_c["join_key"])]
        label_c = ", ".join(sel_c) if sel_c else "All Countries"

        col_dev, col_ins = st.columns(2)
        with col_dev:
            _device_units_panel(df_c, m_c, all_5q, label_c, key_suffix="ctry")
        with col_ins:
            _installer_count_panel(m_c, label_c, key_suffix="ctry")

        st.divider()
        st.markdown("##### 📊 Activation & Installer Count Tables (by Device Type)")
        _render_summary_tables(
            df_raw, master, all_5q,
            "Installer_Country", "Country",
            filter_val=(sel_c[0] if len(sel_c) == 1 else None),
            table_key_prefix="ctry"
        )

    # ── RSM Level visual ──────────────────────────────────────────────────────
    with sub2:
        all_rsms = sorted(master["RSMs"].dropna().unique())
        default_r = [user_rsm] if user_rsm in all_rsms else []
        sel_r = st.multiselect(
            "👤 RSM", all_rsms, default=default_r, key="sum_r1",
            placeholder="Search and select RSM…"
        )
        m_r = master[master["RSMs"].isin(sel_r)] if sel_r else master
        df_r = df_raw[df_raw["join_key"].isin(m_r["join_key"])]
        label_r = ", ".join(sel_r) if sel_r else "All RSMs"

        col_dev2, col_ins2 = st.columns(2)
        with col_dev2:
            _device_units_panel(df_r, m_r, all_5q, label_r, key_suffix="rsm")
        with col_ins2:
            _installer_count_panel(m_r, label_r, key_suffix="rsm")

        st.divider()
        st.markdown("##### 📊 Activation & Installer Count Tables (by Device Type)")
        _render_summary_tables(
            df_raw, master, all_5q,
            "RSMs", "RSM",
            filter_val=(sel_r[0] if len(sel_r) == 1 else None),
            table_key_prefix="rsm"
        )

    # ── Installer Heatmap — Country Breakdown (collapsible) ───────────────────
    _HMAP_SEG_ORDER = ["Lost", "Declining", "Stable", "Growing", "New"]
    _HMAP_VALID_CTRY = {
        "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES",
        "FI", "FR", "GB", "GR", "HR", "HU", "IE", "IT", "LT", "LU",
        "LV", "MT", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK",
    }
    with st.expander("📊 Installer Heatmap — Country Breakdown", expanded=False):
        st.markdown(
            "<div style='font-size:12px;color:#7D7D7D;margin-bottom:14px'>"
            "Each cell shows the number of installers per country."
            "</div>",
            unsafe_allow_html=True,
        )
        hmap_c1, hmap_c2 = st.columns(2)

        with hmap_c1:
            pivot_seg = (
                master.groupby(["Installer_Country", "Installer_Category"])
                .size().reset_index(name="Count")
                .pivot(index="Installer_Country", columns="Installer_Category", values="Count")
                .fillna(0).astype(int)
            )
            pivot_seg = pivot_seg.loc[pivot_seg.sum(axis=1).sort_values(ascending=False).index]
            pivot_seg = pivot_seg[pivot_seg.index.str.strip().str.upper().isin(_HMAP_VALID_CTRY)]
            _seg_row_totals = pivot_seg.sum(axis=1)
            _mt_min = int(_seg_row_totals.get("MT", _seg_row_totals.min() if not _seg_row_totals.empty else 0))
            pivot_seg = pivot_seg[_seg_row_totals >= _mt_min]
            seg_cols = [c for c in _HMAP_SEG_ORDER if c in pivot_seg.columns]
            pivot_seg = pivot_seg[seg_cols]
            n_rows_seg = len(pivot_seg)
            fig_seg = go.Figure(go.Heatmap(
                z=pivot_seg.values,
                x=pivot_seg.columns.tolist(),
                y=pivot_seg.index.tolist(),
                text=pivot_seg.values,
                texttemplate="<b>%{text}</b>",
                textfont={"size": 12, "color": "#3C3C3C",
                          "family": "'DM Mono','IBM Plex Mono',monospace"},
                colorscale=[[0, "#FAFAFA"], [0.15, "#FDEBD0"],
                            [0.5, "#F5A623"], [1.0, "#C85400"]],
                showscale=True,
                colorbar=dict(thickness=10, len=0.6, x=1.01,
                              tickfont=dict(size=9, family="'DM Mono',monospace"),
                              outlinewidth=0),
                xgap=3, ygap=3,
                hovertemplate="<b>%{y}</b> \u00b7 <b>%{x}</b><br>%{text} installers<extra></extra>",
            ))
            fig_seg.update_layout(
                title=dict(text="Country \u00d7 Segment",
                           font=dict(size=13, color="#3C3C3C",
                                     family="'Enphase Visuelt','Helvetica Neue',Arial,sans-serif"),
                           x=0, xanchor="left", y=0.98, yanchor="top"),
                margin=dict(l=0, r=30, t=78, b=10),
                paper_bgcolor="#FFFFFF", plot_bgcolor="#F4F3F0",
                font=dict(family="'DM Mono','IBM Plex Mono',monospace", color="#3C3C3C", size=11),
                xaxis=dict(tickfont=dict(size=11, color="#3C3C3C", family="'DM Mono',monospace"),
                           side="top", showgrid=False, zeroline=False),
                yaxis=dict(tickfont=dict(size=10, color="#3C3C3C"), autorange="reversed",
                           showgrid=False, zeroline=False),
                height=max(320, n_rows_seg * 30 + 100),
            )
            _chart_h_seg = max(320, n_rows_seg * 30 + 100)
            _row_h_seg = (_chart_h_seg - 88) / max(n_rows_seg, 1)
            _seg_totals = [int(pivot_seg.loc[c, seg_cols].sum()) for c in pivot_seg.index]
            _tot_html_seg = "".join(
                f'<div style="height:{_row_h_seg:.1f}px;display:flex;align-items:center;'
                f'justify-content:flex-end;font-size:11px;font-weight:700;'
                f'color:#1E293B;font-family:\'DM Mono\',monospace;'
                f'padding-right:4px">{t:,}</div>'
                for t in _seg_totals
            )
            _sc1, _sc2 = st.columns([11, 1])
            with _sc1:
                st.plotly_chart(fig_seg, use_container_width=True, key="sum_hmap_seg")
            with _sc2:
                st.markdown(
                    f'<div style="margin-top:62px">'
                    f'<div style="font-size:9px;font-weight:700;color:#7D7D7D;'
                    f'font-family:\'DM Mono\',monospace;text-align:right;'
                    f'padding-right:4px;margin-bottom:2px">Total</div>'
                    f'{_tot_html_seg}</div>',
                    unsafe_allow_html=True,
                )

        with hmap_c2:
            tier_data = master[master["Installer_Group"].isin(TIERS)]
            if not tier_data.empty:
                pivot_tier = (
                    tier_data.groupby(["Installer_Country", "Installer_Group"])
                    .size().reset_index(name="Count")
                    .pivot(index="Installer_Country", columns="Installer_Group", values="Count")
                    .fillna(0).astype(int)
                )
                pivot_tier = pivot_tier.loc[
                    pivot_tier.sum(axis=1).sort_values(ascending=False).index]
                pivot_tier = pivot_tier[pivot_tier.index.str.strip().str.upper().isin(_HMAP_VALID_CTRY)]
                _tier_row_totals = pivot_tier.sum(axis=1)
                _mt_min_t = int(_tier_row_totals.get("MT", _tier_row_totals.min() if not _tier_row_totals.empty else 0))
                pivot_tier = pivot_tier[_tier_row_totals >= _mt_min_t]
                tier_cols = [c for c in TIERS if c in pivot_tier.columns]
                pivot_tier = pivot_tier[tier_cols]
                n_rows_tier = len(pivot_tier)
                fig_tier = go.Figure(go.Heatmap(
                    z=pivot_tier.values,
                    x=pivot_tier.columns.tolist(),
                    y=pivot_tier.index.tolist(),
                    text=pivot_tier.values,
                    texttemplate="<b>%{text}</b>",
                    textfont={"size": 12, "color": "#3C3C3C",
                              "family": "'DM Mono','IBM Plex Mono',monospace"},
                    colorscale=[[0, "#FAFAFA"], [0.15, "#D6EAF8"],
                                [0.5, "#2E86C1"], [1.0, "#1B4F72"]],
                    showscale=True,
                    colorbar=dict(thickness=10, len=0.6, x=1.01,
                                  tickfont=dict(size=9, family="'DM Mono',monospace"),
                                  outlinewidth=0),
                    xgap=3, ygap=3,
                    hovertemplate="<b>%{y}</b> \u00b7 <b>%{x}</b><br>%{text} installers<extra></extra>",
                ))
                fig_tier.update_layout(
                    title=dict(text="Country \u00d7 Tier",
                               font=dict(size=13, color="#3C3C3C",
                                         family="'Enphase Visuelt','Helvetica Neue',Arial,sans-serif"),
                               x=0, xanchor="left", y=0.98, yanchor="top"),
                    margin=dict(l=0, r=30, t=78, b=10),
                    paper_bgcolor="#FFFFFF", plot_bgcolor="#F4F3F0",
                    font=dict(family="'DM Mono','IBM Plex Mono',monospace", color="#3C3C3C", size=11),
                    xaxis=dict(tickfont=dict(size=11, color="#3C3C3C", family="'DM Mono',monospace"),
                               side="top", showgrid=False, zeroline=False),
                    yaxis=dict(tickfont=dict(size=10, color="#3C3C3C"), autorange="reversed",
                               showgrid=False, zeroline=False),
                    height=max(320, n_rows_tier * 30 + 100),
                )
                _chart_h_tier = max(320, n_rows_tier * 30 + 100)
                _row_h_tier = (_chart_h_tier - 88) / max(n_rows_tier, 1)
                _tier_totals = [int(pivot_tier.loc[c, tier_cols].sum()) for c in pivot_tier.index]
                _tot_html_tier = "".join(
                    f'<div style="height:{_row_h_tier:.1f}px;display:flex;align-items:center;'
                    f'justify-content:flex-end;font-size:11px;font-weight:700;'
                    f'color:#1E293B;font-family:\'DM Mono\',monospace;'
                    f'padding-right:4px">{t:,}</div>'
                    for t in _tier_totals
                )
                _tc1, _tc2 = st.columns([11, 1])
                with _tc1:
                    st.plotly_chart(fig_tier, use_container_width=True, key="sum_hmap_tier")
                with _tc2:
                    st.markdown(
                        f'<div style="margin-top:62px">'
                        f'<div style="font-size:9px;font-weight:700;color:#7D7D7D;'
                        f'font-family:\'DM Mono\',monospace;text-align:right;'
                        f'padding-right:4px;margin-bottom:2px">Total</div>'
                        f'{_tot_html_tier}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No tier data available.")

