from app.db.database import SessionLocal
from app.api.routes.tracking import get_tracking_summary

db = SessionLocal()
summary = get_tracking_summary(db)
items = summary.get('items', []) if isinstance(summary, dict) else summary

for s in items:
    if not s.get('project_name'): continue
    if 'Reserva' in s['project_name'] or 'Morada' in s['project_name']:
        print(s['project_name'], s.get('tir_anual'))

db.close()
