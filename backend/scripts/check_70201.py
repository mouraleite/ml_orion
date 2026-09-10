import os
import sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy.orm import Session
from sqlalchemy import func, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.db.database import SessionLocal
from app.services.carga_forecast_sharepoint import parse_sienge_forecast_report, FORECAST_BASE_DIR
import glob

db = SessionLocal()
folder = os.path.join(FORECAST_BASE_DIR, "Forecast - 7+5")
files = glob.glob(os.path.join(folder, "**", "*.xlsx"), recursive=True)

raw_data = []
for f in files:
    if "~$" in f: continue
    try:
        raw_data.extend(parse_sienge_forecast_report(f, db))
    except Exception as e:
        pass

cc_70201 = [r for r in raw_data if r['cc_id_sienge'] == '70201']
print(f"Total rows for 70201: {len(cc_70201)}")
for r in cc_70201:
    print(r)
    
total = sum(r['orcado'] for r in cc_70201)
print(f"Total orcado: {total}")
