import re
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
from app.models.orcamento import Orcamento
from app.models.forecast import Forecast, ForecastItem
from app.models.departamento import Departamento
import app.main  # Para inicializar todos os mappers do SQLAlchemy
import json

STATE_FILE = os.path.join(os.path.dirname(__file__), "sync_state.json")

def get_sync_state() -> Dict[str, float]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sync_state(state: Dict[str, float]) -> None:
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Erro ao salvar sync_state: {e}")

FORECAST_BASE_DIR = r"C:\Users\Usuario\MOURA LEITE DESENVOLVIMENTO & URBANIZACAO LTDA\Banco de Dados - Documentos\Sienge - 2653 - Comparativo Orçamento Empresarial X Realizado Agrupado - Forecast\2026"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def parse_sienge_forecast_report(filepath: str, db: Session) -> List[Dict[str, Any]]:
    """
    Lê uma planilha Sienge, extrai o Centro de Custo, percorre os meses
    e gera as linhas estritamente de Orçado.
    Aplica validação estrutural - se as colunas Orçado não existirem, lança exceção.
    """
    try:
        df = pd.read_excel(filepath, header=None)
    except Exception as e:
        raise Exception(f"Falha ao abrir arquivo Excel: {e}")
        
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
        meses_encontrados = []
        for i, val in enumerate(row):
            if pd.notna(val):
                val_str = str(val).strip().lower()
                if "/" in val_str:
                    m_str = val_str.split("/")[0]
                    if m_str in meses_map:
                        y_str = val_str.split("/")[1]
                        meses_encontrados.append((meses_map[m_str], int(y_str), i))
                        
        if meses_encontrados:
            meses_cols = {}
            if idx + 1 < len(df):
                for m, y, i in meses_encontrados:
                    or_col = None
                    # Procura 'orçado' nas colunas adjacentes (devido a mesclagem do Excel)
                    for j in range(max(0, i-2), min(len(df.columns), i+3)):
                        val_11 = str(df.iloc[idx+1, j]).strip().lower()
                        if "orçado" in val_11 or "orcado" in val_11:
                            or_col = j
                            break
                    meses_cols[(m, y)] = {"orçado": or_col}
            continue # Pula a linha de meses

        # 3. Lendo dados analíticos
        tipo = str(row[4]).strip() if pd.notna(row[4]) else ""
        if tipo == "R":
            conta_codigo = str(row[0]).strip()
            conta_desc = str(row[1]).strip()
            
            for mes_ano, cols in meses_cols.items():
                mes, ano = mes_ano
                orcado_col = cols.get("orçado")
                
                # Validação estrutural básica: se achou mês mas não achou coluna orçado
                if orcado_col is None:
                    continue # Pode não ter mês completo, mas se achou a string do mes, deveria ter a coluna embaixo
                    
                val_orcado = float(row[orcado_col]) if orcado_col is not None and pd.notna(row[orcado_col]) else 0.0
                
                if val_orcado != 0:
                    raw_data.append({
                        "cc_raw": cc_name_raw,
                        "cc_nome": cc_name,
                        "cc_id_sienge": cc_id_sienge,
                        "conta_raw": f"{conta_codigo} - {conta_desc}",
                        "conta_nome": conta_desc,
                        "mes": mes,
                        "ano": ano,
                        "orcado": val_orcado
                    })

    # Validação Final de Arquivo
    if not meses_cols:
        raise Exception(f"Validação estrutural falhou: Arquivo '{filepath}' não contém a tabela padrão de meses e colunas 'Orçado'.")
        
    for mes_ano, cols in meses_cols.items():
        if cols.get("orçado") is None:
             raise Exception(f"Validação estrutural falhou: Arquivo '{filepath}' possui o mês {mes_ano[0]}/{mes_ano[1]}, mas não possui a subcoluna 'Orçado'.")

    return raw_data

def resolver_mapeamentos(db: Session, raw_data: List[Dict[str, Any]]) -> bool:
    """
    Busca IDs reais no ERP ML para Centro de Custo e Plano Financeiro.
    PRIORIDADE: usa o código Sienge (id_sienge) como chave primária de mapeamento.
    Retorna True se todos foram mapeados, False se houver pendências.
    """
    pendencias = False
    
    cache_cc = {m.nome_origem: m for m in db.query(MigrationMapping).filter_by(tipo="CENTRO_CUSTO").all()}
    cache_fp = {m.nome_origem: m for m in db.query(MigrationMapping).filter_by(tipo="PLANO_FINANCEIRO").all()}
    
    db_cc_by_sienge = {str(c.id_sienge): c for c in db.query(CostCenter).all() if c.id_sienge}
    db_cc_by_nome = {c.nome.lower(): c for c in db.query(CostCenter).all()}
    db_fp = {f.name.lower(): f for f in db.query(FinancialPlan).all()}
    
    novos_mappings = []

    for row in raw_data:
        cc_id_sienge = row.get("cc_id_sienge")
        cc_nome = row["cc_nome"]
        conta_nome = row["conta_nome"]
        
        # 1. Resolver Centro de Custo
        cc_cache_key = cc_id_sienge if cc_id_sienge else cc_nome
        mapping_cc = cache_cc.get(cc_cache_key)
        
        if not mapping_cc:
            cc = None
            if cc_id_sienge:
                cc = db_cc_by_sienge.get(cc_id_sienge)
            if not cc:
                cc = db_cc_by_nome.get(cc_nome.lower())
                
            if cc:
                mapping_cc = MigrationMapping(tipo="CENTRO_CUSTO", nome_origem=cc_cache_key, id_destino=cc.id, status="MAPPED")
            else:
                mapping_cc = MigrationMapping(tipo="CENTRO_CUSTO", nome_origem=cc_cache_key, status="PENDING")
                pendencias = True
                logger.warning(f"CC não encontrado no Forecast: código={cc_id_sienge}, nome={cc_nome}")
            novos_mappings.append(mapping_cc)
            cache_cc[cc_cache_key] = mapping_cc
        elif getattr(mapping_cc, "status", "PENDING") == "PENDING":
            pendencias = True
            
        row["cc_id"] = getattr(mapping_cc, "id_destino", None)
        
        # 2. Resolver Plano Financeiro (Conta)
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

