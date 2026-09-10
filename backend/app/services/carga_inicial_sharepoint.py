import os
import glob
import pandas as pd
import math
import logging
from typing import List, Dict, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.migration import MigrationMapping
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.actual_transaction import ActualTransaction
from app.services.carga_forecast_sharepoint import get_sync_state, save_sync_state

SHAREPOINT_BASE_DIR = r"C:\Users\Usuario\MOURA LEITE DESENVOLVIMENTO & URBANIZACAO LTDA\Banco de Dados - Documentos\Sienge - 2653 - Comparativo Orçamento Empresarial X Realizado Agrupado\2026\1ª VERSÃO - ANALITICO - consolidar mes 0"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def parse_sienge_report(filepath: str, db: Session) -> List[Dict[str, Any]]:
    """
    Lê uma planilha Sienge, extrai o Centro de Custo, percorre os meses
    e gera as linhas de Orçado e Realizado.
    Retorna uma lista de dicionários com os dados brutos e outra com pendências de mapeamento.
    """
    df = pd.read_excel(filepath, header=None)
    
    cc_name_raw = None
    cc_name = None
    meses_cols = {}
    
    raw_data = []
    
    meses_map = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
    }
    
    for idx in range(len(df)):
        row = df.iloc[idx].values
        
        # 1. Verifica se a linha define um novo Centro de Custo
        found_cc = False
        for i, val in enumerate(row):
            if str(val).strip().lower() == "centro de custo":
                # Procurar próximo valor válido
                for j in range(i+1, len(row)):
                    if pd.notna(row[j]) and str(row[j]).strip():
                        cc_name_raw = str(row[j]).strip()
                        cc_name = cc_name_raw.split("-", 1)[-1].strip() if "-" in cc_name_raw else cc_name_raw
                        # Extrai o código Sienge numérico (ex: "13300" de "13300 - BOTUCATU - LIVIA")
                        import re as _re
                        m = _re.match(r'^(\d+)', cc_name_raw)
                        cc_id_sienge = m.group(1) if m else None
                        found_cc = True
                        break
                break
        
        if found_cc:
            continue
            
        if not cc_name_raw:
            continue
            
        # 2. Verifica se a linha define os meses (cabeçalho de tabela)
        found_months = False
        for i, val in enumerate(row):
            if pd.notna(val):
                val_str = str(val).strip().lower()
                if "/" in val_str:
                    m_str = val_str.split("/")[0]
                    if m_str in meses_map:
                        found_months = True
                        break
                        
        if found_months:
            meses_encontrados = []
            for i, val in enumerate(row):
                if pd.notna(val):
                    val_str = str(val).strip().lower()
                    if "/" in val_str:
                        parts = val_str.split("/")
                        if len(parts) == 2 and parts[0] in meses_map:
                            meses_encontrados.append((meses_map[parts[0]], int(parts[1]), i))
                            
            if meses_encontrados:
                meses_cols = {}
                if idx + 1 < len(df):
                    for m, y, i in meses_encontrados:
                        or_col = None
                        re_col = None
                        # Procura 'orçado' e 'realizado' nas colunas adjacentes (devido a mesclagem do Excel)
                        for j in range(max(0, i-1), min(len(df.columns), i+4)):
                            val_11 = str(df.iloc[idx+1, j]).strip().lower()
                            if ("orçado" in val_11 or "orcado" in val_11) and or_col is None:
                                or_col = j
                            elif "realizado" in val_11 and re_col is None:
                                re_col = j
                        meses_cols[(m, y)] = {"orçado": or_col, "realizado": re_col}
            continue # Pula a linha de meses

        # 3. Lendo dados analíticos
        tipo = str(row[4]).strip() if pd.notna(row[4]) else ""
        if tipo == "R":
            conta_codigo = str(row[0]).strip()
            conta_desc = str(row[1]).strip()
            
            for mes_ano, cols in meses_cols.items():
                mes, ano = mes_ano
                orcado_col = cols["orçado"]
                realizado_col = cols["realizado"]
                
                val_orcado = float(row[orcado_col]) if orcado_col is not None and pd.notna(row[orcado_col]) else 0.0
                val_realizado = float(row[realizado_col]) if realizado_col is not None and pd.notna(row[realizado_col]) else 0.0
                

                if val_orcado != 0 or val_realizado != 0:
                    raw_data.append({
                        "cc_raw": cc_name_raw,
                        "cc_nome": cc_name,
                        "cc_id_sienge": cc_id_sienge,  # código numérico único do CC no Sienge
                        "conta_raw": f"{conta_codigo} - {conta_desc}",
                        "conta_nome": conta_desc,
                        "mes": mes,
                        "ano": ano,
                        "orcado": val_orcado,
                        "realizado": val_realizado
                    })

    return raw_data

