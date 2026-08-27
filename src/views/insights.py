"""Actionable Insights view — helps sales team prioritise which installers to focus on."""

import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_ASP = {
    "Euro": {
        "2024-Q2": {"Microinverter": 141, "IQ Battery": 504},
        "2024-Q3": {"Microinverter": 153, "IQ Battery": 552},
        "2024-Q4": {"Microinverter": 134, "IQ Battery": 494},
        "2025-Q1": {"Microinverter": 156, "IQ Battery": 519},
        "2025-Q2": {"Microinverter": 166, "IQ Battery": 519},
        "2025-Q3": {"Microinverter": 161, "IQ Battery": 494},
        "2025-Q4": {"Microinverter": 167, "IQ Battery": 500},
        "2026-Q1": {"Microinverter": 168, "IQ Battery": 499},
        "2026-Q2": {"Microinverter": 177, "IQ Battery": 496},
        "2026-Q3": {"Microinverter": 173, "IQ Battery": 492},
        "2026-Q4": {"Microinverter": 174, "IQ Battery": 495},
        "2027-Q1": {"Microinverter": 174, "IQ Battery": 495},
    },
    "ANZP": {
        "2024-Q2": {"Microinverter": 106, "IQ Battery": 417},
        "2024-Q3": {"Microinverter": 109, "IQ Battery": 618},
        "2024-Q4": {"Microinverter": 121, "IQ Battery": 518},
        "2025-Q1": {"Microinverter": 112, "IQ Battery": 457},
        "2025-Q2": {"Microinverter": 112, "IQ Battery": 496},
        "2025-Q3": {"Microinverter": 124, "IQ Battery": 505},
        "2025-Q4": {"Microinverter": 126, "IQ Battery": 550},
        "2026-Q1": {"Microinverter": 129, "IQ Battery": 546},
        "2026-Q2": {"Microinverter": 126, "IQ Battery": 542},
        "2026-Q3": {"Microinverter": 126, "IQ Battery": 546},
        "2026-Q4": {"Microinverter": 124, "IQ Battery": 550},
        "2027-Q1": {"Microinverter": 124, "IQ Battery": 550},
    },
}

_SEG_COLOR = {
    "Lost":      "#DE2100",
    "Declining": "#EA6100",
    "Stable":    "#7D7D7D",
    "Growing":   "#439E58",
    "New":       "#3B82F6",
}
_TIER_ORDER = ["Diamond", "Platinum", "Golden", "Silver"]
_SEG_ORDER  = ["Lost", "Declining", "Stable", "Growing", "New"]

_VALID_EURO_COUNTRIES = {
    "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES",
    "FI", "FR", "GB", "GR", "HR", "HU", "IE", "IT", "LT", "LU",
    "LV", "MT", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK",
}


def _blended_asp(region: str, quarter: str) -> float:
    """Blended ASP for a region/quarter using Microinverter as proxy (most common product)."""
    r = _ASP.get(region, _ASP.get("Euro", {}))
    q = r.get(quarter, {})
    return float(q.get("Microinverter", 0))


def _build_rev_from_master(master: pd.DataFrame, q_list: list) -> pd.DataFrame:
    """Vectorised revenue per (join_key, Quarter) from master quarterly columns."""
    has_region = "Region" in master.columns
    frames = []
    for q in q_list:
        if q not in master.columns:
            continue
        tmp = master[["join_key"] + (["Region"] if has_region else []) + [q]].copy()
        tmp = tmp.rename(columns={q: "_qty"})
        tmp["Quarter"] = q
        if has_region:
            tmp["_asp"] = tmp["Region"].map(
                lambda r: _blended_asp(r, q)  # noqa: B023
            )
        else:
            tmp["_asp"] = _blended_asp("Euro", q)
        tmp["_rev"] = pd.to_numeric(tmp["_qty"], errors="coerce").fillna(0) * tmp["_asp"]
        frames.append(tmp[["join_key", "Quarter", "_rev"]])
    if not frames:
        return pd.DataFrame(columns=["join_key", "Quarter", "_rev"])
    return pd.concat(frames, ignore_index=True)


