import os
import math
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from app.models.migration import MigrationMapping
from app.models.cost_center import CostCenter
from app.models.payment_plan import PaymentPlan
from app.models.orcamento import Orcamento, OrcamentoVendaItem
from app.models.forecast import Forecast, ForecastVendaItem
from app.models.user import User
from app.models.departamento import Departamento
from app.models.financial_plan import FinancialPlan
from app.services.budget_shared import canonical_versao_vendas_planilha

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def resolver_mapeamentos_vendas(db: Session, raw_data: List[Dict[str, Any]]) -> bool:
    """Resolve o CostCenter via MigrationMapping."""
    pendencias = False
    cache_cc = {m.nome_origem: m for m in db.query(MigrationMapping).filter_by(tipo="CENTRO_CUSTO").all()}
    db_cc = {c.nome.lower(): c for c in db.query(CostCenter).all()}
    
    novos_mappings = []

    for row in raw_data:
        cc_nome = row["Empreendimento"]
        
        mapping_cc = cache_cc.get(cc_nome)
        if not mapping_cc:
            # Tenta busca exata em CostCenter
            cc = db_cc.get(cc_nome.lower())
            if cc:
                mapping_cc = MigrationMapping(tipo="CENTRO_CUSTO", nome_origem=cc_nome, id_destino=cc.id, status="MAPPED")
            else:
                # Tenta parsear o ID sienge caso venha como "13200 - NOME"
                sienge_id = cc_nome.split(" - ")[0].strip() if " - " in cc_nome else ""
                cc_by_id = db.query(CostCenter).filter(CostCenter.id_sienge == sienge_id).first()
                if cc_by_id:
                    mapping_cc = MigrationMapping(tipo="CENTRO_CUSTO", nome_origem=cc_nome, id_destino=cc_by_id.id, status="MAPPED")
                else:
                    mapping_cc = MigrationMapping(tipo="CENTRO_CUSTO", nome_origem=cc_nome, status="PENDING")
                    pendencias = True
            
            novos_mappings.append(mapping_cc)
            cache_cc[cc_nome] = mapping_cc
        elif getattr(mapping_cc, "status", "PENDING") == "PENDING":
            pendencias = True
            
        row["cc_id"] = getattr(mapping_cc, "id_destino", None)

    if novos_mappings:
        db.add_all(novos_mappings)
        db.commit()

    return not pendencias


