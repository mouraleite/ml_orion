import json
from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.models.construction import ViabilityConstruction
from app.models.revenue import ViabilityRevenue
from app.models.expenses import ViabilityExpenses
from app.models.phase import Phase

def fix():
    db = sessionmaker(bind=engine)()
    
    constructions = db.query(ViabilityConstruction).all()
    for c in constructions:
        changed = False
        if isinstance(c.curva_obras_json, str):
            try: c.curva_obras_json = json.loads(c.curva_obras_json); changed = True
            except: pass
        if isinstance(c.curva_projetos_json, str):
            try: c.curva_projetos_json = json.loads(c.curva_projetos_json); changed = True
            except: pass
        if isinstance(c.curva_aquisicao_json, str):
            try: c.curva_aquisicao_json = json.loads(c.curva_aquisicao_json); changed = True
            except: pass
        if changed: db.add(c)
        
    revenues = db.query(ViabilityRevenue).all()
    for r in revenues:
        changed = False
        if isinstance(r.velocidade_vendas_json, str):
            try: r.velocidade_vendas_json = json.loads(r.velocidade_vendas_json); changed = True
            except: pass
        if changed: db.add(r)
        
    expenses = db.query(ViabilityExpenses).all()
    for e in expenses:
        changed = False
        if isinstance(e.curva_marketing_json, str):
            try: e.curva_marketing_json = json.loads(e.curva_marketing_json); changed = True
            except: pass
        if isinstance(e.curva_comercial_json, str):
            try: e.curva_comercial_json = json.loads(e.curva_comercial_json); changed = True
            except: pass
        if changed: db.add(e)
        
    db.commit()
    print("DB FIXED")

fix()
