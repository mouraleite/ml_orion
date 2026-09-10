import os
from sqlalchemy import text
import sys

# Ajusta o sys.path para garantir que os módulos do app possam ser importados
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine

def add_columns():
    with engine.connect() as con:
        try: 
            con.execute(text('ALTER TABLE actual_transactions ADD COLUMN bill_id VARCHAR'))
            con.commit()
            print("Added bill_id")
        except Exception as e: print(e)
        try: 
            con.execute(text('ALTER TABLE actual_transactions ADD COLUMN creditor_name VARCHAR'))
            con.commit()
            print("Added creditor_name")
        except Exception as e: print(e)
        try: 
            con.execute(text('ALTER TABLE actual_transactions ADD COLUMN document_name VARCHAR'))
            con.commit()
            print("Added document_name")
        except Exception as e: print(e)
        try: 
            con.execute(text('ALTER TABLE actual_transactions ADD COLUMN document_number VARCHAR'))
            con.commit()
            print("Added document_number")
        except Exception as e: print(e)

if __name__ == "__main__":
    add_columns()
