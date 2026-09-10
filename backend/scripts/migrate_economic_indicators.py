import sqlite3
import os
import sys

def migrate():
    # Caminho do banco de dados (relativo ao diretório do script)
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "erp_ml.db")
    print(f"Usando banco de dados em: {db_path}")

    # Conectar ao banco de dados
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Criar a nova tabela economic_indicators se não existir
        print("Criando tabela economic_indicators...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS economic_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR NOT NULL,
                index_type VARCHAR NOT NULL,
                valor FLOAT NOT NULL,
                tipo_unidade VARCHAR NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
        """)
        
        # Inserir alguns dados padrão, se estiver vazia
        cursor.execute("SELECT COUNT(*) FROM economic_indicators")
        count = cursor.fetchone()[0]
        if count == 0:
            print("Inserindo indicadores padrão...")
            cursor.execute("""
                INSERT INTO economic_indicators (nome, index_type, valor, tipo_unidade) 
                VALUES ('Cenário Padrão', 'IPCA', 4.5, '% a.a.')
            """)
            cursor.execute("""
                INSERT INTO economic_indicators (nome, index_type, valor, tipo_unidade) 
                VALUES ('Cenário Padrão', 'INCC', 5.0, '% a.a.')
            """)

        conn.commit()
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
