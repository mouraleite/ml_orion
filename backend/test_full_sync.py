from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.services.sienge_sync import sync_all_sienge_data

def test_full_sync():
    db = SessionLocal()
    cc = db.query(CostCenter).filter_by(id=206).first()
    if cc:
        print(f"Marcando {cc.nome} para track_in_dashboard = True temporariamente")
        cc.track_in_dashboard = True
        db.commit()
        
        # Desabilitar outros CCs para o teste ser mais rpido
        outros = db.query(CostCenter).filter(CostCenter.id != 206).all()
        for o in outros:
            o.track_in_dashboard = False
        db.commit()

        print("Rodando full_load=True para CC 206...")
        sync_all_sienge_data(db, full_load=True)
        print("Finalizado!")
    db.close()

if __name__ == "__main__":
    test_full_sync()
