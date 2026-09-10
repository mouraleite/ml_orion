import sqlite3
import sys

def check():
    conn = sqlite3.connect('viabilidades.db')
    cur = conn.cursor()
    cur.execute("SELECT substr(transaction_date, 1, 4) as ano, transaction_type, sum(value) FROM actual_transactions WHERE is_forecast=1 GROUP BY ano, transaction_type ORDER BY ano")
    for row in cur.fetchall():
        print(row)

if __name__ == '__main__':
    check()
