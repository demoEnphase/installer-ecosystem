"""Chatbot assistant for Installer Ecosystem.
Rule-based engine with optional OpenAI GPT fallback (set OPENAI_API_KEY env var).
"""
import os
import re
import streamlit as st
import pandas as pd

# ─── Knowledge Base ───────────────────────────────────────────────────────────

GLOSSARY = {
    "diamond": "Top 20 installers per country by total activation volume. Highest-value tier requiring priority engagement.",
    "platinum": "Next 50 installers per country. Strong, consistent performers with high activation regularity.",
    "golden": "Next 100 installers per country. Moderate but regular activators.",
    "silver": "Remaining active installers (long tail). Entry-tier, significant growth opportunity.",
    "lost": "Installers with zero activations in the current quarter. Require immediate re-engagement action.",
    "declining": "Active installers whose current run-rate dropped ≥25% vs their prior 2-quarter average. At-risk accounts.",
    "growing": "Active installers whose current run-rate rose ≥15% vs their prior 2-quarter average. Momentum accounts.",
    "new": "Installers who activated with Enphase for the very first time in the current quarter. No prior activation history.",
    "stable": "Active installers with a steady run-rate — not classified as Declining, Growing, or New.",
    "p1": "Priority 1: Diamond or Platinum installers. Highest revenue impact — requires immediate attention.",
    "p2": "Priority 2: Golden or Silver installers. Standard follow-up cadence.",
    "priority 1": "Diamond or Platinum installers. Highest revenue impact — requires immediate attention.",
    "priority 2": "Golden or Silver installers. Standard follow-up cadence.",
    "abc": "ABC classification by revenue contribution. A = top 80% of volume, B = next 15%, C = bottom 5%.",
    "xyz": "XYZ classification by order regularity. X = highly regular, Y = variable, Z = sporadic.",
    "run rate": "The current quarter's activation pace, compared against the prior 2-quarter average to detect trends.",
    "run-rate": "The current quarter's activation pace, compared against the prior 2-quarter average to detect trends.",
    "activation": "Registration of a new Enphase device (microinverter, battery, EVSE, etc.) by an installer in the system.",
    "ww": "Work Week — a numbered week of the year (e.g. WW26 = 26th week of the year).",
    "quarter": "A 3-month period for tracking activations. Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec.",
    "join_key": "Unique identifier per installer: 'Country | Installer Name'. Used to link across data tables.",
    "rsm": "Regional Sales Manager — responsible for a group of installers across one or more countries.",
    "cm": "Country Manager — responsible for all installers within a specific country.",
    "disti": "Distributor — the channel partner from whom installers source Enphase products.",
    "distributor": "Channel partner from whom installers source Enphase products.",
    "top disti": "The distributor from which an installer ordered the most Enphase products in the rolling 5-quarter window.",
    "iq battery": "Enphase home battery storage product tracked as a separate device type in All Devices view.",
    "evse": "Electric Vehicle Supply Equipment — Enphase EV charger tracked as a device type.",
    "microinverter": "Core Enphase product that converts DC power from solar panels to AC power.",
    "lost regained": "An installer previously Lost who has returned to activate devices in the current quarter.",
    "snapshot": "A saved copy of the current installer classification state, used to detect Lost-Regained changes over time.",
    "5 quarter": "Rolling window of 5 most recent quarters used for all classification and trend calculations.",
    "rolling": "The analysis always covers the 5 most recent completed quarters, updating as new data is loaded.",
}

