"""Quick smoke test for the classification engine."""
import sys
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.loader import load_basedata, load_disti
from src.classifier import run_full_classification
from src.abc_xyz import attach_abc_xyz
from src.distributor import compute_top_distis

print("Loading basedata...")
df = load_basedata()   # uses auto-resolved default path
print(f"  rows={len(df)}, quarters={sorted(df['Quarter'].unique())}")

print("Running classification...")
master, cur_q, all_5q, prior_4q, weekly = run_full_classification(df)
print(f"  current_q={cur_q},  5Q={all_5q}")
print(f"  installers={len(master)}")
print("  Segment counts:")
print(master["Installer_Category"].value_counts().to_string())
print("  Tier counts:")
print(master["Installer_Group"].value_counts().to_string())
print(f"  Weekly pivot shape: {weekly.shape}")

print("ABC/XYZ...")
master = attach_abc_xyz(master, prior_4q)
print("  Priority counts:")
print(master["Priority"].value_counts().to_string())
print("  ABC counts:")
print(master["ABC"].value_counts().to_string())
print("  XYZ counts:")
print(master["XYZ"].value_counts().to_string())

print("Disti mapping...")
disti = load_disti()   # uses auto-resolved default path
tops = compute_top_distis(disti)
print(f"  disti rows={len(tops)}")
print(tops.head(3).to_string())

print("\nALL ENGINE TESTS PASSED")
