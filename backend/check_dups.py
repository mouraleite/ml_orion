import sqlite3
conn = sqlite3.connect('viabilidades.db')
c = conn.cursor()
c.execute("""
    SELECT transaction_date, source_id, COUNT(*) 
    FROM actual_transactions 
    WHERE is_forecast=1 AND cost_center_id=206
    GROUP BY source_id 
    HAVING COUNT(*) > 1
    LIMIT 10
""")
duplicates = c.fetchall()
print(f"Number of distinct duplicated source_ids: {len(duplicates)}")
print(duplicates)
c.execute("SELECT COUNT(DISTINCT source_id) FROM actual_transactions WHERE is_forecast=1 AND cost_center_id=206")
print(f"Distinct source_ids: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM actual_transactions WHERE is_forecast=1 AND cost_center_id=206")
print(f"Total rows: {c.fetchone()[0]}")
conn.close()