NAV_GUIDE = {
    "dashboard": "Click **🏠 Dashboard** in the top navigation bar. Shows KPI overview, tier/segment distribution charts, and country breakdown table.",
    "summary": "Click **📈 Summary** in the top nav. Shows pivot tables grouped by Country or RSM with drill-down to individual installers.",
    "installer list": "Click **📋 Installers List** in the top nav. Full installer-level table with email, phone, tier, segment, and activation history. Supports CSV export.",
    "installers list": "Click **📋 Installers List** in the top nav. Full installer-level table with email, phone, tier, segment, and activation history. Supports CSV export.",
    "all devices": "Click **📱 All Devices** in the top nav. Breaks down activations by device type: Microinverter, IQ Battery (KWh), and EVSE.",
    "inbox": "Click **📬 Inbox** in the top nav. Shows action flags and follow-up items scoped to your role and country.",
    "filter": "Use the **left sidebar** to filter by Country, RSM, Segment, Tier, Priority, or Region. Filters apply across all tabs.",
    "export": "Go to **📋 Installers List** or **📱 All Devices** tab and click the **⬇ Download CSV** button at the top of the table.",
    "download": "Go to **📋 Installers List** or **📱 All Devices** tab and click the **⬇ Download CSV** button at the top of the table.",
    "glossary": "Open **📖 Glossary & Guide** in the left sidebar. It covers all definitions, the classification method, and navigation tips.",
    "login": "On the login page, select your **role** (Admin / Country Manager / RSM), choose your **username** from the dropdown, then enter your password.",
    "password": "The default password for all users is **Enphase@123**.",
    "upload": "Admin users can upload new basedata Excel files via **📂 Upload Data Files** in the left sidebar.",
    "snapshot": "Admin users can save a quarter snapshot using **📸 Save Quarter Snapshot** in the sidebar, enabling the Lost-Regained tracking flag.",
    "classification": (
        "Classifications are computed from rolling 5-quarter data:\n"
        "1. **Lost** → zero activations this quarter\n"
        "2. **New** → first-ever activation\n"
        "3. **Declining** → run-rate dropped ≥25% vs prior 2Q avg\n"
        "4. **Growing** → run-rate rose ≥15% vs prior 2Q avg\n"
        "5. **Stable** → everything else active\n\n"
        "Tiers ranked by current-quarter volume per country: Top 20 = Diamond, next 50 = Platinum, next 100 = Golden, rest = Silver."
    ),
    "classify": (
        "Classifications are computed from rolling 5-quarter data:\n"
        "1. **Lost** → zero activations this quarter\n"
        "2. **New** → first-ever activation\n"
        "3. **Declining** → run-rate dropped ≥25% vs prior 2Q avg\n"
        "4. **Growing** → run-rate rose ≥15% vs prior 2Q avg\n"
        "5. **Stable** → everything else active\n\n"
        "Tiers ranked by current-quarter volume per country: Top 20 = Diamond, next 50 = Platinum, next 100 = Golden, rest = Silver."
    ),
}

_GREET_RE = re.compile(
    r"^(hi|hello|hey|good\s*(morning|evening|afternoon|night)|howdy|greetings)[\s!.?]*$", re.I
)
_THANKS_RE = re.compile(r"^(thanks?|thank\s*you|thx|cheers|ty)[\s!.?]*$", re.I)
_QUESTION_WORDS = {"what", "which", "who", "when", "where", "why", "how",
                   "tell me", "explain", "define", "describe", "about", "is a", "definition"}
_COUNT_WORDS = {"how many", "count", "number of", "total", "show me how many"}


# ─── Rule-based engine ────────────────────────────────────────────────────────

