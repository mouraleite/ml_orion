from app.db.database import SessionLocal
from app.services.sienge_sync import sync_units, sync_sales
from app.models.cost_center import CostCenter
from app.models.unit import Unit
from app.models.actual_transaction import ActualTransaction

db = SessionLocal()
try:
    print("Buscando CC...")
    cc = db.query(CostCenter).filter_by(id_sienge=14100).first()
    if not cc:
        print("CC não encontrado")
        exit()
        
    print(f"Sincronizando Unidades do CC {cc.nome}...")
    sync_units(db, cc)
    
    print("Sincronizando Vendas (Corrigindo Emitido e Vínculo com Units)...")
    sync_sales(db, cc, "2001-01-01", "2050-12-31")
    
    print("\nTotal de Unidades:", db.query(Unit).filter_by(cost_center_id=cc.id).count())
    print("Total de Vendas Válidas (VGV):", db.query(ActualTransaction).filter_by(category="VGV Vendido").count())
    print("Total de Distratos:", db.query(ActualTransaction).filter_by(category="Distrato").count())
    
    print("\nExemplo de Venda Vinculada à Unidade:")
    venda = db.query(ActualTransaction).filter(ActualTransaction.unit_id.isnot(None), ActualTransaction.transaction_type=="SALE").first()
    if venda:
        print(f"Venda: {venda.source_id} - R$ {venda.value} - Unit: {venda.unit.name} ({venda.unit.private_area} m2)")
    
finally:
    db.close()