def pre_process_departments(db: Session) -> int:
    """
    Garante o departamento Corporativo (residual) e ajusta o Orcamento inicial.
    Retorna o ID do departamento residual.
    """
    from app.services.corporativo import ensure_corporativo_departamento

    consolidado = ensure_corporativo_departamento(db)
        
    # Correção do débito técnico da carga 2026 original
    orcamentos = db.query(Orcamento).filter_by(descricao="Carga Inicial Sienge 2026").all()
    for o in orcamentos:
        if o.departamento_id is None:
            from app.models.auditoria import Auditoria
            
            auditoria = Auditoria(
                evento="Alteracao",
                tabela_afetada="orcamentos",
                registro_id=o.id,
                campo="departamento_id",
                valor_anterior="null",
                novo_valor=str(consolidado.id),
                usuario_id=None,
                motivo="Correção retroativa (DEC-016) via Carga de Forecast Histórico"
            )
            db.add(auditoria)
            
            o.departamento_id = consolidado.id
            logger.info(f"Corrigindo Orçamento Base 2026 ID {o.id} ({o.tipo}) para apontar para o departamento Consolidado.")
    db.commit()
    return consolidado.id

def obter_orcamentos_base(db: Session, ano: int) -> Tuple[int, int]:
    """
    Retorna (id_orcamento_despesas, id_orcamento_vendas) para a versão 1 do ano fornecido.
    Se não encontrar, lança exceção, prevenindo IDs mágicos no código.
    """
    orc_desp = db.query(Orcamento).filter_by(ano=ano, tipo="DESPESAS", versao_numero=1).first()
    orc_vend = db.query(Orcamento).filter_by(ano=ano, tipo="VENDAS", versao_numero=1).first()
    
    if not orc_desp or not orc_vend:
        raise Exception(f"Orçamentos base (V1) do ano {ano} não encontrados! O sistema exige a carga inicial antes do Forecast.")
        
    return orc_desp.id, orc_vend.id

def efetivar_carga_forecast(db: Session, raw_data: List[Dict[str, Any]], mes_corte: int, desc_forecast: str, dept_id: int) -> int:
    """
    Grava os dados mapeados na tabela de Forecast.
    """
    base_despesas_id, base_vendas_id = obter_orcamentos_base(db, 2026)

    # 1. Obter ou criar Forecast para Despesas
    forecasts_desp_antigos = db.query(Forecast).filter_by(descricao=desc_forecast, tipo="DESPESAS").all()
    for f_antigo in forecasts_desp_antigos:
        db.delete(f_antigo)
    
    if forecasts_desp_antigos:
        db.commit()
        
    forecast_desp = Forecast(
        descricao=desc_forecast,
        ano=2026,
        tipo="DESPESAS",
        mes_corte=mes_corte,
        status="Importado Sienge",
        departamento_id=dept_id,
        versao_base_orcamento_id=base_despesas_id
    )
    db.add(forecast_desp)

    # 2. Obter ou criar Forecast para Receitas
    forecasts_rec_antigos = db.query(Forecast).filter_by(descricao=desc_forecast, tipo="RECEITAS").all()
    for f_antigo in forecasts_rec_antigos:
        db.delete(f_antigo)
        
    if forecasts_rec_antigos:
        db.commit()
        
    forecast_rec = Forecast(
        descricao=desc_forecast,
        ano=2026,
        tipo="RECEITAS",
        mes_corte=mes_corte,
        status="Importado Sienge",
        departamento_id=dept_id,
        versao_base_orcamento_id=base_vendas_id
    )
    db.add(forecast_rec)
    db.commit()
    db.refresh(forecast_desp)
    db.refresh(forecast_rec)

    # Dicionário para agregar ForecastItem por (cc_id, fp_id)
    forecasts_dict = {}

    for row in raw_data:
        cc_id = row["cc_id"]
        fp_id = row["fp_id"]
        if not cc_id or not fp_id: continue
        
        # DEC-018: Filtra apenas os valores do ano correto (2026) ignorando anos passados
        if row.get("ano") != 2026:
            continue
            
        if row["orcado"] != 0:
            key = (cc_id, fp_id)
            if key not in forecasts_dict:
                forecasts_dict[key] = {
                    "jan": 0, "fev": 0, "mar": 0, "abr": 0, "mai": 0, "jun": 0,
                    "jul": 0, "ago": 0, "set": 0, "out": 0, "nov": 0, "dez": 0
                }
            
            mes_map = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
                       7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}
            mes_nome = mes_map.get(row["mes"])
            if mes_nome:
                forecasts_dict[key][mes_nome] += row["orcado"]
            
    # Descobrir mapeamento fp_id -> db_id para separar receitas e despesas
    fps = db.query(FinancialPlan).all()
    fp_map = {fp.id: fp.db_id for fp in fps}

    # Criar ForecastItem agregados
    novos_itens = []
    for (cc_id, fp_id), vals in forecasts_dict.items():
        total = sum(vals.values())
        if total != 0:
            fp_db_id = str(fp_map.get(fp_id, ""))
            target_forecast_id = forecast_rec.id if fp_db_id.startswith("1") else forecast_desp.id
            item = ForecastItem(
                forecast_id=target_forecast_id,
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
                observacao="Importado do Sienge (SharePoint)"
            )
            novos_itens.append(item)

    if novos_itens:
        db.add_all(novos_itens)
        
    db.commit()
    return len(novos_itens)


