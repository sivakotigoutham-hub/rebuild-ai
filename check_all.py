with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines[640:660], 641):
    indent = len(line) - len(line.lstrip(' '))
    # Check for tabs
    has_tab = '\t' in line
    stripped = line.strip()
    print(f'{i}: indent={indent:2d} tabs={has_tab} | {stripped[:50]}')"