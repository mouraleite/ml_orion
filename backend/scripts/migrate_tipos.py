import sqlite3

def migrate():
    conn = sqlite3.connect('viabilidades.db')
    cursor = conn.cursor()
    
    # viability_constructions
    try:
        cursor.execute('ALTER TABLE viability_constructions ADD COLUMN custo_obras_tipo VARCHAR DEFAULT "R$"')
        cursor.execute('ALTER TABLE viability_constructions ADD COLUMN custo_projetos_tipo VARCHAR DEFAULT "%"')
        cursor.execute('ALTER TABLE viability_constructions ADD COLUMN aquisicao_area_tipo VARCHAR DEFAULT "R$"')
        cursor.execute('ALTER TABLE viability_constructions ADD COLUMN adm_obras_tipo VARCHAR DEFAULT "%"')
        print("Added columns to viability_constructions")
    except sqlite3.OperationalError as e:
        print(f"Error adding to constructions: {e}")

    # viability_expenses
    try:
        cursor.execute('ALTER TABLE viability_expenses RENAME COLUMN marketing_perc_vgv TO marketing_valor')
        cursor.execute('ALTER TABLE viability_expenses RENAME COLUMN comercial_perc_vgv TO comercial_valor')
        cursor.execute('ALTER TABLE viability_expenses RENAME COLUMN adm_perc_vgv TO adm_valor')
        
        cursor.execute('ALTER TABLE viability_expenses ADD COLUMN marketing_tipo VARCHAR DEFAULT "%"')
        cursor.execute('ALTER TABLE viability_expenses ADD COLUMN comercial_tipo VARCHAR DEFAULT "%"')
        cursor.execute('ALTER TABLE viability_expenses ADD COLUMN adm_tipo VARCHAR DEFAULT "%"')
        print("Added/Renamed columns in viability_expenses")
    except sqlite3.OperationalError as e:
        print(f"Error modifying expenses: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
