import os
from sqlalchemy import create_engine, text

# Ajuste conforme seu docker-compose ou .env
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/viabilidades")
engine = create_engine(db_url)

with engine.connect() as con:
    try: 
        con.execute(text('ALTER TABLE viabilities ADD COLUMN version_of_id INTEGER REFERENCES viabilities(id) ON DELETE SET NULL'))
        con.commit()
    except Exception as e: 
        print("version_of_id:", e)
    
    try: 
        con.execute(text('ALTER TABLE viabilities ADD COLUMN taxa_desconto_vpl FLOAT DEFAULT 12.0'))
        con.commit()
    except Exception as e: 
        print("taxa_desconto_vpl:", e)
    
    try: 
        con.execute(text('ALTER TABLE phase_exchanges ADD COLUMN permuta_rateio_obras BOOLEAN DEFAULT FALSE'))
        con.commit()
    except Exception as e: 
        print("permuta_rateio_obras:", e)
        
    try: 
        con.execute(text('ALTER TABLE phase_exchanges ADD COLUMN permuta_rateio_mkt BOOLEAN DEFAULT FALSE'))
        con.commit()
    except Exception as e: 
        print("permuta_rateio_mkt:", e)
        
    try: 
        con.execute(text('ALTER TABLE phase_exchanges ADD COLUMN permuta_rateio_adm BOOLEAN DEFAULT FALSE'))
        con.commit()
    except Exception as e: 
        print("permuta_rateio_adm:", e)

    try: 
        con.execute(text('ALTER TABLE viability_revenues ADD COLUMN plano_ativo VARCHAR'))
        con.commit()
    except Exception as e: 
        print("plano_ativo:", e)
        
    try: 
        con.execute(text('ALTER TABLE viability_revenues ADD COLUMN condicoes_pagamento_json JSON DEFAULT \'[]\''))
        con.commit()
    except Exception as e: 
        print("condicoes_pagamento_json:", e)

    # Impostos
    try: 
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_pis FLOAT DEFAULT 0.65'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_cofins FLOAT DEFAULT 3.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_irpj FLOAT DEFAULT 0.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_csll FLOAT DEFAULT 0.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_outros FLOAT DEFAULT 0.0'))
        con.execute(text('ALTER TABLE phase_taxes ADD COLUMN aliquota_total FLOAT DEFAULT 4.0'))
        con.commit()
    except Exception as e: 
        print("phase_taxes novos impostos:", e)

    try: 
        con.execute(text('ALTER TABLE viability_revenues ADD COLUMN origem_correcao VARCHAR DEFAULT \'PROJETADO\''))
        con.commit()
    except Exception as e: 
        print("origem_correcao:", e)

    try: 
        con.execute(text('ALTER TABLE viability_revenues ADD COLUMN nome_indice_mercado VARCHAR'))
        con.commit()
    except Exception as e: 
        print("nome_indice_mercado:", e)

    try: 
        con.execute(text('ALTER TABLE viability_expenses ADD COLUMN comissao_corretagem_valor FLOAT DEFAULT 0.0'))
        con.commit()
    except Exception as e: 
        print("comissao_corretagem_valor:", e)

print("Migrações manuais concluídas!")
