import sqlite3
import json

try:
    conn = sqlite3.connect('viabilidades.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print("Tables:", tables)
    
    if "viability_phases" in tables:
        c.execute("SELECT id FROM viability_phases ORDER BY id DESC LIMIT 1")
    elif "phases" in tables:
        c.execute("SELECT id FROM phases ORDER BY id DESC LIMIT 1")
    else:
        print("No phases table found")
        exit()
        
    phase_id = c.fetchone()[0]
    print("Phase ID:", phase_id)
    
    # Check funding
    c.execute("SELECT * FROM phase_fundings WHERE phase_id = ?", (phase_id,))
    funding = c.fetchone()
    print("Funding:", funding is not None)
    
    # Check construction
    c.execute("SELECT * FROM viability_constructions WHERE phase_id = ?", (phase_id,))
    const = c.fetchone()
    print("Construction configured:", const is not None)
    if const:
        print("Const row:", const)

except Exception as e:
    print("Error:", e)
