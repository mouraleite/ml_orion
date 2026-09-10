"""
Script de migração DIRETO via sqlite3 (sem SQLAlchemy) para evitar problemas de lock.
Execução: cd backend && uv run python scripts/migrate_vision_direct.py
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Localizar o banco
from app.core.config import settings
db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
if not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(__file__), "..", db_path)
db_path = os.path.normpath(db_path)

print(f"=== Migração Direta de Visões Nomeadas ===")
print(f"Banco: {db_path}")

conn = sqlite3.connect(db_path, timeout=10)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Verificar se já migrou
cur.execute("SELECT COUNT(*) FROM visions")
if cur.fetchone()[0] > 0:
    print("✓ Migração já foi executada. Abortando.")
    conn.close()
    sys.exit(0)

try:
    # 2. Criar tabelas se não existirem
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS visions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            is_padrao INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fp_vision_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            financial_plan_id INTEGER NOT NULL REFERENCES planos_financeiros(id),
            vision_id INTEGER NOT NULL REFERENCES visions(id),
            vision_node_id INTEGER REFERENCES vision_nodes(id)
        );
    """)
    print("✓ Tabelas criadas/verificadas")

    # 3. Adicionar vision_id em vision_nodes se não existir
    try:
        cur.execute("ALTER TABLE vision_nodes ADD COLUMN vision_id INTEGER REFERENCES visions(id)")
        conn.commit()
        print("✓ Coluna vision_id adicionada em vision_nodes")
    except sqlite3.OperationalError:
        print("  Coluna vision_id já existe (OK)")

    # 4. Criar a Visão Padrão
    cur.execute(
        "INSERT INTO visions (nome, descricao, is_padrao) VALUES (?, ?, ?)",
        ("Visão Sienge", "Estrutura importada automaticamente do relatório do Sienge.", 1)
    )
    vision_id = cur.lastrowid
    print(f"✓ Visão Padrão criada com ID: {vision_id}")

    # 5. Atualizar vision_nodes com vision_id
    cur.execute("UPDATE vision_nodes SET vision_id = ?", (vision_id,))
    print(f"✓ {cur.rowcount} nós vinculados à Visão Padrão")

    # 6. Criar os fp_vision_links a partir dos vínculos existentes
    cur.execute("""
        SELECT id, vision_node_id FROM planos_financeiros 
        WHERE vision_node_id IS NOT NULL AND tp_conta != 'T'
    """)
    planos = cur.fetchall()
    
    links_criados = 0
    for plano in planos:
        cur.execute(
            "INSERT INTO fp_vision_links (financial_plan_id, vision_id, vision_node_id) VALUES (?, ?, ?)",
            (plano["id"], vision_id, plano["vision_node_id"])
        )
        links_criados += 1
    
    print(f"✓ {links_criados} vínculos plano<->nó criados")

    conn.commit()
    print("\n=== Migração concluída com sucesso! ===")
    print(f"  Visão Padrão ID: {vision_id}")
    print(f"  Nós vinculados: {cur.execute('SELECT COUNT(*) FROM vision_nodes').fetchone()[0]}")
    print(f"  Links criados: {links_criados}")

except Exception as e:
    conn.rollback()
    print(f"\n❌ Erro: {e}")
    raise
finally:
    conn.close()