def _rule_response(query: str, master: pd.DataFrame) -> str | None:
    q = query.lower().strip()

    # ── Greetings / thanks ────────────────────────────────────────────────────
    if _GREET_RE.match(q):
        return (
            "👋 Hello! I'm the Installer Ecosystem assistant.\n\n"
            "I can help with:\n"
            "- **Definitions** — *What is Diamond?*\n"
            "- **Live data** — *How many Lost installers are in Germany?*\n"
            "- **Navigation** — *How do I export data?*\n"
            "- **Classification logic** — *How is the tier calculated?*"
        )
    if _THANKS_RE.match(q):
        return "You're welcome! Let me know if you have more questions. 😊"

    # ── Glossary lookups ──────────────────────────────────────────────────────
    is_question = "?" in query or any(w in q for w in _QUESTION_WORDS)
    if is_question:
        # Longest-match first
        for term in sorted(GLOSSARY, key=len, reverse=True):
            if re.search(rf"\b{re.escape(term)}\b", q):
                return f"**{term.title()}**\n\n{GLOSSARY[term]}"

    # ── Navigation ────────────────────────────────────────────────────────────
    if is_question:
        for page in sorted(NAV_GUIDE, key=len, reverse=True):
            if page in q:
                return NAV_GUIDE[page]

    if any(w in q for w in ["navigate", "navigation", "tabs", "menu"]):
        return (
            "**App Navigation**\n\n"
            "Use the **top navigation bar** to switch between:\n"
            "- 🏠 Dashboard\n- 📈 Summary\n- 📋 Installers List\n- 📱 All Devices\n- 📬 Inbox\n\n"
            "Use the **left sidebar** to filter by Country, RSM, Segment, Tier, Priority, or Region."
        )

    # ── Data queries ──────────────────────────────────────────────────────────
    if master is not None and not master.empty:
        count_intent = any(phrase in q for phrase in _COUNT_WORDS)

        if count_intent:
            tier_map = {"diamond": "Diamond", "platinum": "Platinum",
                        "golden": "Golden", "silver": "Silver"}
            seg_map  = {"lost": "Lost", "declining": "Declining",
                        "growing": "Growing", "new": "New", "stable": "Stable"}
            pri_map  = {"p1": "P1", "p2": "P2",
                        "priority 1": "P1", "priority 2": "P2"}

            tier    = next((v for k, v in tier_map.items() if re.search(rf"\b{k}\b", q)), None)
            seg     = next((v for k, v in seg_map.items()  if re.search(rf"\b{k}\b", q)), None)
            pri     = next((v for k, v in pri_map.items()  if k in q), None)
            country = None
            if "in " in q:
                for c in master["Installer_Country"].unique():
                    if c.lower() in q:
                        country = c
                        break

            df = master
            filters = []
            if tier:
                df = df[df["Installer_Group"] == tier]
                filters.append(f"Tier = {tier}")
            if seg:
                df = df[df["Installer_Category"] == seg]
                filters.append(f"Segment = {seg}")
            if pri:
                df = df[df["Priority"] == pri]
                filters.append(f"Priority = {pri}")
            if country:
                df = df[df["Installer_Country"] == country]
                filters.append(f"Country = {country}")

            count = len(df)
            if filters:
                return f"There are **{count:,} installers** matching: {', '.join(filters)}."
            return f"There are **{len(master):,} total active installers** in the current dataset."

        # Country breakdown
        if "country" in q and any(w in q for w in ["breakdown", "list", "which", "all"]):
            cb = master.groupby("Installer_Country").size().sort_values(ascending=False)
            lines = [f"- **{c}**: {n:,}" for c, n in cb.items()]
            return "**Installers by Country:**\n\n" + "\n".join(lines)

        # Top country
        if any(w in q for w in ["top", "most", "largest", "biggest"]) and "country" in q:
            top_c = master["Installer_Country"].value_counts().idxmax()
            top_n = master["Installer_Country"].value_counts().iloc[0]
            return f"The country with the most installers is **{top_c}** with **{top_n:,} installers**."

        # Installer lookup
        if "installer" in q and any(w in q for w in ["find", "search", "look up", "detail", "info"]):
            return ("To look up a specific installer, go to **📋 Installers List**, "
                    "use the search box at the top of the table to filter by name.")

    # ── Classification method ─────────────────────────────────────────────────
    if any(w in q for w in ["classify", "classification", "how is", "how are",
                             "method", "calculated", "determined", "derived", "work"]):
        return NAV_GUIDE.get("classification", "")

    return None


# ─── OpenAI fallback ──────────────────────────────────────────────────────────

