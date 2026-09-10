import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

import app.main # Ensure all models are loaded
from app.db.database import SessionLocal
from app.models.departamento import Departamento
from app.api.routes.orcamentos import get_orcamento_despesas

# mock user
class MockUser:
    def __init__(self):
        self.id = 9999
        self.role = "DIRETOR"

db = SessionLocal()
try:
    dept = db.query(Departamento).first()
    if not dept:
        print("Nenhum departamento encontrado.")
    else:
        res = get_orcamento_despesas(2027, db, dept, MockUser())
        print("Success:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
