import sqlite3
import sys

def add_column():
    conn = sqlite3.connect('viabilidades.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE cost_centers ADD COLUMN partnership_config_id INTEGER")
        print("Column added successfully.")
    except sqlite3.OperationalError as e:
        print("Column might already exist:", e)
    
    # Check if table partnership_configs exists, if not main.py will create it, 
    # but we can force it here just in case.
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partnership_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR UNIQUE,
                rules JSON
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_partnership_configs_name ON partnership_configs(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_partnership_configs_id ON partnership_configs(id)")
    except Exception as e:
        print("Error creating partnership_configs:", e)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_column()