def _openai_response(query: str, master: pd.DataFrame, api_key: str) -> str:
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        ctx_lines = []
        if master is not None and not master.empty:
            ctx_lines.append(f"Total installers: {len(master):,}")
            for col, lbl in [("Installer_Group", "Tiers"),
                              ("Installer_Category", "Segments"),
                              ("Installer_Country", "Countries (top 10)")]:
                if col in master.columns:
                    vc = master[col].value_counts().head(10)
                    ctx_lines.append(f"{lbl}: " + ", ".join(f"{k}={v:,}" for k, v in vc.items()))

        system = (
            "You are a helpful assistant for the Installer Ecosystem analytics platform (Enphase Energy, Euro region).\n\n"
            "Key facts:\n"
            "- Tiers by activation volume: Diamond (top 20/country), Platinum (next 50), Golden (next 100), Silver (rest)\n"
            "- Segments: Lost (0 activations), Declining (run-rate -25%), Growing (run-rate +15%), New (first time), Stable\n"
            "- Priority: P1 = Diamond/Platinum, P2 = Golden/Silver\n"
            "- Rolling 5-quarter data window. Current quarter vs prior 2Q average for trend.\n"
            "- Navigation tabs: Dashboard, Summary, Installers List, All Devices, Inbox\n"
            "- Sidebar filters: Country, RSM, Segment, Tier, Priority, Region\n\n"
            + ("Live data snapshot:\n" + "\n".join(ctx_lines) if ctx_lines else "")
            + "\n\nAnswer concisely. Use markdown bold for emphasis. Keep answers under 150 words."
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": query},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()

    except ImportError:
        return "OpenAI package not installed. Run `pip install openai` to enable AI-powered answers."
    except Exception as e:
        return (
            "I couldn't find a direct answer. Try asking:\n\n"
            "- *What is Declining?*\n"
            "- *How many Lost installers are in France?*\n"
            "- *How do I export data?*\n"
            "- *How is the tier calculated?*"
        )


# ─── Main render ──────────────────────────────────────────────────────────────

def render_chatbot(master: pd.DataFrame = None):
    """Renders the chatbot assistant expander at the bottom of the page."""

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": (
                    "\u26a1 **Installer Ecosystem** assistant \u00b7 "
                    "*What is Diamond? \u00b7 How many Lost in Germany? \u00b7 How is tier calculated?*"
                ),
            }
        ]

    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    st.markdown("---")
    with st.expander("💬  Assistant — Ask anything about the data or app", expanded=False):
        st.markdown(
            """<style>
            [data-testid="stChatMessage"] {
                background: #F9F9F7 !important;
                border-radius: 8px !important;
                border: 1px solid #E8E8E2 !important;
                margin-bottom: 4px !important;
                padding: 5px 10px !important;
            }
            [data-testid="stChatMessage"] p,
            [data-testid="stChatMessage"] li,
            [data-testid="stChatMessage"] span,
            [data-testid="stChatMessage"] strong,
            [data-testid="stChatMessage"] em,
            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] strong,
            [data-testid="stMarkdownContainer"] em {
                font-size: 11px !important;
                line-height: 1.45 !important;
                color: #3C3C3C !important;
                font-family: 'Helvetica Neue', Arial, sans-serif !important;
            }
            [data-testid="stChatMessageAvatarAssistant"],
            [data-testid="stChatMessageAvatarUser"] {
                width: 20px !important;
                height: 20px !important;
                font-size: 10px !important;
                min-width: 20px !important;
            }
            [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
                padding: 0 !important;
                margin: 0 !important;
            }
            </style>""",
            unsafe_allow_html=True,
        )

        chat_box = st.container(height=200)
        with chat_box:
            for msg in st.session_state.chat_history:
                avatar = "⚡" if msg["role"] == "assistant" else "👤"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        col_q, col_clr = st.columns([6, 1])
        with col_clr:
            if st.button("🗑️ Clear", key="chat_clear_btn", use_container_width=True,
                         help="Clear chat history"):
                st.session_state.chat_history = [
                    {"role": "assistant", "content": "Chat cleared. What would you like to know?"}
                ]
                st.rerun()

        user_input = st.chat_input(
            "Ask about definitions, data counts, navigation…",
            key="chatbot_input",
        )

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            response = _rule_response(user_input, master)
            if response is None:
                if openai_key:
                    with st.spinner("Thinking…"):
                        response = _openai_response(user_input, master, openai_key)
                else:
                    response = (
                        "I didn't find a direct match. Try asking:\n\n"
                        "- *What is Declining?*\n"
                        "- *How many Diamond installers are in France?*\n"
                        "- *How do I export data?*\n"
                        "- *How is the tier calculated?*\n\n"
                        "*(Set an `OPENAI_API_KEY` environment variable for AI-powered answers to any question.)*"
                    )

            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
