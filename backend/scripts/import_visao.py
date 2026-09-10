import sys
import os
import pandas as pd

# Adicionar o diretório raiz ao path para importar os módulos da aplicação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal, Base, engine
from app.models.vision import VisionNode
from app.models.financial_plan import FinancialPlan

def import_visao():
    print("Iniciando importação da Visão (DRE)...")
    
    # Recriar as tabelas para garantir que vision_nodes exista e financial_plans tenha vision_node_id
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Limpar visões antigas
    db.query(VisionNode).delete()
    
    # Desvincular todos os planos financeiros de qualquer visão anterior
    db.query(FinancialPlan).update({"vision_node_id": None})
    db.commit()

    file_path = os.path.join(os.path.dirname(__file__), "../../relatorio.xlsx")
    if not os.path.exists(file_path):
        print(f"Erro: Arquivo não encontrado em {file_path}")
        return

    df = pd.read_excel(file_path)
    
    # Começar a partir da linha onde as categorias de fato começam (baseado na estrutura vista, linha 9 é o cabeçalho)
    # Mas como o pandas já trata a primeira linha como cabeçalho ou índices, vamos iterar usando iterrows
    
    current_vision_node = None
    nodes_created = 0
    plans_linked = 0
    
    for index, row in df.iterrows():
        col0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else "nan"
        col1 = str(row.iloc[1]) if pd.notna(row.iloc[1]) else "nan"
        col2 = str(row.iloc[2]) if pd.notna(row.iloc[2]) else "nan"
        
        # Ignora as linhas de cabeçalho do Sienge
        if col0.lower() == 'código' or col0 == 'nan' and col2 == 'nan':
            continue
            
        # É um Nó de Visão (ex: 01, 01.01)
        if col0 != 'nan':
            codigo = col0.strip()
            descricao = col1.strip()
            
            # Alguns códigos podem vir como numéricos do excel (ex: 1 em vez de 01). 
            # Se for necessário formatar, podemos fazer aqui. Mas vamos manter como veio no excel.
            
            # Criar o nó
            node = VisionNode(codigo=codigo, descricao=descricao)
            db.add(node)
            db.commit()
            db.refresh(node)
            current_vision_node = node
            nodes_created += 1
            print(f"Criado Nó Visão: {codigo} - {descricao}")
            
        # É uma conta filha associada ao nó atual (ex: 1.01.01.01 - Receita de Venda...)
        elif col0 == 'nan' and col2 != 'nan' and current_vision_node is not None:
            text = col2.strip()
            if " - " in text:
                prefix = text.split(" - ")[0].strip()
                
                # Transformar o prefixo '1.01.01.01' no db_id '1010101'
                db_id = prefix.replace(".", "")
                
                # Buscar o Plano Financeiro no banco
                fp = db.query(FinancialPlan).filter(FinancialPlan.db_id == db_id).first()
                if fp:
                    fp.vision_node_id = current_vision_node.id
                    plans_linked += 1
                    # print(f"  -> Vinculado {fp.name} a {current_vision_node.codigo}")
                else:
                    print(f"  -> AVISO: Plano Financeiro {db_id} não encontrado no banco de dados local.")

    db.commit()
    db.close()
    
    print(f"\nImportação concluída com sucesso!")
    print(f"Total de Nós da Visão criados: {nodes_created}")
    print(f"Total de Planos Financeiros vinculados: {plans_linked}")

if __name__ == "__main__":
    import_visao()
