# ⚡ Installer Ecosystem — Enphase Euro Region

Streamlit analytics platform for installer activation classification, segmentation, and RSM coordination.

---

## Quick Start

### 1. First-time setup
```powershell
# Install Python 3.11 if needed
winget install Python.Python.3.11

# Install dependencies
pip install -r requirements.txt

# Create user accounts (run once; edits config/users.yaml)
python create_users.py
```

### 2. Launch app
```powershell
streamlit run app.py
```
Open **http://localhost:8501** in your browser.

---

## Default Login Credentials

| Username | Role | Scope | Password |
|---|---|---|---|
| `admin` | Admin | All countries | `enphase123` |
| `cm_fr` | Country Manager | France (FR) | `enphase123` |
| `cm_nl` | Country Manager | Netherlands (NL) | `enphase123` |
| `cm_de` | Country Manager | Germany (DE) | `enphase123` |
| `cm_be` | Country Manager | Belgium (BE) | `enphase123` |
| `rsm_virginie` | RSM | Virginie Jonet | `enphase123` |

> ⚠️ **Change passwords** in `create_users.py` and re-run before sharing with the team.

To add RSMs: edit the `USERS` list in `create_users.py` and re-run.

---

## Data Files

Place Excel files in the project root (or `data/` subfolder):

| File | Purpose |
|---|---|
| `basedata.xlsx` | All installer activation rows (filter: Status ≠ Inactive) |
| `Installer disti mapping.xlsx` | Distributor → Installer mapping (sheet: `2_Euro Activations (all devices`) |

> 📌 The app auto-detects these files in either the project root or `data/` subfolder.

---

## Classification Logic

| Dimension | Logic |
|---|---|
| **Segment** | Lost (0 activations current Q) · New (0 prior 4Q) · Declining (run-rate ↓25%+) · Growing (↑15%+) · Stable |
| **Tier** | Diamond (top 20/country) · Platinum (next 50) · Golden (next 100) · Silver (rest) — excludes Lost |
| **ABC** | Per-country volume share rolling prior 4Q: A≤80% · B≤95% · C=rest |
| **XYZ** | Coefficient of variation prior 4Q: X≤0.5 · Y<0.8 · Z≥0.8 |
| **Priority** | P1 = AX,AY,AZ,BX · P2 = BY,BZ,CX,CY,CZ |

---

## Features by Role

| Feature | Admin | Country Manager | RSM |
|---|---|---|---|
| All-country view | ✓ | — | — |
| Country-filtered view | ✓ | ✓ (own country) | — |
| RSM-filtered view | ✓ | — | ✓ (own RSMs) |
| Edit Category/Group/Priority | ✓ | ✓ | — |
| Post installer comments | ✓ | ✓ | ✓ |
| Raise action item → RSM | ✓ | ✓ | — |
| Inbox (receive action items) | — | — | ✓ |
| Refresh data cache | ✓ | — | — |
| Save quarter snapshot | ✓ | — | — |

---

## Project Structure

```
├── app.py                        # Streamlit entry point
├── requirements.txt
├── create_users.py               # One-time user setup script
├── config/users.yaml             # Auth config (bcrypt hashed passwords)
├── db/app.db                     # SQLite — overrides, comments, messages, snapshots
├── src/
│   ├── loader.py                 # Excel → DataFrames
│   ├── classifier.py             # Core classification engine
│   ├── abc_xyz.py                # ABC/XYZ/Priority logic
│   ├── distributor.py            # Top Disti 1 & 2 computation
│   ├── db.py                     # SQLAlchemy models + CRUD
│   └── views/
│       ├── installer_list.py     # Tab 1: Installer List
│       ├── device_view.py        # Tab 2: Device-Type View
│       ├── summary.py            # Tab 3: Country + RSM Summary
│       ├── group_patterns.py     # Tab 4: Group Patterns
│       └── inbox.py              # Inbox: CM→RSM messaging
└── utils/
    ├── helpers.py                # Quarter arithmetic + labels
    └── state_lookup.py           # State abbreviation → full name
```

---

## Refreshing Data

- **Admin → Dashboard tab → "Refresh Data Cache"** — re-reads Excel files and re-runs classification
- **Admin → Dashboard tab → "Save Quarter Snapshot"** — saves current classification to SQLite (used to detect Lost-Regained next quarter)
- On next upload of multi-quarter `basedata.xlsx` (50MB full history), all segments and ABC/XYZ will populate fully