def run_carga_forecast(db: Session) -> None:
    """
    Função principal executada em background.
    """
    if not os.path.exists(FORECAST_BASE_DIR):
        logger.error("Diretório SharePoint Base não encontrado!")
        return

    # Passo 1: Prepara o departamento consolidado
    dept_id = pre_process_departments(db)

    # Identificar todas as pastas "Forecast - X+Y"
    subdirs = [f.path for f in os.scandir(FORECAST_BASE_DIR) if f.is_dir() and "Forecast -" in f.name]
    
    # Sort folders by name logically if possible
    subdirs.sort()

    for folder in subdirs:
        folder_name = os.path.basename(folder)
        logger.info(f"\n--- Processando Pasta: {folder_name} ---")
        
        # O mês de corte é o número X em "Forecast - X+Y" + 1 (pois X são meses realizados)
        # Exemplo: "Forecast - 7+5" -> 7 meses realizados, logo corte é no mês 8.
        try:
            parts = folder_name.split("-")[1].strip().split("+")
            realizados = int(parts[0])
            mes_corte = realizados + 1
        except Exception:
            logger.warning(f"Não foi possível extrair o mês de corte do nome {folder_name}, pulando...")
            continue
            
        desc_forecast = folder_name
        if '+' in desc_forecast:
            parts = re.findall(r'\d+\+\d+', desc_forecast)
            if parts:
                desc_forecast = f'Forecast - {parts[0]}'
        all_raw_data = []
        
        search_pattern = os.path.join(folder, "**", "*.xlsx")
        files = glob.glob(search_pattern, recursive=True)
        
        if not files:
            logger.warning("Nenhum arquivo Excel encontrado nesta pasta.")
            continue
            
        # Pula se não houve alteração
        max_mtime = max(os.path.getmtime(f) for f in files)
        sync_state = get_sync_state()
        if sync_state.get(folder_name) == max_mtime:
            logger.info(f"Nenhuma alteração nos arquivos de {folder_name}. Pulando importação para economizar tempo.")
            continue

        folder_has_errors = False
        
        for f in files:
            if "~$" in f: continue
            logger.info(f"Lendo: {f}")
            try:
                data = parse_sienge_forecast_report(f, db)
                all_raw_data.extend(data)
            except Exception as e:
                logger.error(f"ERRO CRÍTICO em {f}: {e}")
                folder_has_errors = True
                break # Para imediatamente a leitura dessa pasta
                
        if folder_has_errors:
            logger.error(f"Carga da pasta '{folder_name}' CANCELADA devido a erro estrutural. Nenhum dado foi inserido.")
            continue
            
        if not all_raw_data:
            logger.warning("Nenhum dado financeiro encontrado nos arquivos.")
            continue
            
        # Valida e cria mapeamentos
        tudo_mapeado = resolver_mapeamentos(db, all_raw_data)
        
        if tudo_mapeado:
            logger.info(f"Todos os mapeamentos resolvidos para {folder_name}! Efetivando carga no banco...")
            qtd = efetivar_carga_forecast(db, all_raw_data, mes_corte, desc_forecast, dept_id)
            logger.info(f"SUCESSO: Forecast '{desc_forecast}' (Corte: Mês {mes_corte}) inserido com {qtd} itens.")
            
            # Atualiza o estado
            sync_state[folder_name] = max_mtime
            save_sync_state(sync_state)
        else:
            logger.warning(f"Existem pendências de mapeamento (De-Para) para {folder_name}. Carga cancelada. Resolva no app primeiro.")

if __name__ == "__main__":
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        run_carga_forecast(db)
    finally:
        db.close()
