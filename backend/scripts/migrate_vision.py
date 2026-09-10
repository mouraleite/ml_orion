"""
Script de migração: Move os dados existentes para o novo modelo de Visões Nomeadas.

Execução: cd backend && uv run python scripts/migrate_vision.py

O que faz:
1. Cria uma Visão Padrão chamada "Visão Sienge" (is_padrao=True)
2. Copia todos os VisionNodes existentes (sem vision_id) para dentro dela
3. Cria os FinancialPlanVisionLink para todos os planos vinculados
4. Remove o campo vision_node_id de planos_financeiros (via ALTER TABLE)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import Base, engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

print("=== Migração de Visões Nomeadas ===")

# Conectar ao banco
Session = sessionmaker(bind=engine)

# database.py já importa todos os modelos ao ser importado acima
from app.models.financial_plan import FinancialPlan
from app.models.vision import Vision, VisionNode, FinancialPlanVisionLink

# Criar novas tabelas
print("Criando novas tabelas...")
Base.metadata.create_all(bind=engine)

# Adicionar coluna vision_id em vision_nodes se não existir (SQLite não tem IF NOT EXISTS para colunas)
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE vision_nodes ADD COLUMN vision_id INTEGER REFERENCES visions(id)"))
        conn.commit()
        print("  Coluna vision_id adicionada em vision_nodes")
    except Exception:
        print("  Coluna vision_id já existe em vision_nodes (OK)")

with Session() as db:
    # 1. Verificar se já migrou
    existing = db.query(Vision).first()
    if existing:
        print("✓ Migração já foi executada anteriormente. Abortando para evitar duplicação.")
        sys.exit(0)

    print("Lendo VisionNodes existentes...")
    
    # Ler nodes existentes diretamente via SQL para evitar problemas de modelo antigo
    with engine.connect() as conn:
        old_nodes = conn.execute(text("SELECT id, codigo, descricao FROM vision_nodes")).fetchall()
        print(f"  Encontrados {len(old_nodes)} nós existentes")
        
        # Verificar se há planos vinculados
        try:
            old_links = conn.execute(text(
                "SELECT id, vision_node_id FROM planos_financeiros WHERE vision_node_id IS NOT NULL"
            )).fetchall()
            print(f"  Encontrados {len(old_links)} planos vinculados")
        except Exception:
            old_links = []
            print("  Coluna vision_node_id não encontrada nos planos financeiros")

    # 2. Criar a Visão Padrão
    print("Criando Visão Padrão 'Visão Sienge'...")
    visao_padrao = Vision(
        nome="Visão Sienge",
        descricao="Estrutura importada automaticamente do relatório do Sienge.",
        is_padrao=True
    )
    db.add(visao_padrao)
    db.flush()
    print(f"  Visão Padrão criada com ID: {visao_padrao.id}")

    # 3. Atualizar os VisionNodes existentes com o vision_id (UPDATE em vez de INSERT)
    print("Vinculando nós existentes à Visão Padrão...")
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE vision_nodes SET vision_id = :vid"),
            {"vid": visao_padrao.id}
        )
        conn.commit()
        print(f"  {result.rowcount} nós atualizados")

    # 4. Criar os links plano <-> nó usando os IDs originais (não mudaram)
    if old_links:
        print("Criando vínculos plano financeiro <-> nó...")
        migrated_links = 0
        for plano_row in old_links:
            old_node_id = plano_row.vision_node_id
            link = FinancialPlanVisionLink(
                financial_plan_id=plano_row.id,
                vision_id=visao_padrao.id,
                vision_node_id=old_node_id  # ID do nó não mudou, só adicionamos vision_id
            )
            db.add(link)
            migrated_links += 1
        print(f"  {migrated_links} vínculos criados")

    db.commit()
    print("\n=== Migração concluída com sucesso! ===")
    print(f"  Visão Padrão: '{visao_padrao.nome}' (ID: {visao_padrao.id})")
    print(f"  Nós vinculados: {len(old_nodes)}")
    print(f"  Planos vinculados: {len(old_links)}")
    print()
    print("PRÓXIMO PASSO: Reinicie o servidor backend para carregar os novos modelos.")
