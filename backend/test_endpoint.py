import sys, glob, importlib
sys.path.append('C:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
for f in glob.glob('app/models/*.py'):
    mod = f.replace('\\', '.').replace('/', '.')[:-3]
    importlib.import_module(mod)
from app.db.database import SessionLocal
from app.api.routes.orcamentos import get_orcamento_receitas
from app.models.user import User
from app.models.departamento import Departamento
db = SessionLocal()
user = db.query(User).filter(User.id == 1).first()
dept = db.query(Departamento).filter(Departamento.id == 1).first()
try:
    res = get_orcamento_receitas(2026, False, db, dept, user)
    print('Success:', res.keys())
except Exception as e:
    import traceback
    traceback.print_exc()

