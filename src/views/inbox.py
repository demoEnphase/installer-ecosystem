"""Inbox — Actions table (bulk comments) + RSM notification inbox + sent items."""
import pandas as pd
import streamlit as st
from src.db import (get_messages_for_rsm, get_sent_messages,
                    update_message_status, upsert_action_note, get_all_action_notes)
from utils.helpers import quarter_label, sort_quarters


STATUS_COLORS = {"Open": "#EF4444", "In Progress": "#F59E0B", "Done": "#22C55E"}
PRIORITY_COLORS = {"High": "#EF4444", "Normal": "#64748B"}
SEG_ORDER = ["Lost", "Declining", "Growing", "New"]


def _badge(text: str, color: str) -> str:
    return (f"<span style='background:{color}22;color:{color};"
            f"padding:2px 8px;border-radius:4px;font-size:0.8rem;font-weight:600'>{text}</span>")


def _render_actions_table(master: pd.DataFrame, role: str, username: str,
                          user_country: str = "", user_rsm: str = "",
                          caller_key: str = "inbox",
                          segments: list = None,
                          df_raw: pd.DataFrame = None,
                          all_5q: list = None):
    """Bulk editable table of Lost (+ Declining) installers with action notes."""
    if segments is None:
        segments = ["Lost", "Declining"]

    seg_label = " & ".join(segments)
    st.markdown(f"#### 💬 Action Notes — {seg_label} Installers")
    st.caption("All roles can add/update notes. Changes saved per row on **Save All**.")

    # Filter to requested segments
    df = master[master["Installer_Category"].isin(segments)].copy()

    # Role scoping for display
    scope_label = "All"
    if role == "country_manager" and user_country:
        scope_label = f"Country: {user_country}"
    elif role == "rsm" and user_rsm:
        scope_label = f"RSM: {user_rsm}"
    st.caption(f"Scope: **{scope_label}** · {len(df):,} installers")

    if df.empty:
        st.info("No Lost or Declining installers in this scope.")
        return

    # Load existing notes
    notes = get_all_action_notes()

    # Build display frame
    rows = []
    for _, r in df.iterrows():
        jk = r["join_key"]
        note_row = notes.get(jk, {})
        raw_email = str(r.get("Support Emai", "") or "").strip()
        raw_phone = str(r.get("Account Phone", "") or "").strip()
        rows.append({
            "join_key":        jk,
            "Country":         r.get("Installer_Country", ""),
            "Installer":       r.get("Installer_Mapped", ""),
            "RSM":             r.get("RSMs", ""),
            "Segment":         r.get("Installer_Category", ""),
            "Priority":        r.get("Priority", ""),
            "Email":           f"mailto:{raw_email}" if "@" in raw_email else "",
            "Phone":           f"tel:{raw_phone}" if raw_phone else "",
            "Action Note":     note_row.get("note", ""),
            "Status":          note_row.get("status", "Open"),
            "Last Updated By": note_row.get("updated_by", ""),
            "_total_acts":     float(r.get("Grand_Total_5Q", 0) or 0),
        })

    tbl = pd.DataFrame(rows)

    # ── Progress summary ─────────────────────────────────────────────────────
    total_lost = len(tbl[tbl["Segment"] == "Lost"])
    commented_lost = len(tbl[(tbl["Segment"] == "Lost") & (tbl["Action Note"].str.strip() != "")])
    pending_lost = total_lost - commented_lost
    total_all = len(tbl)
    commented_all = len(tbl[tbl["Action Note"].str.strip() != ""])

    pc1, pc2, pc3, pc4 = st.columns(4)
    pc1.metric("🔴 Lost Total", f"{total_lost:,}")
    pc2.metric("✅ Lost — Commented", f"{commented_lost:,}")
    pc3.metric("⏳ Lost — Pending", f"{pending_lost:,}")
    pc4.metric("📝 All Commented", f"{commented_all:,}/{total_all:,}")

    if total_lost > 0:
        progress = commented_lost / total_lost
        st.progress(progress, text=f"Lost installer coverage: {commented_lost:,} of {total_lost:,} commented ({progress*100:.0f}%)")

    # Sort: segment → country total desc → installer total desc → pending first
    tbl["_has_note"] = tbl["Action Note"].str.strip().ne("").astype(int)
    seg_order_map = {s: i for i, s in enumerate(["Lost", "Declining", "Growing", "New", "Stable"])}
    tbl["_seg_order"] = tbl["Segment"].map(seg_order_map).fillna(99)
    tbl["_ctry_total"] = tbl.groupby(["_seg_order", "Country"])["_total_acts"].transform("sum")
    tbl = tbl.sort_values(["_seg_order", "_ctry_total", "Country", "_total_acts", "_has_note"],
                          ascending=[True, False, True, False, True])
    tbl = tbl.drop(columns=["_has_note", "_seg_order", "_total_acts", "_ctry_total"])

    # ── Join quarterly + weekly activation history ────────────────────────────
    q_cols_added: list = []
    wk_cols_added: list = []
    if df_raw is not None and all_5q:
        _5q_sorted = sort_quarters(all_5q)
        _q_lbl = {q: quarter_label(q) for q in _5q_sorted}

        # Quarterly totals per installer (all device types summed)
        _q_data = (
            df_raw[df_raw["Quarter"].isin(_5q_sorted)]
            .groupby(["join_key", "Quarter"])["Number of devices"]
            .sum()
            .unstack(fill_value=0)
            .reindex(columns=_5q_sorted, fill_value=0)
            .rename(columns=_q_lbl)
        )
        q_cols_added = list(_q_lbl.values())
        tbl = tbl.merge(_q_data.reset_index(), on="join_key", how="left")
        for c in q_cols_added:
            tbl[c] = tbl[c].fillna(0).astype(int)

        # Weekly totals per installer (current-quarter weeks only)
        _wk_data_raw = df_raw[df_raw["Quarter"] == _5q_sorted[-1]].copy()
        _wk_cols_raw = sorted(
            [c for c in df_raw.columns if "-W" in str(c)], key=lambda x: x)
        if _wk_cols_raw:
            _wk_lbl = {c: f"WW{int(c.split('-W')[1])}" for c in _wk_cols_raw}
            _seen = set(); _wk_lbl = {c: v for c, v in _wk_lbl.items()
                                       if not (v in _seen or _seen.add(v))}
            _wk_pivot = (
                _wk_data_raw.groupby("join_key")[list(_wk_lbl.keys())]
                .sum()
                .rename(columns=_wk_lbl)
            )
            wk_cols_added = list(_wk_lbl.values())
            tbl = tbl.merge(_wk_pivot.reset_index(), on="join_key", how="left")
            for c in wk_cols_added:
                tbl[c] = tbl[c].fillna(0).astype(int)

    show_weekly = bool(wk_cols_added) and st.toggle(
        "📅 Show weekly columns", value=False, key=f"inbox_wk_{caller_key}")

    col_cfg = {
        "join_key":        None,
        "Country":         st.column_config.TextColumn("Country",   width="small"),
        "Installer":       st.column_config.TextColumn("Installer", width="large"),
        "RSM":             st.column_config.TextColumn("RSM",       width="medium"),
        "Segment":         st.column_config.TextColumn("Segment",   width="small"),
        "Priority":        st.column_config.TextColumn("P",         width="small"),
        "Email":           st.column_config.LinkColumn("✉️ Email",
                               display_text=r"mailto:(.*)", width="medium"),
        "Phone":           st.column_config.LinkColumn("📞 Phone",
                               display_text=r"tel:(.*)", width="medium"),
        "Action Note":     st.column_config.TextColumn("Action Note",
                                                        width="large",
                                                        help="Type your action note here"),
        "Status":          st.column_config.SelectboxColumn(
                               "Status", width="small",
                               options=["Open", "In Progress", "Done"]),
        "Last Updated By": st.column_config.TextColumn("By", width="small"),
    }
    for _qc in q_cols_added:
        col_cfg[_qc] = st.column_config.NumberColumn(_qc, format="%,d", width="small")
    for _wc in wk_cols_added:
        col_cfg[_wc] = st.column_config.NumberColumn(_wc, format="%,d", width="small")

    _drop = ["join_key"] + ([] if show_weekly else wk_cols_added)
    _disabled = ["Country", "Installer", "RSM", "Segment", "Priority",
                 "Email", "Phone", "Last Updated By"] + q_cols_added + wk_cols_added

    edited = st.data_editor(
        tbl.drop(columns=_drop),
        use_container_width=True,
        height=580,
        column_config=col_cfg,
        disabled=_disabled,
        key=f"actions_table_edit_{caller_key}",
        hide_index=True,
    )

    if st.button("💾 Save All Notes", type="primary", key=f"save_actions_btn_{caller_key}"):
        saved = 0
        for i, row in edited.iterrows():
            orig_jk = tbl.iloc[i]["join_key"]
            orig_row = tbl.iloc[i]
            new_note   = str(row["Action Note"] or "").strip()
            new_status = str(row["Status"] or "Open")
            old_note   = str(orig_row["Action Note"] or "").strip()
            old_status = str(orig_row["Status"] or "Open")
            if new_note != old_note or new_status != old_status:
                upsert_action_note(
                    join_key=orig_jk,
                    installer_name=orig_row["Installer"],
                    country=orig_row["Country"],
                    rsm=orig_row["RSM"],
                    segment=orig_row["Segment"],
                    priority=orig_row["Priority"],
                    note=new_note,
                    status=new_status,
                    user=username,
                )
                saved += 1
        if saved:
            st.success(f"✓ Saved {saved} note(s)")
            st.rerun()
        else:
            st.info("No changes detected.")

    # Export
    csv = edited.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export Actions to CSV", csv,
                       "action_notes.csv", "text/csv", key=f"dl_actions_{caller_key}")


