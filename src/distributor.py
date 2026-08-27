"""Derive Top Distributor 1 & 2 for each installer from the shipment file."""
import pandas as pd


def compute_top_distis(disti_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns DataFrame with columns: join_key, Top_Disti_1, Top_Disti_2
    join_key = 'Installer Country | Installer Name'
    """
    # Sum Activations by installer × distributor (all quarters)
    agg = (
        disti_df.groupby(["join_key", "Distributor"])["Activations"]
        .sum()
        .reset_index()
        .sort_values(["join_key", "Activations"], ascending=[True, False])
    )

    top1 = (
        agg.groupby("join_key")
        .nth(0)
        .reset_index()[["join_key", "Distributor"]]
        .rename(columns={"Distributor": "Top_Disti_1"})
    )
    top2 = (
        agg.groupby("join_key")
        .nth(1)
        .reset_index()[["join_key", "Distributor"]]
        .rename(columns={"Distributor": "Top_Disti_2"})
    )

    result = top1.merge(top2, on="join_key", how="left")
    result["Top_Disti_1"] = result["Top_Disti_1"].fillna("")
    result["Top_Disti_2"] = result["Top_Disti_2"].fillna("")
    return result
