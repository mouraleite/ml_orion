import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.forecast import Forecast
from app.api.routes.orcamentos import get_comparativo_versoes
from app.models.seguranca import Departamento

db = SessionLocal()
dept = db.query(Departamento).filter(Departamento.id == 1).first()

# Mocking current_user dependency bypass isn't needed if we don't pass it or if the function doesn't use it directly without Depends
# Let's inspect the function definition
# get_comparativo_versoes(versao_a: str, versao_b: str, ano: int, tipo: str, consolidado: bool, db, dept, current_user)
# Wait, get_comparativo_versoes takes current_user. We can pass None if it doesn't crash.

try:
    res = get_comparativo_versoes("FC_Forecast - 7+5", "OC_Original - 2024", 2026, "DESPESAS", False, db, dept, None)
    total_a = 0
    total_b = 0
    for inc in res['inclusoes']:
        total_b += inc.get('total', 0)
    for exc in res['exclusoes']:
        total_a += exc.get('total', 0)
    for alt in res['alteracoes']:
        total_a += alt['versao_a'].get('total', 0)
        total_b += alt['versao_b'].get('total', 0)
    print(f"Total A: {total_a}")
    print(f"Total B: {total_b}")
    print(f"Lenth alteracoes: {len(res['alteracoes'])}, inclusoes: {len(res['inclusoes'])}, exclusoes: {len(res['exclusoes'])}")
except Exception as e:
    import traceback
    traceback.print_exc()
