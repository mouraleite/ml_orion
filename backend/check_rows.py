import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3

def check():
    conn = sqlite3.connect('viabilidades.db')
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM actual_transactions")
    print("Total rows in ActualTransaction:", cur.fetchone()[0])

if __name__ == '__main__':
    check()
