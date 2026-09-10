import sys, glob, os
sys.path.append('C:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend')
import importlib
for f in glob.glob('app/models/*.py'):
    mod = f.replace('\\', '.').replace('/', '.')[:-3]
    importlib.import_module(mod)
from app.db.database import SessionLocal
from app.services.carga_inicial_sharepoint import run_carga_inicial
db = SessionLocal()
run_carga_inicial(db)
db.close()
