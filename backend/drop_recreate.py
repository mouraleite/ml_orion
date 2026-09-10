import sys
import os
from sqlalchemy import text

# Load environment first
from dotenv import load_dotenv
load_dotenv()

from app.db.database import engine

def drop_tables():
    with engine.connect() as conn:
        try:
            conn.execute(text("DROP TABLE phase_funding"))
            print("Dropped phase_funding")
        except Exception as e:
            print("Could not drop phase_funding:", e)
            
        try:
            conn.execute(text("DROP TABLE phase_fundings"))
            print("Dropped phase_fundings")
        except Exception as e:
            print("Could not drop phase_fundings:", e)
            
        try:
            conn.execute(text("DROP TABLE system_settings"))
            print("Dropped system_settings")
        except Exception as e:
            print("Could not drop system_settings:", e)
        conn.commit()
    
    # re-importing models and calling create_all
    from app.db.database import Base
    Base.metadata.create_all(bind=engine)
    print("Tables recreated.")

if __name__ == "__main__":
    drop_tables()
