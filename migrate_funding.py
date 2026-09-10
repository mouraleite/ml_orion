import sqlite3

def migrate():
    conn = sqlite3.connect('backend/app.db')
    cursor = conn.cursor()

    try:
        # Phase Fundings migration
        cursor.execute("ALTER TABLE phase_funding RENAME COLUMN perc_financiado TO percentual_obra_financiado;")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE phase_funding RENAME COLUMN taxa_juros_aa TO taxa_juros;")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN tipo_funding VARCHAR DEFAULT 'Plano Empresarial (Banco)';")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN modo_volume VARCHAR DEFAULT 'percentual';")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN volume_fixo FLOAT DEFAULT 0.0;")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN prazo_meses INTEGER DEFAULT 36;")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN securitizadora VARCHAR;")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN estrutura_cri VARCHAR;")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN icvm VARCHAR DEFAULT 'ICVM 400';")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN gross_up FLOAT DEFAULT 9.65;")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN taxa_estruturacao FLOAT DEFAULT 0.0;")
        cursor.execute("ALTER TABLE phase_funding ADD COLUMN diluir_custos BOOLEAN DEFAULT 0;")
        
        # System settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR UNIQUE,
                value JSON,
                updated_at DATETIME
            )
        ''')
    except Exception as e:
        print("Error migrating phase_funding:", e)
        
    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
