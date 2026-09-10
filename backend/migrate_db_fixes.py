import sqlite3

def migrate():
    conn = sqlite3.connect('viabilidades.db')
    cursor = conn.cursor()
    
    # phase_exchanges
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN permuta_fisica_unidades INTEGER DEFAULT 0')
    except Exception as e: print("phase_exchanges.permuta_fisica_unidades:", e)
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN permuta_fisica_valor_unidade FLOAT DEFAULT 0.0')
    except Exception as e: print("phase_exchanges.permuta_fisica_valor_unidade:", e)
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN perc_area_terrenista FLOAT DEFAULT 100.0')
    except Exception as e: print("phase_exchanges.perc_area_terrenista:", e)
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN perc_area_investidor FLOAT DEFAULT 0.0')
    except Exception as e: print("phase_exchanges.perc_area_investidor:", e)
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN perc_area_empreendedor FLOAT DEFAULT 0.0')
    except Exception as e: print("phase_exchanges.perc_area_empreendedor:", e)
    
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN perc_parceria_terrenista FLOAT DEFAULT 38.5')
    except Exception as e: print("phase_exchanges.perc_parceria_terrenista:", e)
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN perc_parceria_investidor FLOAT DEFAULT 0.0')
    except Exception as e: print("phase_exchanges.perc_parceria_investidor:", e)
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN perc_parceria_empreendedor FLOAT DEFAULT 61.5')
    except Exception as e: print("phase_exchanges.perc_parceria_empreendedor:", e)

    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN abertura_terrenistas_json JSON')
    except Exception as e: print("phase_exchanges.abertura_terrenistas_json:", e)
    try:
        cursor.execute('ALTER TABLE phase_exchanges ADD COLUMN rateios_config_json JSON')
    except Exception as e: print("phase_exchanges.rateios_config_json:", e)

    # phase_fundings
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN tipo_funding VARCHAR DEFAULT "Plano Empresarial (Banco)"')
    except Exception as e: print("phase_fundings.tipo_funding:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN modo_volume VARCHAR DEFAULT "percentual"')
    except Exception as e: print("phase_fundings.modo_volume:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN volume_fixo FLOAT DEFAULT 0.0')
    except Exception as e: print("phase_fundings.volume_fixo:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN prazo_meses INTEGER DEFAULT 36')
    except Exception as e: print("phase_fundings.prazo_meses:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN securitizadora VARCHAR')
    except Exception as e: print("phase_fundings.securitizadora:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN estrutura_cri VARCHAR')
    except Exception as e: print("phase_fundings.estrutura_cri:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN icvm VARCHAR DEFAULT "ICVM 400"')
    except Exception as e: print("phase_fundings.icvm:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN gross_up FLOAT DEFAULT 9.65')
    except Exception as e: print("phase_fundings.gross_up:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN taxa_estruturacao FLOAT DEFAULT 0.0')
    except Exception as e: print("phase_fundings.taxa_estruturacao:", e)
    try:
        cursor.execute('ALTER TABLE phase_fundings ADD COLUMN diluir_custos BOOLEAN DEFAULT 0')
    except Exception as e: print("phase_fundings.diluir_custos:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
    print("Done migrating!")
