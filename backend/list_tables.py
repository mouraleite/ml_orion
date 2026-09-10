import sqlite3
c = sqlite3.connect('viabilidades.db').cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print([r[0] for r in c.fetchall()])
