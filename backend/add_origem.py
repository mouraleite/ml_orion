from app.db.database import engine
from sqlalchemy import text

with engine.connect() as con:
    try: 
        con.execute(text('ALTER TABLE orcamento_venda_itens ADD COLUMN origem_venda VARCHAR'))
        con.commit()
        print("Column added to orcamento_venda_itens")
    except Exception as e: 
        print("Error orcamento_venda_itens:", e)

    try: 
        con.execute(text('ALTER TABLE forecast_venda_itens ADD COLUMN origem_venda VARCHAR'))
        con.commit()
        print("Column added to forecast_venda_itens")
    except Exception as e: 
        print("Error forecast_venda_itens:", e)
