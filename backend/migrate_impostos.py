from sqlalchemy import text
from app.db.database import engine

with engine.connect() as con:
    try: 
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_pis FLOAT DEFAULT 0.65'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_cofins FLOAT DEFAULT 3.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_irpj FLOAT DEFAULT 0.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_csll FLOAT DEFAULT 0.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_outros FLOAT DEFAULT 0.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_total FLOAT DEFAULT 4.0'))
        con.commit()
        print('Colunas adicionadas com sucesso!')
    except Exception as e: 
        print('Erro ao adicionar colunas:', e)
