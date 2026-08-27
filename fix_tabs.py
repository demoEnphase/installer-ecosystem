"""Fix corrupted emoji in tab definitions."""
path = r'c:\Shubha Bharti\Installer Ecosystem\app.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
i = 0
while i < len(lines):
    line = lines[i]
    # RSM tabs block: line with "My Dashboard" that has replacement char
    if 'My Dashboard' in line and '\ufffd' in line:
        out.append('    tabs = st.tabs(["🏠 My Dashboard", "📈 Summary",\n')
        i += 1
        continue
    # Admin tabs block: line with "🏠 Dashboard" that has replacement char
    if '🏠 Dashboard' in line and '\ufffd' in line:
        out.append('    tabs = st.tabs(["🏠 Dashboard", "📈 Summary", "📋 Installer List",\n')
        i += 1
        # skip next continuation line if it still has the garbled Installer List
        if i < len(lines) and '\ufffd' in lines[i] and 'Installer List' in lines[i]:
            i += 1
        continue
    out.append(line)
    i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(out)
print("Done. Lines written:", len(out))
