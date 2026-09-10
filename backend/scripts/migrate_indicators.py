import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('viabilidades.db')
        cursor = conn.cursor()
        
        print("Criando tabela global_indicators...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipca_padrao_valor FLOAT DEFAULT 4.5,
                ipca_padrao_tipo VARCHAR DEFAULT '% a.a.',
                incc_padrao_valor FLOAT DEFAULT 5.0,
                incc_padrao_tipo VARCHAR DEFAULT '% a.a.',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        print("Adicionando colunas de ipca e incc projetado em viabilities...")
        try:
            cursor.execute("ALTER TABLE viabilities ADD COLUMN ipca_projetado_valor FLOAT")
        except sqlite3.OperationalError:
            print("Coluna ipca_projetado_valor já existe.")

        try:
            cursor.execute("ALTER TABLE viabilities ADD COLUMN ipca_projetado_tipo VARCHAR DEFAULT '% a.a.'")
        except sqlite3.OperationalError:
            print("Coluna ipca_projetado_tipo já existe.")
            
        try:
            cursor.execute("ALTER TABLE viabilities ADD COLUMN incc_projetado_valor FLOAT")
        except sqlite3.OperationalError:
            print("Coluna incc_projetado_valor já existe.")
            
        try:
            cursor.execute("ALTER TABLE viabilities ADD COLUMN incc_projetado_tipo VARCHAR DEFAULT '% a.a.'")
        except sqlite3.OperationalError:
            print("Coluna incc_projetado_tipo já existe.")
            
        conn.commit()
        conn.close()
        print("Migração concluída com sucesso.")
    except Exception as e:
        print(f"Erro na migração: {e}")

if __name__ == '__main__':
    migrate()
