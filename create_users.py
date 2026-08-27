"""
Run this script ONCE to create config/users.yaml with hashed passwords.
Usage:
    python create_users.py

Edit the USERS list below to add real team members before running.
Default password for all users: enphase123  (change after first login)
"""
import yaml
import bcrypt
from pathlib import Path

USERS = [
    # (username,            display_name,               email,                            role,             country, rsm_name,                    password)
    ("admin",               "Admin",                    "admin@enphase.com",              "admin",          "",      "",                          "enphase123"),
    # Country Managers — set country to the ISO-2 code matching your Installer_Country column
    ("cm_fr",               "France CM",                "cm.fr@enphase.com",              "country_manager","FR",   "",                          "enphase123"),
    ("cm_nl",               "Netherlands CM",           "cm.nl@enphase.com",              "country_manager","NL",   "",                          "enphase123"),
    ("cm_de",               "Germany CM",               "cm.de@enphase.com",              "country_manager","DE",   "",                          "enphase123"),
    ("cm_be",               "Belgium CM",               "cm.be@enphase.com",              "country_manager","BE",   "",                          "enphase123"),
    ("cm_gb",               "UK CM",                    "cm.gb@enphase.com",              "country_manager","GB",   "",                          "enphase123"),
    ("cm_ch",               "Switzerland CM",           "cm.ch@enphase.com",              "country_manager","CH",   "",                          "enphase123"),
    # RSMs — rsm_name MUST match exactly the RSMs column value in basedata.xlsx
    ("rsm_virginie",        "Virginie Jonet",           "virginie@enphase.com",           "rsm",            "",     "Virginie Jonet",            "enphase123"),
    ("rsm_anish",           "Anish Shah",               "anish@enphase.com",              "rsm",            "",     "Anish Shah",                "enphase123"),
    ("rsm_carlos",          "Carlos Sellas",            "carlos@enphase.com",             "rsm",            "",     "Carlos Sellas",             "enphase123"),
    ("rsm_clement",         "Clement Trasfi",           "clement@enphase.com",            "rsm",            "",     "Clément Trasfi",            "enphase123"),
    ("rsm_david",           "David Duculty",            "david@enphase.com",              "rsm",            "",     "David Duculty",             "enphase123"),
    ("rsm_jan",             "Jan Roschek",              "jan@enphase.com",                "rsm",            "",     "Jan Roschek",               "enphase123"),
    ("rsm_kay",             "Kay Crombag",              "kay@enphase.com",                "rsm",            "",     "Kay Crombag",               "enphase123"),
    ("rsm_maarten",         "Maarten Riedijk",          "maarten@enphase.com",            "rsm",            "",     "Maarten Riedijk",           "enphase123"),
    ("rsm_nicolas",         "Nicolas Levavasseur",      "nicolas@enphase.com",            "rsm",            "",     "Nicolas LEVAVASSEUR",       "enphase123"),
    ("rsm_pascal",          "Pascal Broers",            "pascal@enphase.com",             "rsm",            "",     "Pascal Broers",             "enphase123"),
    ("rsm_romuald",         "Romuald Pannetier",        "romuald@enphase.com",            "rsm",            "",     "Romuald Pannetier",         "enphase123"),
    ("rsm_stephane",        "Stephane Chevrel",         "stephane@enphase.com",           "rsm",            "",     "Stephane Chevrel",          "enphase123"),
    ("rsm_tom",             "Tom Wilson",               "tom@enphase.com",                "rsm",            "",     "Tom Wilson",                "enphase123"),
]


def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


credentials = {"usernames": {}}
for username, name, email, role, country, rsm_name, pw in USERS:
    credentials["usernames"][username] = {
        "name": name,
        "email": email,
        "password": hash_pw(pw),
        "role": role,
        "country": country,
        "rsm_name": rsm_name,
    }

config = {
    "credentials": credentials,
    "cookie": {
        "expiry_days": 30,
        "key": "installer_ecosystem_v1_secret",
        "name": "installer_ecosystem_auth",
    },
}

out = Path("config/users.yaml")
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    yaml.dump(config, f, default_flow_style=False)

print(f"✓ Created {out} with {len(USERS)} users. Default password: enphase123")
