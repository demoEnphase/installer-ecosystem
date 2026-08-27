"""Excel → raw DataFrames. Swap load_basedata/load_disti for Incorta REST in future."""
import pandas as pd
import streamlit as st
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DISTI_SHEET = "2_Euro Activations (all devices"


def _resolve_data_path(filename: str) -> str:
    """Look for data file in project root first, then data/ subdir."""
    for candidate in [
        BASE_DIR / filename,
        BASE_DIR / "data" / filename,
    ]:
        if candidate.exists():
            return str(candidate)
    return str(BASE_DIR / "data" / filename)  # will raise FileNotFoundError with clear path


BASEDATA_PATH = _resolve_data_path("basedata.xlsx")
DISTI_PATH = _resolve_data_path("Installer disti mapping.xlsx")

# ── Region mappings ───────────────────────────────────────────────────────────
EURO_COUNTRIES = {
    "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES",
    "FI", "FR", "GB", "GR", "HR", "HU", "IE", "IT", "LT", "LU",
    "LV", "MT", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK",
}
ANZP_COUNTRIES = {"AU", "NZ", "PG", "FJ", "WS", "TO", "VU", "SB", "NC"}


def _get_region(country_code: str) -> str:
    c = str(country_code).strip().upper()
    if c in EURO_COUNTRIES:
        return "Euro"
    if c in ANZP_COUNTRIES:
        return "ANZP"
    return "Other"


# ── Installer name aliases ────────────────────────────────────────────────────
# Maps old_name → canonical_name (applied across all countries).
# Applied before join_key is built so all history merges under one entity.
INSTALLER_ALIASES: dict[str, str] = {
    "Soleco Corse": "Soleco SARL",
    "Hunter Solar Solutions - Enphase Regional Installer of the Year 2024, Enphase National Installer of the Year 2025": "Hunter Solar Solutions",
}


def _apply_installer_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Replace aliased installer names with their canonical name."""
    if not INSTALLER_ALIASES or "Installer_Mapped" not in df.columns:
        return df
    df["Installer_Mapped"] = df["Installer_Mapped"].str.strip().replace(INSTALLER_ALIASES)
    return df


def _clean_basedata(df: pd.DataFrame) -> pd.DataFrame:
    """Shared cleaning logic for any basedata DataFrame."""
    # Normalise column name variants across file versions
    _col_aliases = {
        "Support Email": "Support Emai",       # new basedata column
        "Support Phone": "Account Phone",      # new basedata column
        "Battery Kwh": "KWh",                  # new basedata column name
        "Battery KWh": "KWh",                  # variant casing
        "HO Email": "Support Emai",
        "HO Phone": "Account Phone",
        "Installer Email": "Support Emai",     # fallback
        "Enphase Contact Phone": "Account Phone",  # fallback
    }
    for old, new in _col_aliases.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    for col in ["Number of devices", "KWh"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df.dropna(subset=["Installer_Mapped"])
    df["Installer_Mapped"] = df["Installer_Mapped"].str.strip()
    df["Installer_Country"] = df["Installer_Country"].str.strip()
    df = _apply_installer_aliases(df)
    if "Status" in df.columns:
        df = df[df["Status"].str.strip().str.lower() != "inactive"].copy()
    df["Commercial Y/N"] = df["Site Type"].apply(
        lambda x: "Y" if str(x).strip().lower() == "commercial" else "N"
    )
    df["join_key"] = df["Installer_Country"] + " | " + df["Installer_Mapped"]
    df["Region"] = df["Installer_Country"].apply(_get_region)
    df["Quarter"] = df["Quarter"].str.strip()
    df["Year-week"] = df["Year-week"].str.strip()
    return df


def load_basedata_from_bytes(file_bytes_list: list) -> pd.DataFrame:
    """Load and combine multiple uploaded Excel files (one per quarter or combined)."""
    frames = []
    for fb in file_bytes_list:
        raw = pd.read_excel(fb, engine="openpyxl", dtype=str)
        frames.append(_clean_basedata(raw))
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["join_key", "Quarter", "Year-week", "Device Type", "Site Id"],
        keep="last"
    )
    return combined


@st.cache_data(show_spinner=False)
def load_basedata(path: str = BASEDATA_PATH) -> pd.DataFrame:
    return _clean_basedata(pd.read_excel(path, engine="openpyxl", dtype=str))


def _clean_disti_df(df: pd.DataFrame) -> pd.DataFrame:
    """Shared cleaning for any disti DataFrame."""
    df.columns = [c.strip() for c in df.columns]
    if "Activations" in df.columns:
        df["Activations"] = pd.to_numeric(df["Activations"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Installer Country", "Installer Name"])
    df = df[df["Installer Country"].str.strip() != ""]
    df = df[df["Installer Name"].str.strip() != ""]
    df["Installer Country"] = df["Installer Country"].str.strip()
    df["Installer Name"] = df["Installer Name"].str.strip()
    df["join_key"] = df["Installer Country"] + " | " + df["Installer Name"]
    return df


def _load_all_disti_sheets(path_or_bytes) -> pd.DataFrame:
    """Load all sheets from the disti file that contain Installer Country + Installer Name."""
    xl = pd.ExcelFile(path_or_bytes, engine="openpyxl")
    frames = []
    for sheet in xl.sheet_names:
        try:
            raw = xl.parse(sheet, dtype=str)
            raw.columns = [c.strip() for c in raw.columns]
            if "Installer Country" in raw.columns and "Installer Name" in raw.columns:
                frames.append(raw)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    return _clean_disti_df(combined)


def load_disti_from_bytes(file_bytes) -> pd.DataFrame:
    """Load disti mapping from an uploaded file object (all matching sheets)."""
    return _load_all_disti_sheets(file_bytes)


@st.cache_data(show_spinner=False)
def load_disti(path: str = DISTI_PATH) -> pd.DataFrame:
    """Load disti mapping from all matching sheets (Euro + ANZP + any future region)."""
    return _load_all_disti_sheets(path)
