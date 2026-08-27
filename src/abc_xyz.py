"""
ABC-XYZ classification and P1/P2 priority assignment.

ABC — per-country volume share (rolling prior 4 quarters):
  A = cumulative % <= 80%
  B = cumulative % <= 95%
  C = rest

XYZ — QoQ coefficient of variation (prior 4 quarters):
  X = COV > 0 and <= 0.5
  Y = COV > 0.5 and < 0.8
  Z = COV = 0 or >= 0.8

P1 = AX, AY, AZ, BX
P2 = BY, BZ, CX, CY, CZ
"""
import pandas as pd
import numpy as np
from utils.helpers import quarter_to_int, int_to_quarter


P1_COMBOS = {"AX", "AY", "AZ", "BX"}
P2_COMBOS = {"BY", "BZ", "CX", "CY", "CZ"}


def compute_abc(master: pd.DataFrame, prior_4q: list) -> pd.Series:
    """
    Returns a Series indexed by master's index with ABC labels.
    Computed per Installer_Country, sorted descending by prior-4Q total.
    """
    existing_4q = [q for q in prior_4q if q in master.columns]
    prior_total = master[existing_4q].fillna(0).sum(axis=1) if existing_4q else pd.Series(0.0, index=master.index)

    df = pd.DataFrame({"_prior_total": prior_total, "_country": master["Installer_Country"].values},
                      index=master.index)
    df = df.sort_values(["_country", "_prior_total"], ascending=[True, False])

    country_totals = df.groupby("_country")["_prior_total"].transform("sum")
    cum_pct = df.groupby("_country")["_prior_total"].cumsum() / country_totals.replace(0, np.nan)
    cum_pct = cum_pct.fillna(1.0)

    labels = np.where(cum_pct <= 0.80, "A", np.where(cum_pct <= 0.95, "B", "C"))
    return pd.Series(labels, index=df.index).reindex(master.index)


def compute_xyz(master: pd.DataFrame, prior_4q: list) -> pd.Series:
    """
    Returns a Series indexed by master's index with XYZ labels.
    COV = std / mean of quarterly activations across prior 4Q.
    """
    existing_4q = [q for q in prior_4q if q in master.columns]
    if not existing_4q:
        return pd.Series("Z", index=master.index)

    q_data = master[existing_4q].fillna(0)
    means = q_data.mean(axis=1)
    stds = q_data.std(axis=1, ddof=0)
    cov = (stds / means.replace(0, np.nan)).fillna(0)

    xyz = np.where(cov <= 0, "Z", np.where(cov <= 0.5, "X", np.where(cov < 0.8, "Y", "Z")))
    return pd.Series(xyz, index=master.index)


def compute_priority(abc: pd.Series, xyz: pd.Series) -> pd.Series:
    combined = abc + xyz
    return pd.Series(np.where(combined.isin(P1_COMBOS), "P1", "P2"), index=abc.index)


def attach_abc_xyz(master: pd.DataFrame, prior_4q: list) -> pd.DataFrame:
    """Add ABC, XYZ, ABCXYZ, and Priority columns to master."""
    master = master.copy()
    master["ABC"] = compute_abc(master, prior_4q)
    master["XYZ"] = compute_xyz(master, prior_4q)
    master["ABCXYZ"] = master["ABC"] + master["XYZ"]
    master["Priority"] = compute_priority(master["ABC"], master["XYZ"])
    return master


def attach_abc_xyz_per_segment(master: pd.DataFrame, prior_4q: list,
                                current_q: str) -> pd.DataFrame:
    """
    Run ABC/XYZ **independently within each Installer_Category** so that P1/P2
    reflects relative importance inside Lost, Declining, Growing, New, and Stable
    separately — not across the whole population.

    • Lost / Declining / Growing / Stable → ABC/XYZ on prior_4q volumes
    • New → ABC on current_q (no prior history); XYZ = Z (no variation data)
    """
    master = master.copy()
    results = []
    for seg, grp in master.groupby("Installer_Category", sort=False):
        grp = grp.copy()
        if seg == "New":
            cur_cols = [current_q] if current_q in grp.columns else []
            grp["ABC"] = compute_abc(grp, cur_cols)
            grp["XYZ"] = pd.Series("Z", index=grp.index)
        else:
            grp["ABC"] = compute_abc(grp, prior_4q)
            grp["XYZ"] = compute_xyz(grp, prior_4q)
        grp["ABCXYZ"] = grp["ABC"] + grp["XYZ"]
        _combo = grp["ABC"] + grp["XYZ"]
        grp["Priority"] = np.where(_combo.isin(P1_COMBOS), "P1", "P2")
        results.append(grp)

    if not results:
        return master
    return pd.concat(results).sort_index()
