import sys

with open('app/api/routes/tracking.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_else_block = False
for i, line in enumerate(lines):
    if line.strip() == "for sub_cc in ccs:":
        if lines[i-1].strip() == "else:":
            in_else_block = True
            continue
    
    if in_else_block:
        if line.strip() == "":
            pass
        elif line.startswith("            "):
            lines[i] = "    " + line
        elif line.startswith("        # Calcular Margem"):
            in_else_block = False

with open('app/api/routes/tracking.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
