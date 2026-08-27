"""Verify all modules import cleanly."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

print("Checking imports...")
from utils.helpers import quarter_to_int, int_to_quarter, quarter_label
from utils.state_lookup import get_state_full
from src.loader import load_basedata, load_disti
from src.classifier import run_full_classification
from src.abc_xyz import attach_abc_xyz
from src.distributor import compute_top_distis
from src.db import (get_overrides, save_override, save_comment, get_comments,
                    save_message, get_messages_for_rsm, get_sent_messages,
                    update_message_status, save_snapshot, get_last_snapshot_lost)

print("Loading data for view tests...")
df = load_basedata()
disti = load_disti()
master, cur_q, all_5q, prior_4q, weekly = run_full_classification(df)
master = attach_abc_xyz(master, prior_4q)
tops = compute_top_distis(disti)
master = master.merge(tops, on="join_key", how="left")
master["Top_Disti_1"] = master["Top_Disti_1"].fillna("")
master["Top_Disti_2"] = master["Top_Disti_2"].fillna("")
master["Lost_Regained"] = "No"

print(f"  master shape: {master.shape}")
print(f"  master columns: {list(master.columns)}")
print(f"  cur_q={cur_q}, all_5q={all_5q}")
print(f"  Segments: {master['Installer_Category'].value_counts().to_dict()}")
print(f"  Tiers: {master['Installer_Group'].value_counts().to_dict()}")
print(f"  Countries: {sorted(master['Installer_Country'].dropna().unique()[:5])}")

print("\nALL IMPORTS AND DATA LOAD OK")
