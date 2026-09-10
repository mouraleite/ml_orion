import sqlite3

def run():
    conn = sqlite3.connect("viabilidades.db")
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE viabilities ADD COLUMN city VARCHAR DEFAULT 'Não informado';")
        conn.commit()
        print("Success")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run()