def _rev_for_keys(rev_lookup: pd.DataFrame, keys, quarters: list) -> float:
    if rev_lookup.empty or not quarters:
        return 0.0
    mask = rev_lookup["join_key"].isin(keys) & rev_lookup["Quarter"].isin(quarters)
    return float(rev_lookup.loc[mask, "_rev"].sum())


def _peak_rev_for_keys(rev_lookup: pd.DataFrame, keys, all_quarters: list) -> float:
    """Sum of each installer's best-quarter revenue — used for Lost revenue at risk."""
    if rev_lookup.empty or not all_quarters:
        return 0.0
    mask = rev_lookup["join_key"].isin(keys) & rev_lookup["Quarter"].isin(all_quarters)
    sub = rev_lookup.loc[mask]
    if sub.empty:
        return 0.0
    return float(sub.groupby("join_key")["_rev"].max().sum())


def _fmt_usd(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def _fmt_q(q: str) -> str:
    if not q:
        return ""
    yr, qn = q.split("-Q")
    return f"Q{qn}'{yr[2:]}"


def _alert_card(col, label: str, count: int, sub_line: str,
                action: str, color: str, bg: str, pct_str: str = ""):
    _pct_html = (
        f'<div style="font-size:18px;font-weight:700;color:{color};'
        f'font-family:\'DM Mono\',monospace;line-height:1;margin-bottom:8px">{pct_str}</div>'
        if pct_str else ""
    )
    col.markdown(f"""
<div style="background:{bg};border:1px solid {color};border-left:4px solid {color};
            border-radius:16px;padding:18px 20px;
            box-shadow:0 1px 3px rgba(60,60,60,0.07)">
  <div style="font-size:9px;font-weight:500;text-transform:uppercase;
              letter-spacing:0.15em;color:{color};
              font-family:'DM Mono','IBM Plex Mono',monospace;margin-bottom:8px">{label}</div>
  <div style="font-size:34px;font-weight:400;color:#3C3C3C;line-height:1.1;margin-bottom:2px">{count:,}</div>
  <div style="font-size:11px;color:#7D7D7D;margin-bottom:6px">installers</div>
  {_pct_html}
  <div style="font-size:12px;font-weight:500;color:{color};margin-bottom:4px">{sub_line}</div>
  <div style="font-size:10px;color:#7D7D7D;font-family:'DM Mono','IBM Plex Mono',monospace">{action}</div>
</div>""", unsafe_allow_html=True)


def _section_label(text: str):
    st.markdown(
        f"""<div style="font-size:9px;font-weight:500;text-transform:uppercase;
        letter-spacing:0.15em;color:#7D7D7D;
        font-family:'DM Mono','IBM Plex Mono',monospace;
        margin-bottom:10px;margin-top:4px">{text}</div>""",
        unsafe_allow_html=True,
    )


def render_insights(master: pd.DataFrame, df_raw: pd.DataFrame, q_list: list):
    if master.empty:
        st.info("No installer data available for the current selection.")
        return

    cq = q_list[-1] if q_list else None
    lq = q_list[-2] if len(q_list) >= 2 else cq
    cq_label = _fmt_q(cq)
    lq_label = _fmt_q(lq)

    # ── Counts ──────────────────────────────────────────────────────────────
    seg_counts = master["Installer_Category"].value_counts()
    n_lost      = int(seg_counts.get("Lost",      0))
    n_declining = int(seg_counts.get("Declining", 0))
    n_growing   = int(seg_counts.get("Growing",   0))
    n_new       = int(seg_counts.get("New",       0))
    total       = len(master)

    pri_counts = master["Priority"].value_counts()
    n_p1 = int(pri_counts.get("High", 0) or pri_counts.get("P1", 0))

    # ── Revenue — use master quarterly columns directly (avoids df_raw device-type issues) ──
    _rev_lkp = _build_rev_from_master(master, q_list)

    keys_lost      = master[master["Installer_Category"] == "Lost"]["join_key"]
    keys_declining = master[master["Installer_Category"] == "Declining"]["join_key"]
    keys_growing   = master[master["Installer_Category"] == "Growing"]["join_key"]
    keys_new       = master[master["Installer_Category"] == "New"]["join_key"]

    # Lost  → lq (Q1'26) units × lq ASP
    # Others → cq (Q2'26) units × cq ASP
    rev_lost_lq      = _rev_for_keys(_rev_lkp, keys_lost,      [lq] if lq else [])
    rev_dec_cq       = _rev_for_keys(_rev_lkp, keys_declining, [cq] if cq else [])
    rev_dec_lq       = _rev_for_keys(_rev_lkp, keys_declining, [lq] if lq else [])
    rev_growing_cq   = _rev_for_keys(_rev_lkp, keys_growing,   [cq] if cq else [])
    rev_new_cq       = _rev_for_keys(_rev_lkp, keys_new,       [cq] if cq else [])
    rev_dec_drop     = max(rev_dec_lq - rev_dec_cq, 0.0)

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="margin-bottom:20px">
  <div style="font-size:22px;font-weight:400;color:#3C3C3C;
              letter-spacing:-0.01em;margin-bottom:4px">Actionable Insights</div>
  <div style="font-size:10px;color:#7D7D7D;letter-spacing:0.15em;text-transform:uppercase;
              font-family:'DM Mono','IBM Plex Mono',monospace">
    {_fmt_q(q_list[0]) if len(q_list) > 1 else cq_label}–{cq_label} snapshot &nbsp;\u00b7&nbsp; {total:,} installers in view
  </div>
</div>""", unsafe_allow_html=True)

    # ── Alert strip ──────────────────────────────────────────────────────────
    _section_label("Where to focus")
    c1, c2, c3, c4 = st.columns(4)
    _p1_pct = f"{n_p1 / total * 100:.0f}%" if total else ""
    _alert_card(c1, "Lost installers", n_lost,
                f"{_fmt_usd(rev_lost_lq)} revenue at risk",
                "Based on last active quarter — re-engage to recover",
                "#DE2100", "#FFF8F7")
    _alert_card(c2, "Declining installers", n_declining,
                f"\u2193 {_fmt_usd(rev_dec_drop)} drop vs {lq_label}",
                "Re-engage before further churn",
                "#EA6100", "#FFF9F5")
    _alert_card(c3, "High priority (P1)", n_p1,
                "Flagged for immediate action",
                "Requires sales follow-up this quarter",
                "#7B5EA7", "#F9F7FD", pct_str=_p1_pct)
    _alert_card(c4, "New installers", n_new,
                f"{_fmt_usd(rev_new_cq)} {cq_label} revenue",
                "Growth opportunity \u2014 onboard & activate",
                "#439E58", "#F5FAF6")

    # ── Drill buttons under cards — navigate to All Devices tab ──────────────
    _db1, _db2, _db3, _db4 = st.columns(4)
    with _db1:
        if st.button("View Lost list \u2192", key="ins_drill_lost", use_container_width=True):
            st.session_state["active_tab"]       = "All Devices"
            st.session_state["il_seg"]           = "Lost"
            st.session_state["il_priority"]      = "All"
            st.session_state["ins_from_insights"] = True
            st.rerun()
    with _db2:
        if st.button("View Declining list \u2192", key="ins_drill_dec", use_container_width=True):
            st.session_state["active_tab"]       = "All Devices"
            st.session_state["il_seg"]           = "Declining"
            st.session_state["il_priority"]      = "All"
            st.session_state["ins_from_insights"] = True
            st.rerun()
    with _db3:
        if st.button("View P1 list \u2192", key="ins_drill_p1", use_container_width=True):
            st.session_state["active_tab"]       = "All Devices"
            st.session_state["il_seg"]           = "All"
            st.session_state["il_priority"]      = "P1"
            st.session_state["ins_from_insights"] = True
            st.rerun()
    with _db4:
        if st.button("View New list \u2192", key="ins_drill_new", use_container_width=True):
            st.session_state["active_tab"]       = "All Devices"
            st.session_state["il_seg"]           = "New"
            st.session_state["il_priority"]      = "All"
            st.session_state["ins_from_insights"] = True
            st.rerun()

    # ── Lost Installers — Pareto Focus ───────────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    _section_label("Lost installers \u2014 focus where it matters most (80/20)")

    _lost_m = master[master["Installer_Category"] == "Lost"].copy()
    if lq and lq in _lost_m.columns and not _lost_m.empty:
        _lost_m["_units"] = pd.to_numeric(_lost_m[lq], errors="coerce").fillna(0)
        _lost_m = _lost_m.sort_values("_units", ascending=False).reset_index(drop=True)
        _total_vol = _lost_m["_units"].sum()
        if _total_vol > 0:
            _lost_m["_cumpct"] = _lost_m["_units"].cumsum() / _total_vol * 100

            # Tier cut-offs: 80% and 95% cumulative volume
            _n1 = int((_lost_m["_cumpct"] >= 80).argmax()) + 1
            _n2 = int((_lost_m["_cumpct"] >= 95).argmax()) + 1 - _n1
            _n3 = len(_lost_m) - _n1 - _n2

            _t1 = _lost_m.iloc[:_n1]
            _t2 = _lost_m.iloc[_n1:_n1 + _n2]
            _t3 = _lost_m.iloc[_n1 + _n2:]

            _asp_lq = _blended_asp("Euro", lq)   # placeholder; revenue already in rev_lost_lq

            def _tier_rev(tdf):
                if "Region" not in tdf.columns:
                    return float(tdf["_units"].sum()) * _asp_lq
                total = 0.0
                for _reg, _grp in tdf.groupby("Region"):
                    _asp = _ASP.get(_reg, _ASP.get("Euro", {})).get(lq, {})
                    _asp_val = _asp.get("Microinverter", 0) if isinstance(_asp, dict) else 0
                    total += float(_grp["_units"].sum()) * _asp_val
                return total

            _t1_units = int(_t1["_units"].sum())
            _t2_units = int(_t2["_units"].sum())
            _t3_units = int(_t3["_units"].sum())
            _t1_rev = _tier_rev(_t1)
            _t2_rev = _tier_rev(_t2)
            _t3_rev = _tier_rev(_t3)
            _t1_pct_n = f"{_n1 / n_lost * 100:.0f}%"
            _t2_pct_n = f"{_n2 / n_lost * 100:.0f}%"
            _t3_pct_n = f"{_n3 / n_lost * 100:.0f}%"
            _t1_vol_pct = f"{_t1_units / _total_vol * 100:.0f}%"
            _t2_vol_pct = f"{_t2_units / _total_vol * 100:.0f}%"
            _t3_vol_pct = f"{_t3_units / _total_vol * 100:.0f}%"

            def _tier_card(col, emoji, label, color, n, pct_n, units, vol_pct, rev):
                col.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #DCDCD6;border-radius:14px;
            padding:16px 18px;border-left:4px solid {color}">
  <div style="font-size:10px;font-weight:600;color:{color};text-transform:uppercase;
              letter-spacing:0.12em;margin-bottom:8px">{emoji} {label}</div>
  <div style="font-size:26px;font-weight:300;color:#3C3C3C;line-height:1">{n:,}
    <span style="font-size:13px;color:#7D7D7D;font-weight:400">installers ({pct_n})</span>
  </div>
  <div style="margin-top:10px;display:flex;gap:18px">
    <div>
      <div style="font-size:11px;color:#7D7D7D">Volume ({lq_label})</div>
      <div style="font-size:15px;font-weight:500;color:#3C3C3C">{units:,} units
        <span style="font-size:11px;color:#7D7D7D">· {vol_pct} of lost</span>
      </div>
    </div>
    <div>
      <div style="font-size:11px;color:#7D7D7D">Revenue at risk</div>
      <div style="font-size:15px;font-weight:500;color:{color}">{_fmt_usd(rev)}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

            _pa, _pb, _pc = st.columns(3)
            _tier_card(_pa, "🔴", "Tier 1 — Critical", "#DE2100",
                       _n1, _t1_pct_n, _t1_units, _t1_vol_pct, _t1_rev)
            _tier_card(_pb, "🟠", "Tier 2 — Important", "#EA6100",
                       _n2, _t2_pct_n, _t2_units, _t2_vol_pct, _t2_rev)
            _tier_card(_pc, "⚪", "Tier 3 — Long tail", "#94A3B8",
                       _n3, _t3_pct_n, _t3_units, _t3_vol_pct, _t3_rev)

            # Drill buttons
            _da, _db, _dc = st.columns(3)
            _tier_keys = [
                ("ins_drill_lost_t1", _t1["join_key"].tolist(), "Tier 1 — Critical"),
                ("ins_drill_lost_t2", _t2["join_key"].tolist(), "Tier 2 — Important"),
                ("ins_drill_lost_t3", _t3["join_key"].tolist(), "Tier 3 — Long tail"),
            ]
            for _col, (_btn_key, _keys, _label) in zip([_da, _db, _dc], _tier_keys):
                with _col:
                    if st.button(f"View {_label} list \u2192",
                                 key=_btn_key, use_container_width=True):
                        st.session_state["active_tab"]          = "All Devices"
                        st.session_state["il_seg"]              = "Lost"
                        st.session_state["il_priority"]         = "All"
                        st.session_state["ins_from_insights"]   = True
                        st.session_state["ins_lost_tier_keys"]  = _keys
                        st.session_state["ins_lost_tier_label"] = _label
                        st.rerun()

            st.caption(
                f"Sorted by {lq_label} activations (descending). "
                f"Tier 1 = top accounts covering 80% of lost volume · "
                f"Tier 2 = next 15% · Tier 3 = remaining 5%."
            )

    # ── Cross Selling ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    _section_label("Cross Selling \u2014 portfolio mix by country")

    _OV_ORDER = ["PV+Storage+EVSE", "Micros+Storage", "PV+EVSE",
                 "Storage+EVSE", "PV Only", "Storage Only", "EVSE Only",
                 "No Device Data"]
    _OV_COLORS = {
        "PV+Storage+EVSE": "#7B5EA7", "Micros+Storage": "#EA6100",
        "PV+EVSE":         "#3B82F6", "Storage+EVSE":   "#439E58",
        "PV Only":         "#F5A623", "Storage Only":   "#64748B",
        "EVSE Only":       "#06B6D4", "No Device Data": "#CBD5E1",
    }

    if "Installer_Overview" in master.columns:
        _all_ctry_cs = ["All Countries"] + sorted(master["Installer_Country"].dropna().unique().tolist())
        _sel_ctry_cs = st.selectbox("Country", _all_ctry_cs, key="ins_cs_country")

        _cs_scope = master if _sel_ctry_cs == "All Countries" \
                    else master[master["Installer_Country"] == _sel_ctry_cs]
        # Map Unknown → No Device Data so it appears in the chart
        _ov_mapped = _cs_scope["Installer_Overview"].replace("Unknown", "No Device Data")
        _cs_counts = (
            _ov_mapped
            .value_counts()
            .reindex(_OV_ORDER)
            .fillna(0).astype(int)
        )
        _cs_total  = len(_cs_scope)          # all installers — matches sidebar
        _cs_active = int(_cs_counts.drop("No Device Data", errors="ignore").sum())
        _pv_cross  = {"PV+Storage+EVSE", "Micros+Storage", "PV+EVSE", "Storage+EVSE"}
        _cs_xsell  = sum(int(_cs_counts.get(t, 0)) for t in _pv_cross)
        _cs_xpct   = f"{_cs_xsell / _cs_active * 100:.0f}%" if _cs_active else "0%"
        _cs_non_pv = int(_cs_counts.get("Storage Only", 0)) + int(_cs_counts.get("EVSE Only", 0))

        # ── Headline metrics ──────────────────────────────────────────────────
        _m1, _m2, _m3 = st.columns(3)
        _m1.metric("Total installers", f"{_cs_total:,}")
        _m2.metric("PV cross-sell achieved", f"{_cs_xsell:,}", _cs_xpct)
        _m3.metric("PV Only — opportunity", f"{int(_cs_counts.get('PV Only', 0)):,}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Donut + horizontal breakdown side by side ─────────────────────────
        _ch_left, _ch_right = st.columns([1, 1])

        with _ch_left:
            _labels = [l for l in _OV_ORDER if _cs_counts.get(l, 0) > 0]
            _vals   = [int(_cs_counts[l]) for l in _labels]
            _cols   = [_OV_COLORS[l] for l in _labels]
            fig_donut = go.Figure(go.Pie(
                labels=_labels, values=_vals,
                hole=0.54,
                marker=dict(colors=_cols, line=dict(color="#FFFFFF", width=2)),
                textinfo="percent",
                textfont=dict(size=11, family="'DM Mono',monospace"),
                hovertemplate="<b>%{label}</b><br>%{value:,} installers (%{percent})<extra></extra>",
                sort=False,
            ))
            _scope_lbl = _sel_ctry_cs
            fig_donut.add_annotation(
                text=f"<b>{_cs_total:,}</b><br><span style='font-size:10px'>total</span>",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#3C3C3C",
                          family="'Enphase Visuelt','Helvetica Neue',Arial,sans-serif"),
                align="center",
            )
            fig_donut.update_layout(
                showlegend=False,
                margin=dict(t=8, b=8, l=8, r=8),
                paper_bgcolor="#FFFFFF",
                height=260,
            )
            st.plotly_chart(fig_donut, use_container_width=True, key="ins_cs_donut")

        with _ch_right:
            _hbar_labels = list(reversed(_labels))
            _hbar_vals   = list(reversed(_vals))
            _hbar_cols   = [_OV_COLORS[l] for l in _hbar_labels]
            _hbar_pcts   = [f"{v / _cs_total * 100:.1f}%  ({v:,})" if _cs_total else "0%"
                            for v in _hbar_vals]
            fig_hbar = go.Figure(go.Bar(
                x=_hbar_vals, y=_hbar_labels,
                orientation="h",
                marker_color=_hbar_cols,
                marker_line_width=0,
                text=_hbar_pcts,
                textposition="outside",
                textfont=dict(size=10, color="#3C3C3C",
                              family="'DM Mono',monospace"),
                hovertemplate="<b>%{y}</b>: %{x:,}<extra></extra>",
                cliponaxis=False,
            ))
            fig_hbar.update_layout(
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FAFAFA",
                margin=dict(t=8, b=8, l=0, r=140),
                height=260,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False,
                           tickfont=dict(size=11, color="#3C3C3C",
                                         family="'DM Mono',monospace")),
                font=dict(family="'DM Mono',monospace"),
            )
            st.plotly_chart(fig_hbar, use_container_width=True, key="ins_cs_hbar")
    else:
        st.caption("No cross-selling data available.")

    # ── Installer list (collapsed) ─────────────────────────────────────────────
    _exp_label = (
        f"\U0001f50d Installer list \u2014 {_sel_ctry_cs}"
        if "Installer_Overview" in master.columns else
        "\U0001f50d Installer list"
    )
    with st.expander(_exp_label, expanded=False):
        # Base is already scoped to the top country filter
        _base = _cs_scope if "Installer_Overview" in master.columns else master

        _all_segs     = [s for s in _SEG_ORDER if s in _base["Installer_Category"].unique()]
        _all_tiers    = [t for t in _TIER_ORDER if t in _base["Installer_Group"].unique()]
        _all_overview = sorted(_base["Installer_Overview"].dropna().unique().tolist()) \
                        if "Installer_Overview" in _base.columns else []

        _dc1, _dc2, _dc3 = st.columns(3)
        with _dc1:
            drill_seg = st.selectbox("Segment", ["All"] + _all_segs, key="ins_sel_seg")
        with _dc2:
            drill_tier = st.selectbox("Tier", ["All"] + _all_tiers, key="ins_sel_tier")
        with _dc3:
            drill_overview = st.selectbox("Cross Selling", ["All"] + _all_overview,
                                          key="ins_sel_overview")

        drilled = _base.copy()
        if drill_seg != "All":
            drilled = drilled[drilled["Installer_Category"] == drill_seg]
        if drill_tier != "All":
            drilled = drilled[drilled["Installer_Group"] == drill_tier]
        if drill_overview != "All" and "Installer_Overview" in drilled.columns:
            drilled = drilled[drilled["Installer_Overview"] == drill_overview]

        if drilled.empty:
            st.info("No installers found for the selected combination.")
        else:
            _ctry_suffix = f"  \u2014  {_sel_ctry_cs}" if _sel_ctry_cs != "Euro Total" else ""
            st.markdown(
                f"<div style='font-size:12px;color:#7D7D7D;margin-bottom:8px'>"
                f"Showing <b>{len(drilled):,}</b> installers{_ctry_suffix}</div>",
                unsafe_allow_html=True,
            )
            _disp_cols = [c for c in ["join_key", "Installer_Mapped", "Installer_Country",
                                       "Installer_Category", "Installer_Group",
                                       "Installer_Overview", "Priority",
                                       "Account Phone", "Support Emai"] if c in drilled.columns]
            _rename = {
                "join_key": "ID", "Installer_Mapped": "Installer",
                "Installer_Country": "Country", "Installer_Category": "Segment",
                "Installer_Group": "Tier", "Installer_Overview": "Cross Selling",
                "Account Phone": "Phone", "Support Emai": "Email",
            }
            _drilled_disp = drilled[_disp_cols].rename(columns=_rename)

            def _color_seg(val):
                return f"color:{_SEG_COLOR.get(val, '#3C3C3C')};font-weight:500"

            st.dataframe(_drilled_disp.style.map(_color_seg, subset=["Segment"]),
                         use_container_width=True, hide_index=True)
            _idl1, _idl2 = st.columns(2)
            with _idl1:
                st.download_button(
                    label="⬇ Download CSV",
                    data=_drilled_disp.to_csv(index=False).encode("utf-8"),
                    file_name=f"installer_list_{_sel_ctry_cs.replace(' ', '_')}.csv",
                    mime="text/csv",
                    key="ins_dl_cs",
                )
            with _idl2:
                _ixl = io.BytesIO()
                _drilled_disp.to_excel(_ixl, index=False, engine="openpyxl")
                st.download_button(
                    label="⬇ Download Excel",
                    data=_ixl.getvalue(),
                    file_name=f"installer_list_{_sel_ctry_cs.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="ins_dl_cs_xl",
                )

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ── Priority focus list ───────────────────────────────────────────────────
    _section_label("Priority focus list \u2014 installers to act on now")
    st.markdown(
        "<div style='font-size:12px;color:#7D7D7D;margin-bottom:8px'>"
        "Lost + Declining + all High-priority installers, ranked by last-quarter revenue impact."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("\U0001f6a8 View priority installer list", expanded=False):
        _focus_countries = sorted(master["Installer_Country"].dropna().unique().tolist())
        _fcol1, _fcol2 = st.columns([1, 3])
        with _fcol1:
            focus_country = st.selectbox("Filter by country", ["All"] + _focus_countries,
                                         key="ins_focus_country")

        focus = master[
            master["Installer_Category"].isin(["Lost", "Declining"]) |
            (master["Priority"].isin(["High", "P1"]))
        ].copy()
        if focus_country != "All":
            focus = focus[focus["Installer_Country"] == focus_country]

        rev_col = None
        if not focus.empty and not _rev_lkp.empty and lq:
            rev_col = f"LQ Rev ({lq_label}) $"
            _lq_rev = (_rev_lkp[_rev_lkp["Quarter"] == lq]
                       .rename(columns={"_rev": rev_col})
                       [["join_key", rev_col]])
            focus = focus.merge(_lq_rev, on="join_key", how="left")
            focus[rev_col] = focus[rev_col].fillna(0).astype(int)
            focus = focus.sort_values(rev_col, ascending=False)

        if not focus.empty:
            display_cols = ["join_key", "Installer_Mapped", "Installer_Country",
                            "Installer_Category", "Installer_Group", "Priority"]
            if rev_col and rev_col in focus.columns:
                display_cols.append(rev_col)
            for _c in ["Account Phone", "Support Emai"]:
                if _c in focus.columns:
                    display_cols.append(_c)
            available = [c for c in display_cols if c in focus.columns]
            rename_map = {
                "join_key": "ID",
                "Installer_Mapped": "Installer",
                "Installer_Country": "Country",
                "Installer_Category": "Segment",
                "Installer_Group": "Tier",
                "Account Phone": "Phone",
                "Support Emai": "Email",
            }
            focus_display = focus[available].rename(columns=rename_map).head(200)

            def _color_seg(val):
                return f"color:{_SEG_COLOR.get(val, '#3C3C3C')};font-weight:500"

            styled = focus_display.style.map(_color_seg, subset=["Segment"])
            if rev_col and rev_col in focus_display.columns:
                styled = styled.format({rev_col: "${:,.0f}"})
            st.dataframe(styled, use_container_width=True, hide_index=True)
            _fdl1, _fdl2 = st.columns(2)
            with _fdl1:
                st.download_button(
                    label="⬇ Download CSV",
                    data=focus_display.to_csv(index=False).encode("utf-8"),
                    file_name=f"priority_list_{focus_country.replace(' ', '_')}.csv",
                    mime="text/csv",
                    key="ins_dl_focus",
                )
            with _fdl2:
                _fxl = io.BytesIO()
                focus_display.to_excel(_fxl, index=False, engine="openpyxl")
                st.download_button(
                    label="⬇ Download Excel",
                    data=_fxl.getvalue(),
                    file_name=f"priority_list_{focus_country.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="ins_dl_focus_xl",
                )
        else:
            st.success("No urgent installers with the current filter selection.")

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # ── Key takeaways ─────────────────────────────────────────────────────────
    _section_label("Key takeaways")

    pct = lambda n: n / total * 100 if total else 0
    rows = []
    if n_lost:
        rows.append(("ins-danger", "#DE2100",
            f"<b>{n_lost} installers ({pct(n_lost):.0f}%) are lost.</b> "
            f"LQ revenue baseline: <b>{_fmt_usd(rev_lost_lq)}</b>. "
            "Re-engage to recover \u2014 every won-back installer rebuilds recurring revenue."))
    if n_declining:
        rows.append(("ins-warn", "#EA6100",
            f"<b>{n_declining} installers ({pct(n_declining):.0f}%) are declining.</b> "
            f"Revenue drop vs {lq_label}: <b>{_fmt_usd(rev_dec_drop)}</b>. "
            "Intervene now before they move to Lost."))
    if n_growing:
        rows.append(("ins-good", "#439E58",
            f"<b>{n_growing} installers ({pct(n_growing):.0f}%) are growing</b> \u2014 "
            f"accelerating activations. {cq_label} revenue: <b>{_fmt_usd(rev_growing_cq)}</b>. "
            "Nurture and reward to sustain momentum."))
    if n_new:
        rows.append(("ins-info", "#3B82F6",
            f"<b>{n_new} new installers</b> just onboarded. "
            f"Early {cq_label} revenue: <b>{_fmt_usd(rev_new_cq)}</b>. "
            "Fast-track enablement to capture first activations quickly."))
    if n_p1:
        rows.append(("ins-purple", "#7B5EA7",
            f"<b>{n_p1} high-priority (P1) installers</b> are flagged for immediate follow-up."))
    if not rows:
        rows.append(("ins-good", "#439E58",
            "Portfolio looks healthy with the current filter selection."))

    items_html = "\n".join(
        f'<div class="ins-row {cls}">'
        f'<span class="ins-dot" style="background:{col}"></span>'
        f'<div style="font-size:13px;line-height:1.6;color:#3C3C3C">{text}</div>'
        f'</div>'
        for cls, col, text in rows
    )
    st.markdown(f"""
<style>
.ins-row   {{display:flex;align-items:flex-start;gap:10px;padding:12px 16px;
             border-radius:12px;margin-bottom:8px}}
.ins-dot   {{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:6px}}
.ins-danger{{background:#FFF8F7;border:1px solid #F4C2BD}}
.ins-warn  {{background:#FFF9F5;border:1px solid #F5D6C0}}
.ins-good  {{background:#F5FAF6;border:1px solid #B7DEC1}}
.ins-info  {{background:#F0F6FF;border:1px solid #BFCFED}}
.ins-purple{{background:#F9F7FD;border:1px solid #D5C8EE}}
</style>
{items_html}""", unsafe_allow_html=True)
