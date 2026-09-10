import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('viabilidades.db')
        cursor = conn.cursor()
        
        # Obter todos os cenários únicos já cadastrados nos projetos
        cursor.execute('SELECT DISTINCT cenario FROM phase_physical_data WHERE cenario IS NOT NULL AND cenario != ""')
        existing_in_projects = [row[0] for row in cursor.fetchall()]
        
        # Cenários padrões
        default_scenarios = [
            "Pessimista +",
            "Pessimista",
            "Neutro",
            "Otimista",
            "Otimista +"
        ]
        
        # Juntar todos
        all_scenarios = list(set(existing_in_projects + default_scenarios))
        
        # Inserir na tabela scenarios se não existirem
        added_count = 0
        for name in all_scenarios:
            cursor.execute('SELECT id FROM scenarios WHERE nome = ?', (name,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO scenarios (nome) VALUES (?)', (name,))
                added_count += 1
                
        conn.commit()
        print(f"Migração concluída! {added_count} cenários adicionados ao cadastro.")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate()