def render_inbox(master: pd.DataFrame, role: str, username: str,
                 user_rsm: str = "", user_country: str = ""):
    st.subheader("📬 Inbox & Messages")

    tab_actions, tab_inbox, tab_sent = st.tabs(
        ["� Action Notes", "�📥 Inbox", "📤 Sent Items"])

    with tab_actions:
        _render_actions_table(master, role, username, user_country, user_rsm)

    # ── Inbox (RSM sees messages directed to them) ───────────────────────────
    with tab_inbox:
        if role == "rsm":
            rsm_name = user_rsm
        else:
            # Admin/CM can view any RSM inbox
            all_rsms_placeholder = [username]
            rsm_name = st.text_input("View inbox for RSM name", value=user_rsm or username)

        msgs = get_messages_for_rsm(rsm_name)
        if not msgs:
            st.info("📭 No messages in inbox.")
        else:
            st.caption(f"{len(msgs)} message(s)")
            for m in msgs:
                pri_color = PRIORITY_COLORS.get(m["priority"], "#64748B")
                sta_color = STATUS_COLORS.get(m["status"], "#64748B")
                with st.expander(
                    f"[{m['status']}] {m['subject']} — {m['installer']} ({m['country']})",
                    expanded=(m["status"] == "Open")
                ):
                    col_left, col_right = st.columns([3, 1])
                    with col_left:
                        st.markdown(
                            f"**From:** {m['from']}  |  "
                            f"**Installer:** `{m['installer']}` ({m['country']})  |  "
                            f"**Received:** {m['at'].strftime('%d %b %Y %H:%M')}",
                            unsafe_allow_html=True
                        )
                        if m.get("call_dt"):
                            st.markdown(f"📅 **Scheduled call:** {m['call_dt']}")
                        st.markdown(f"**Message:**\n\n{m['message']}")
                        st.markdown(
                            _badge(m["priority"], pri_color) + "  " +
                            _badge(m["status"], sta_color),
                            unsafe_allow_html=True
                        )
                    with col_right:
                        new_status = st.selectbox(
                            "Update status",
                            ["Open", "In Progress", "Done"],
                            index=["Open", "In Progress", "Done"].index(m["status"]),
                            key=f"status_{m['id']}"
                        )
                        if st.button("Update", key=f"upd_{m['id']}"):
                            update_message_status(m["id"], new_status)
                            st.success("Status updated")
                            st.rerun()

    # ── Sent Items (CM/admin sees what they sent) ────────────────────────────
    with tab_sent:
        sent = get_sent_messages(username)
        if not sent:
            st.info("📭 No sent messages.")
        else:
            st.caption(f"{len(sent)} sent message(s)")
            for m in sent:
                sta_color = STATUS_COLORS.get(m["status"], "#64748B")
                with st.expander(
                    f"→ {m['to_rsm']} | {m['subject']} — {m['installer']} | "
                    f"{_badge(m['status'], sta_color)}",
                    unsafe_allow_html=True
                ):
                    st.markdown(
                        f"**To RSM:** {m['to_rsm']}  |  "
                        f"**Installer:** `{m['installer']}` ({m['country']})  |  "
                        f"**Sent:** {m['at'].strftime('%d %b %Y %H:%M')}"
                    )
                    if m.get("call_dt"):
                        st.markdown(f"📅 **Scheduled call:** {m['call_dt']}")
                    st.markdown(f"**Message:**\n\n{m['message']}")
                    st.markdown(
                        _badge(m["priority"], PRIORITY_COLORS.get(m["priority"], "#64748B")) +
                        "  " + _badge(m["status"], sta_color),
                        unsafe_allow_html=True
                    )