def processar_planilha_vendas(db: Session, filepath: str, ano_filtro: int = 2026):
    logger.info(f"Iniciando leitura da planilha de Vendas: {filepath}")
    
    try:
        df = pd.read_excel(filepath, sheet_name="Orcamento", header=1)
    except PermissionError:
        import tempfile
        import shutil
        logger.warning("Arquivo travado. Criando cópia temporária...")
        temp_path = os.path.join(tempfile.gettempdir(), "copy_vendas_temp.xlsx")
        shutil.copy2(filepath, temp_path)
        df = pd.read_excel(temp_path, sheet_name="Orcamento", header=1)

    df_filtrado = df[df['Ano'] == ano_filtro].copy()
    if df_filtrado.empty:
        logger.warning(f"Nenhum dado encontrado para o ano {ano_filtro}.")
        return
    
    df_filtrado = df_filtrado.where(pd.notnull(df_filtrado), None)
    raw_data = df_filtrado.to_dict(orient='records')
    
    logger.info(f"Linhas encontradas para {ano_filtro}: {len(raw_data)}")
    
    tudo_mapeado = resolver_mapeamentos_vendas(db, raw_data)
    if not tudo_mapeado:
        logger.error("Pendências de mapeamento (De-Para) de Centro de Custo! Vá no painel e mapeie os PENDING.")
        return

    plano_180x = db.query(PaymentPlan).filter(PaymentPlan.nome == "180x").first()
    if not plano_180x:
        logger.error("Plano de Pagamento '180x' não encontrado no banco.")
        return
        
    admin_user = db.query(User).filter(User.role.in_(["Administrador", "Integracao"])).first()
    admin_id = admin_user.id if admin_user else 1

    budgets_cache = {}
    
    def get_or_create_budget(versao: str):
        versao, kind = canonical_versao_vendas_planilha(versao)
        if versao in budgets_cache:
            return budgets_cache[versao]

        if kind == "orcamento":
            aliases = [versao, "1ª versão", "1º versão", "Orçamento", f"Orçamento Vendas {ano_filtro}"]
            b = None
            for alias in aliases:
                b = (
                    db.query(Orcamento)
                    .filter_by(ano=ano_filtro, tipo="VENDAS", descricao=alias)
                    .first()
                )
                if b:
                    break
            if not b:
                b = Orcamento(descricao=versao, ano=ano_filtro, tipo="VENDAS", status="Aprovado", versao_numero=1, usuario_criador_id=admin_id)
                db.add(b)
                db.commit()
                db.refresh(b)
            budgets_cache[versao] = {"obj": b, "type": "orcamento"}
        else:
            b = db.query(Forecast).filter_by(descricao=versao, ano=ano_filtro, tipo="VENDAS").first()
            if not b:
                rolling = None
                if "+" in versao:
                    try:
                        rolling = int(versao.split("-")[-1].split("+")[0].strip())
                    except Exception:
                        rolling = 1
                b = Forecast(
                    descricao=versao,
                    ano=ano_filtro,
                    tipo="VENDAS",
                    status="Aprovado",
                    versao_numero=1,
                    mes_corte=(rolling or 0) + 1,
                    usuario_criador_id=admin_id,
                )
                db.add(b)
                db.commit()
                db.refresh(b)
            budgets_cache[versao] = {"obj": b, "type": "forecast"}

        return budgets_cache[versao]

    orcamentos_ano = db.query(Orcamento.id).filter_by(ano=ano_filtro, tipo="VENDAS").all()
    if orcamentos_ano:
        o_ids = [r[0] for r in orcamentos_ano]
        db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id.in_(o_ids)).delete(synchronize_session=False)

    forecasts_ano = db.query(Forecast.id).filter_by(ano=ano_filtro, tipo="VENDAS").all()
    if forecasts_ano:
        f_ids = [r[0] for r in forecasts_ano]
        db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id.in_(f_ids)).delete(synchronize_session=False)
        
    db.commit()

    orcamento_items = []
    forecast_items = []

    for row in raw_data:
        cc_id = row.get("cc_id")
        if not cc_id: continue
        
        # Access dict via "M\ufffd\ufffds" (which was seen as 'Ms') or try both
        mes = None
        for k in list(row.keys()):
            if "m" in str(k).lower() and "s" in str(k).lower() and len(str(k)) <= 4:
                mes = row.get(k)
                break
        
        try:
            mes = int(mes)
        except:
            continue
            
        if mes < 1 or mes > 12: continue

        versao = str(row.get("Versao orcamento", "1ª versão")).strip()
        qtd_vendas = row.get("Quantidade Vendas")
        qtd_vendas = float(qtd_vendas) if qtd_vendas is not None else 0.0
        
        qtd_distratos = row.get("Quantidade Distratos")
        qtd_distratos = float(qtd_distratos) if qtd_distratos is not None else 0.0
        
        vgv = row.get("VGV")
        vgv = float(vgv) if vgv is not None else 0.0
        
        origem_venda = row.get("Origem Venda")
        if origem_venda is None or pd.isna(origem_venda):
            origem_venda = None
        else:
            origem_venda = str(origem_venda).strip()
            
        tipo_venda = str(row.get("Tipo de Venda", "")).strip()

        budget_info = get_or_create_budget(versao)
        
        # Calcula Ticket Médio base
        ticket_medio = 0.0
        if qtd_vendas > 0 and vgv != 0:
            ticket_medio = abs(vgv) / qtd_vendas
        elif qtd_distratos > 0 and qtd_vendas == 0 and vgv != 0:
            ticket_medio = abs(vgv) / qtd_distratos
            
        # 1) Lançamento de Vendas
        if qtd_vendas > 0:
            vgv_venda = qtd_vendas * ticket_medio
            item_data = dict(
                produto_id=cc_id, plano_venda_id=plano_180x.id, mes=mes, ano=ano_filtro,
                numero_vendas=int(qtd_vendas), vgv=vgv_venda, ticket_medio=ticket_medio,
                origem_venda=origem_venda, observacao=f"{tipo_venda} (Venda)".strip()
            )
            if budget_info["type"] == "orcamento":
                orcamento_items.append(OrcamentoVendaItem(orcamento_id=budget_info["obj"].id, **item_data))
            else:
                forecast_items.append(ForecastVendaItem(forecast_id=budget_info["obj"].id, **item_data))

        # 2) Lançamento de Distratos
        if qtd_distratos > 0:
            vgv_distrato = - (qtd_distratos * ticket_medio)
            item_data = dict(
                produto_id=cc_id, plano_venda_id=plano_180x.id, mes=mes, ano=ano_filtro,
                numero_vendas=-int(qtd_distratos), vgv=vgv_distrato, ticket_medio=ticket_medio,
                origem_venda=origem_venda, observacao=f"{tipo_venda} (Distrato)".strip()
            )
            if budget_info["type"] == "orcamento":
                orcamento_items.append(OrcamentoVendaItem(orcamento_id=budget_info["obj"].id, **item_data))
            else:
                forecast_items.append(ForecastVendaItem(forecast_id=budget_info["obj"].id, **item_data))
                
        # 3) Lançamento vazio (para preenchimento manual) se ambos forem zero
        if qtd_vendas == 0 and qtd_distratos == 0:
            item_data = dict(
                produto_id=cc_id, plano_venda_id=plano_180x.id, mes=mes, ano=ano_filtro,
                numero_vendas=0, vgv=0.0, ticket_medio=0.0,
                origem_venda=origem_venda, observacao=tipo_venda
            )
            if budget_info["type"] == "orcamento":
                orcamento_items.append(OrcamentoVendaItem(orcamento_id=budget_info["obj"].id, **item_data))
            else:
                forecast_items.append(ForecastVendaItem(forecast_id=budget_info["obj"].id, **item_data))
            
    if orcamento_items:
        db.add_all(orcamento_items)
    if forecast_items:
        db.add_all(forecast_items)
        
    db.commit()
    logger.info(f"Importação concluída! Orçamentos: {len(orcamento_items)}, Forecasts: {len(forecast_items)}")

if __name__ == "__main__":
    from app.db.database import SessionLocal
    db = SessionLocal()
    path = r"C:\Users\Usuario\MOURA LEITE DESENVOLVIMENTO & URBANIZACAO LTDA\Banco de Dados - Documentos\Orçamento - Vendas\Orcamento de vendas.xlsx"
    processar_planilha_vendas(db, path, 2026)
    db.close()
