"""Smoke-test every view's data-processing path without Streamlit UI."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

import pandas as pd

from src.loader import load_basedata, load_disti
from src.classifier import run_full_classification
from src.abc_xyz import attach_abc_xyz
from src.distributor import compute_top_distis

# ── Build master ──────────────────────────────────────────────────────────────
df = load_basedata()
disti = load_disti()
master, cur_q, all_5q, prior_4q, weekly_pivot = run_full_classification(df)
master = attach_abc_xyz(master, prior_4q)
tops = compute_top_distis(disti)
master = master.merge(tops, on="join_key", how="left")
master["Top_Disti_1"] = master["Top_Disti_1"].fillna("")
master["Top_Disti_2"] = master["Top_Disti_2"].fillna("")
master["Lost_Regained"] = "No"
print(f"Master ready: {len(master)} rows, {len(master.columns)} cols")

# ── Test installer_list logic ─────────────────────────────────────────────────
print("\n--- installer_list ---")
from utils.helpers import quarter_label
q_labels = {q: quarter_label(q) for q in all_5q}
wk_cols = [c for c in weekly_pivot.columns if c != "join_key"]
wk_display = {c: f"WW{c.split('-W')[-1].lstrip('0') or '0'}" for c in wk_cols}
wk_renamed = weekly_pivot.rename(columns=wk_display)
df_merged = master.merge(wk_renamed, on="join_key", how="left")
df_display = df_merged.rename(columns=q_labels)
display_cols = (
    ["Installer_Country", "Installer_Mapped", "RSMs"] +
    list(q_labels.values()) +
    list(wk_display.values()) +
    ["Grand_Total_5Q", "Current_Q_Acts", "Installer_Category", "Installer_Group", "Priority"]
)
display_cols = [c for c in display_cols if c in df_display.columns]
df_show = df_display[display_cols].copy()
print(f"  display cols: {display_cols[:8]}...")
print(f"  shape: {df_show.shape}")
assert len(df_show) == len(master), "row count mismatch"
print("  OK")

# ── Test device_view logic ────────────────────────────────────────────────────
print("\n--- device_view ---")
from src.views.device_view import _build_device_master
dm = _build_device_master(df, master, all_5q, weekly_pivot)
print(f"  device_master shape: {dm.shape}")
print(f"  Device types: {dm['Device Type'].unique()}")
assert "join_key" in dm.columns
assert "Device Type" in dm.columns
print("  OK")

# ── Test summary pivot logic ──────────────────────────────────────────────────
print("\n--- summary ---")
from src.views.summary import _pivot_summary
test_country = master["Installer_Country"].value_counts().index[0]
print(f"  Testing with country: {test_country}")
m_c = master[master["Installer_Country"] == test_country]
df_c = df[df["Installer_Country"] == test_country]
u, cnt = _pivot_summary(df_c, m_c, all_5q, "Installer_Country", "Microinverter")
print(f"  units shape: {u.shape}, count shape: {cnt.shape}")
if not u.empty:
    print(f"  units cols (first 6): {list(u.columns[:6])}")
print("  OK")

# ── Test group_patterns logic ─────────────────────────────────────────────────
print("\n--- group_patterns ---")
from src.views.group_patterns import _build_group_pattern_table
gp = _build_group_pattern_table(df, master, all_5q, "Microinverter")
print(f"  group_patterns shape: {gp.shape}")
if not gp.empty:
    print(f"  cols (first 6): {list(gp.columns[:6])}")
print("  OK")

# ── Test db helpers ───────────────────────────────────────────────────────────
print("\n--- db ---")
from src.db import get_overrides, get_comments, get_messages_for_rsm, get_sent_messages
ov = get_overrides(); print(f"  overrides: {len(ov)}")
cm = get_comments("test_jk"); print(f"  comments for test_jk: {len(cm)}")
msgs = get_messages_for_rsm("nobody"); print(f"  msgs for nobody: {len(msgs)}")
print("  OK")

print("\n✅ ALL VIEW SMOKE TESTS PASSED")
