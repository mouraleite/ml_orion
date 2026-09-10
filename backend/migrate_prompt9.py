import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.models.fechamento import ClosedMonth
from app.models.user import User

def migrate():
    print("Iniciando migração (Prompt 9)...")
    
    # 1. Cria nova tabela fechamento_meses
    print("Criando tabela fechamento_meses...")
    ClosedMonth.metadata.create_all(bind=engine)
    
    # 2. Adiciona campos na tabela forecasts (SQLite syntax via ALTER TABLE)
    db = SessionLocal()
    try:
        # Check if columns exist first
        result = db.execute(text("PRAGMA table_info(forecasts);"))
        columns = [row[1] for row in result]
        
        if "usuario_edicao_id" not in columns:
            print("Adicionando usuario_edicao_id...")
            db.execute(text("ALTER TABLE forecasts ADD COLUMN usuario_edicao_id INTEGER REFERENCES users(id);"))
        else:
            print("usuario_edicao_id já existe.")
            
        if "data_inicio_edicao" not in columns:
            print("Adicionando data_inicio_edicao...")
            db.execute(text("ALTER TABLE forecasts ADD COLUMN data_inicio_edicao DATETIME;"))
        else:
            print("data_inicio_edicao já existe.")
            
        db.commit()
        print("Migração concluída com sucesso!")
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
