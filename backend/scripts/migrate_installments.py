import os
import sys
import argparse
from datetime import datetime

# Garantir que o diretório raiz esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal, engine
from app.models.cost_center import CostCenter
from app.services.sienge_sync import sync_sales
from sqlalchemy import text

def main():
    print("Iniciando migração de installments_number...")
    
    # 1. Adicionar coluna na tabela se não existir
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE actual_transactions ADD COLUMN installments_number INTEGER DEFAULT 0"))
            print("Coluna installments_number adicionada com sucesso.")
    except Exception as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            print("A coluna installments_number já existe.")
        else:
            print(f"Erro ao adicionar coluna: {e}")
            
    # 2. Re-sincronizar os centros de custo
    db = SessionLocal()
    
    ccs = db.query(CostCenter).filter(CostCenter.track_in_dashboard == True).all()
    
    start_date = "2015-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    for cc in ccs:
        print(f"Ressincronizando Vendas para o Centro de Custo {cc.id_sienge} - {cc.nome}...")
        try:
            sync_sales(db, cc, start_date, end_date)
            print(f"Sucesso CC {cc.id_sienge}!")
        except Exception as e:
            print(f"Erro no CC {cc.id_sienge}: {e}")
            
    db.close()
    print("Migração concluída.")

if __name__ == "__main__":
    main()
