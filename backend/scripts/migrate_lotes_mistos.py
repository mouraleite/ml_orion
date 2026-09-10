import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('viabilidades.db')
        cursor = conn.cursor()
        
        # phase_physical_data
        try:
            cursor.execute('ALTER TABLE phase_physical_data ADD COLUMN area_lotes_mistos FLOAT DEFAULT 0.0')
            cursor.execute('ALTER TABLE phase_physical_data ADD COLUMN qtde_lotes_mistos INTEGER DEFAULT 0')
            cursor.execute('ALTER TABLE phase_physical_data ADD COLUMN valor_venda_misto_m2 FLOAT DEFAULT 0.0')
            print("Colunas de lotes mistos adicionadas com sucesso.")
        except sqlite3.OperationalError as e:
            print(f"Erro ao adicionar colunas ou elas já existem: {e}")

        conn.commit()
    except Exception as e:
        print(f"Erro geral: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
