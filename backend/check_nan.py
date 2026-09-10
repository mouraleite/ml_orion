import json

with open("summary_dump.json", "r", encoding="utf-16") as f:
    text = f.read()

if "NaN" in text or "Infinity" in text:
    print("FOUND NaN or Infinity!")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "NaN" in line or "Infinity" in line:
            print(f"Line {i}: {line.strip()}")
else:
    print("Clean JSON.")
