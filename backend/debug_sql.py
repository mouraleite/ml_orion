import sqlite3
import json

conn = sqlite3.connect('erp_ml.db')
c = conn.cursor()

# Get the latest viability phase
c.execute("SELECT id, viability_id FROM viability_phases ORDER BY id DESC LIMIT 1")
row = c.fetchone()
if row:
    phase_id = row[0]
    viab_id = row[1]
    print(f"Phase ID: {phase_id}")
    
    # We can just fetch all JSONs
    c.execute("SELECT * FROM viability_revenue WHERE phase_id = ?", (phase_id,))
    rev = c.fetchone()
    
    c.execute("SELECT * FROM viability_construction WHERE phase_id = ?", (phase_id,))
    const = c.fetchone()
    if const:
        print(f"Construction Custo Obras: {const[2]}")
        print(f"Curva Obras: {const[7][:100] if const[7] else None}")
        
    c.execute("SELECT * FROM viability_expenses WHERE phase_id = ?", (phase_id,))
    exp = c.fetchone()
    
    # We can run the calculate_viability_results if we fix the imports
    # Let's just fix the imports by importing everything first
    print("Done checking raw DB.")
else:
    print("No phase found")
