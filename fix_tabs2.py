"""Fix corrupted emoji in tab definitions and swap tab order."""
import re

path = r"c:\Shubha Bharti\Installer Ecosystem\app.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Replace RSM tab block
old_rsm = (
    'if role == "rsm":\n'
    '    tabs = st.tabs(["🏠 My Dashboard", "📈 Summary",\n'
    '                    "\ufffd All Devices", "📋 Installers List", "📬 Inbox"])\n'
    '    tab_dash, tab_sum, tab_list, tab_dev, tab_inbox = tabs'
)
new_rsm = (
    'if role == "rsm":\n'
    '    tabs = st.tabs(["🏠 My Dashboard", "📈 Summary",\n'
    '                    "📋 Installers List", "📱 All Devices", "📬 Inbox"])\n'
    '    tab_dash, tab_sum, tab_dev, tab_list, tab_inbox = tabs'
)

# Replace admin/CM tab block
old_adm = (
    'else:\n'
    '    tabs = st.tabs(["🏠 Dashboard", "📈 Summary", "\ufffd All Devices",\n'
    '                    "\ufffd Installers List", "🏆 Group Patterns", "📬 Inbox"])\n'
    '    tab_dash, tab_sum, tab_list, tab_dev, tab_gp, tab_inbox = tabs'
)
new_adm = (
    'else:\n'
    '    tabs = st.tabs(["🏠 Dashboard", "📈 Summary", "📋 Installers List",\n'
    '                    "📱 All Devices", "🏆 Group Patterns", "📬 Inbox"])\n'
    '    tab_dash, tab_sum, tab_dev, tab_list, tab_gp, tab_inbox = tabs'
)

if old_rsm in src:
    src = src.replace(old_rsm, new_rsm)
    print("RSM tabs fixed")
else:
    print("RSM block NOT found - check encoding")

if old_adm in src:
    src = src.replace(old_adm, new_adm)
    print("Admin tabs fixed")
else:
    print("Admin block NOT found - check encoding")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Done")