def resolver_mapeamentos(db: Session, raw_data: List[Dict[str, Any]]) -> bool:
    """
    Busca IDs reais no ERP ML para Centro de Custo e Plano Financeiro.
    PRIORIDADE: usa o código Sienge (id_sienge) como chave primária de mapeamento,
    que é único por definição. Nome só é usado como fallback de último recurso.
    Cria MigrationMapping PENDING se não achar.
    Retorna True se todos foram mapeados, False se houver pendências.
    """
    pendencias = False
    
    # Cache De-Para existente (keyed por código Sienge quando disponível, senão por nome)
    cache_cc = {m.nome_origem: m for m in db.query(MigrationMapping).filter_by(tipo="CENTRO_CUSTO").all()}
    cache_fp = {m.nome_origem: m for m in db.query(MigrationMapping).filter_by(tipo="PLANO_FINANCEIRO").all()}
    
    # Índice de CostCenters por id_sienge (chave primária) e por nome (fallback)
    db_cc_by_sienge = {str(c.id_sienge): c for c in db.query(CostCenter).all() if c.id_sienge}
    db_cc_by_nome = {c.nome.lower(): c for c in db.query(CostCenter).all()}
    db_fp = {f.name.lower(): f for f in db.query(FinancialPlan).all()}
    
    novos_mappings = []

    for row in raw_data:
        cc_id_sienge = row.get("cc_id_sienge")  # código numérico Sienge (ex: "13300")
        cc_nome = row["cc_nome"]
        conta_nome = row["conta_nome"]
        
        # 1. Resolver Centro de Custo — usando código Sienge como chave primária
        # A chave no cache é o código Sienge ("13300") quando disponível, senão o nome
        cc_cache_key = cc_id_sienge if cc_id_sienge else cc_nome
        mapping_cc = cache_cc.get(cc_cache_key)
        
        if not mapping_cc:
            cc = None
            # PRIORIDADE 1: busca pelo código Sienge único
            if cc_id_sienge:
                cc = db_cc_by_sienge.get(cc_id_sienge)
            # PRIORIDADE 2: fallback por nome (somente se não tem código)
            if not cc:
                cc = db_cc_by_nome.get(cc_nome.lower())
            
            if cc:
                mapping_cc = MigrationMapping(
                    tipo="CENTRO_CUSTO",
                    nome_origem=cc_cache_key,
                    id_destino=cc.id,
                    status="MAPPED"
                )
            else:
                mapping_cc = MigrationMapping(
                    tipo="CENTRO_CUSTO",
                    nome_origem=cc_cache_key,
                    status="PENDING"
                )
                pendencias = True
                logger.warning(f"CC não encontrado: código={cc_id_sienge}, nome={cc_nome}")
            novos_mappings.append(mapping_cc)
            cache_cc[cc_cache_key] = mapping_cc
        elif getattr(mapping_cc, "status", "PENDING") == "PENDING":
            pendencias = True
            
        row["cc_id"] = getattr(mapping_cc, "id_destino", None)
        
        # 2. Resolver Plano Financeiro (Conta) — nome é suficiente pois contas são únicas por nome
        mapping_fp = cache_fp.get(conta_nome)
        if not mapping_fp:
            fp = db_fp.get(conta_nome.lower())
            if fp:
                mapping_fp = MigrationMapping(tipo="PLANO_FINANCEIRO", nome_origem=conta_nome, id_destino=fp.id, status="MAPPED")
            else:
                mapping_fp = MigrationMapping(tipo="PLANO_FINANCEIRO", nome_origem=conta_nome, status="PENDING")
                pendencias = True
            novos_mappings.append(mapping_fp)
            cache_fp[conta_nome] = mapping_fp
        elif getattr(mapping_fp, "status", "PENDING") == "PENDING":
            pendencias = True
            
        row["fp_id"] = getattr(mapping_fp, "id_destino", None)

    if novos_mappings:
        db.add_all(novos_mappings)
        db.commit()

    return not pendencias

from app.models.orcamento import Orcamento, OrcamentoItem
from app.models.user import User

def efetivar_carga(db: Session, raw_data: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Grava os dados mapeados nas tabelas de Orçado e Realizado.
    Utiliza uma abordagem idempotente para evitar duplicação.
    """
    admin_user = db.query(User).filter(User.role.in_(["Administrador", "Integracao"])).first()
    admin_id = admin_user.id if admin_user else 1

    # Para Orçamento, garantimos que existe um Orcamento "Carga Inicial Sienge 2026" para Despesas e Receitas
    budget_despesas = db.query(Orcamento).filter_by(descricao="Carga Inicial Sienge 2026", tipo="DESPESAS").first()
    if not budget_despesas:
        budget_despesas = Orcamento(
            descricao="Carga Inicial Sienge 2026",
            ano=2026,
            tipo="DESPESAS",
            status="Aprovado",
            versao_numero=1,
            usuario_criador_id=admin_id
        )
        db.add(budget_despesas)

    budget_receitas = db.query(Orcamento).filter_by(descricao="Carga Inicial Sienge 2026", tipo="RECEITAS").first()
    if not budget_receitas:
        budget_receitas = Orcamento(
            descricao="Carga Inicial Sienge 2026",
            ano=2026,
            tipo="RECEITAS",
            status="Aprovado",
            versao_numero=1,
            usuario_criador_id=admin_id
        )
        db.add(budget_receitas)
        
    db.commit()
    db.refresh(budget_despesas)
    db.refresh(budget_receitas)

    # Coleta de transações e itens a serem persistidos
    novos_realizados = []
    
    # Limpeza simples para idempotência: remover carga anterior via source_id
    db.query(OrcamentoItem).filter(OrcamentoItem.orcamento_id.in_([budget_despesas.id, budget_receitas.id])).delete(synchronize_session=False)
    db.query(ActualTransaction).filter(ActualTransaction.source_id.like("SP-MIG-%")).delete(synchronize_session=False)
    db.commit()

    # Descobrir mapeamento fp_id -> db_id para separar receitas e despesas
    fps = db.query(FinancialPlan).all()
    fp_map = {fp.id: fp.db_id for fp in fps}

    # Dicionário para agregar OrcamentoItem por (cc_id, fp_id)
    orcamentos_dict = {}

    for row in raw_data:
        cc_id = row["cc_id"]
        fp_id = row["fp_id"]
        if not cc_id or not fp_id: continue
        
        # Orçado
        if row["orcado"] != 0:
            key = (cc_id, fp_id)
            if key not in orcamentos_dict:
                orcamentos_dict[key] = {
                    "jan": 0, "fev": 0, "mar": 0, "abr": 0, "mai": 0, "jun": 0,
                    "jul": 0, "ago": 0, "set": 0, "out": 0, "nov": 0, "dez": 0
                }
            
            mes_map = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
                       7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}
            mes_nome = mes_map.get(row["mes"])
            if mes_nome:
                orcamentos_dict[key][mes_nome] += row["orcado"]
            
        # Realizado
        if row["realizado"] != 0:
            dt = datetime(row["ano"], row["mes"], 1)
            hash_id = f"SP-MIG-CC{cc_id}-FP{fp_id}-{dt.strftime('%Y%m')}"
            
            fp_db_id = str(fp_map.get(fp_id, ""))
            # Se a conta contábil começa com 1, é Receita (INCOME). Caso contrário é Despesa (OUTCOME).
            # Valores no Sienge geralmente vêm positivos para ambos os casos nesse relatório.
            t_type = "INCOME" if fp_db_id.startswith("1") else "OUTCOME"
            
            tx = ActualTransaction(
                cost_center_id=cc_id,
                source_id=hash_id,
                transaction_type=t_type, 
                transaction_date=dt,
                value=row["realizado"],
                category=row["conta_nome"]
            )
            novos_realizados.append(tx)
            
    # Criar OrcamentoItem agregados
    novos_orcamentos = []
    for (cc_id, fp_id), vals in orcamentos_dict.items():
        total = sum(vals.values())
        if total != 0:
            fp_db_id = str(fp_map.get(fp_id, ""))
            target_budget_id = budget_receitas.id if fp_db_id.startswith("1") else budget_despesas.id
            item = OrcamentoItem(
                orcamento_id=target_budget_id,
                produto_id=cc_id,
                plano_financeiro_id=fp_id,
                jan=vals.get("jan") or 0.0,
                fev=vals.get("fev") or 0.0,
                mar=vals.get("mar") or 0.0,
                abr=vals.get("abr") or 0.0,
                mai=vals.get("mai") or 0.0,
                jun=vals.get("jun") or 0.0,
                jul=vals.get("jul") or 0.0,
                ago=vals.get("ago") or 0.0,
                set=vals.get("set") or 0.0,
                out=vals.get("out") or 0.0,
                nov=vals.get("nov") or 0.0,
                dez=vals.get("dez") or 0.0,
                total_anual=total,
                observacao="Carga Inicial SharePoint"
            )
            novos_orcamentos.append(item)

    if novos_orcamentos:
        db.add_all(novos_orcamentos)
    if novos_realizados:
        db.add_all(novos_realizados)

    db.commit()

    from app.services.sharepoint_departamento import fix_orcamentos_sharepoint_sem_departamento

    fix_orcamentos_sharepoint_sem_departamento(db)

    return len(novos_orcamentos), len(novos_realizados)


def run_carga_inicial(db: Session) -> None:
    """
    Função principal executada em background.
    """
    if not os.path.exists(SHAREPOINT_BASE_DIR):
        logger.error("Diretório SharePoint não encontrado!")
        return

    all_raw_data = []
    
    # Procurar planilhas em subpastas recursivamente
    search_pattern = os.path.join(SHAREPOINT_BASE_DIR, "**", "*.xlsx")
    files = glob.glob(search_pattern, recursive=True)
    
    if not files:
        logger.warning("Nenhum arquivo Excel encontrado para carga inicial.")
        return

    # Pular se não houve alteração
    max_mtime = max(os.path.getmtime(f) for f in files)
    sync_state = get_sync_state()
    if sync_state.get("carga_inicial") == max_mtime:
        logger.info("Nenhuma alteração nos arquivos da carga inicial. Pulando importação para economizar tempo.")
        return
    
    for f in files:
        if "~$" in f: continue # Ignora arquivos temporários do excel
        logger.info(f"Lendo: {f}")
        try:
            data = parse_sienge_report(f, db)
            all_raw_data.extend(data)
        except Exception as e:
            logger.error(f"Erro ao ler {f}: {e}")
            
    if not all_raw_data:
        logger.warning("Nenhum dado encontrado para carga.")
        return
        
    logger.info(f"Total de linhas analíticas extraídas: {len(all_raw_data)}")
    
    # Valida e cria mapeamentos
    tudo_mapeado = resolver_mapeamentos(db, all_raw_data)
    
    if tudo_mapeado:
        logger.info("Todos os mapeamentos resolvidos! Efetivando carga...")
        orc, real = efetivar_carga(db, all_raw_data)
        logger.info(f"Carga finalizada com sucesso! {orc} orçamentos e {real} realizados inseridos.")
        
        # Atualiza o estado
        sync_state["carga_inicial"] = max_mtime
        save_sync_state(sync_state)
    else:
        logger.warning("Existem pendências de mapeamento (De-Para). Acesse o frontend para resolver.")
