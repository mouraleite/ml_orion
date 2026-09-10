import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.cost_center import CostCenter
from app.models.actual_transaction import ActualTransaction
from app.models.unit import Unit
from app.services.sienge_client import bulk_base_url, get_default_client

SIENGE_BASE_URL = bulk_base_url()
SIENGE_USER = settings.SIENGE_USER
SIENGE_PASS = settings.SIENGE_PASS

def get_auth_header():
    return get_default_client().auth_headers()


def outcome_contas_pagar_url(cost_center_sienge_id: str, start_date: str, end_date: str) -> str:
    """URL bulk de contas a pagar realizadas. withAuthorizations para gravar o name; filtro de tela não muda."""
    return (
        f"{SIENGE_BASE_URL}/outcome?startDate={start_date}&endDate={end_date}"
        f"&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01"
        f"&costCentersId={cost_center_sienge_id}&withAuthorizations=true&withBankMovements=true"
    )

def _fetch_paginated_bulk(url: str):
    """Auxiliar para buscar todas as páginas de um endpoint Bulk Data. Retorna em blocos."""
    yield from get_default_client().paginate_bulk(url)

def sync_all_sienge_data(db: Session, full_load: bool = False):
    """
    Roda o sincronismo de Vendas, Recebimentos e Pagamentos.
    Se full_load for True, busca desde 2001. Se False, busca os ltimos 3 dias por segurana.
    """
    if full_load:
        start_date = "2001-01-01"
        end_date = "2050-12-31"
    else:
        hoje = datetime.now()
        start_date = (hoje - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = hoje.strftime("%Y-%m-%d")

    # 1. Pega todos os Centros de Custo rastreados no Dashboard
    tracked = db.query(CostCenter).filter(CostCenter.track_in_dashboard == True).all()
    
    # 2. Extrai os prefixos (3 primeiros dígitos) dos CCs rastreados
    prefixes = set()
    for cc in tracked:
        if cc.id_sienge and len(cc.id_sienge) >= 3:
            prefixes.add(cc.id_sienge[:3])
            
    # 3. Busca todos os CCs que compartilham o mesmo prefixo (para incluir OBRAS, MLDU, etc.)
    if prefixes:
        from sqlalchemy import or_
        conditions = [CostCenter.id_sienge.like(f"{p}%") for p in prefixes]
        centros = db.query(CostCenter).filter(or_(*conditions)).all()
    else:
        centros = tracked
    
    for cc in centros:
        if not cc.id_sienge:
            continue
            
        sync_single_cc_sienge_data(db, cc, start_date, end_date)

    # Caixa e Bancos — uma passagem para todos os CCs do sync
    print("Sincronizando Caixa e Bancos (BM-*)...")
    sync_bank_movements_batch(db, start_date, end_date, cost_centers=centros)

    # Ao final do sincronismo de centros de custo, sincroniza também os colaboradores
    print("Sincronizando Colaboradores (Credores) do Sienge...")
    sync_sienge_colaboradores(db)
    
    # Gravar timestamp exato da sincronização para exibir no frontend
    try:
        from app.models.system_settings import SystemSettings
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        setting = db.query(SystemSettings).filter_by(key="last_api_sync").first()
        if setting:
            setting.value = {"timestamp": ts}
            setting.updated_at = datetime.now()
        else:
            setting = SystemSettings(key="last_api_sync", value={"timestamp": ts})
            db.add(setting)
        db.commit()
        print(f"[Sienge Sync] Timestamp de sincronização registrado: {ts}")
    except Exception as e:
        print(f"[Sienge Sync] Aviso: não foi possível gravar timestamp: {e}")


def sync_single_cc_sienge_data(db: Session, cc: CostCenter, start_date: str = "2001-01-01", end_date: str = "2050-12-31"):
    if not cc.id_sienge:
        return
        
    print(f"Sincronizando CC {cc.nome} (Sienge ID: {cc.id_sienge})...")
    
    # 0. SINCRONIZAR UNIDADES (Estoque)
    sync_units(db, cc)
    
    # 1. SINCRONIZAR VENDAS (Sales) - realizadas
    sync_sales(db, cc, start_date, end_date)
    
    # 2. SINCRONIZAR PAGAMENTOS REALIZADOS (Outcome - baixas bancárias)
    sync_outcomes(db, cc, start_date, end_date)
    
    # 3. SINCRONIZAR RECEBIMENTOS REALIZADOS (Income - baixas bancárias)
    sync_incomes(db, cc, start_date, end_date)

    # AFAC: SP lançará como despesa — espelha INC AFAC → OUT
    mirror_afac_income_as_outcome(db, cc, start_date, end_date)

    # BM-* é feito em lote em sync_all_sienge_data (sync_bank_movements_batch)
    
    # 4. SINCRONIZAR CONTAS A RECEBER EM ABERTO (previsão futura)
    sync_receivables_forecast(db, cc)
    
    # 5. SINCRONIZAR CONTAS A PAGAR EM ABERTO (previsão futura)
    sync_payables_forecast(db, cc)

def sync_units(db: Session, cc: CostCenter):
    """Sincroniza as unidades (Lotes/Apartamentos) do Centro de Custo"""
    from app.services.sienge_client import api_v1_base_url

    url = f"{api_v1_base_url()}/units?enterpriseId={cc.id_sienge}"
    client = get_default_client()

    existing = {
        u.id_sienge: u
        for u in db.query(Unit).filter_by(cost_center_id=cc.id).all()
    }

    try:
        for results in client.paginate_v1_pages(url):
            for item in results:
                sienge_id = item.get("id")
                if not sienge_id:
                    continue

                unit = existing.get(sienge_id)
                if not unit:
                    unit = Unit(
                        cost_center_id=cc.id,
                        id_sienge=sienge_id,
                    )
                    db.add(unit)
                    existing[sienge_id] = unit

                unit.name = item.get("name")
                unit.status = item.get("commercialStock")
                unit.private_area = float(item.get("privateArea", 0))
    except Exception as e:
        print(f"[Sienge Sync] Erro lendo Units: {e}")

    db.commit()

def sync_sales(db: Session, cc: CostCenter, start_date: str, end_date: str):
    """Sincroniza Contratos de Vendas e Distratos"""
    existing = {
        r.source_id: r 
        for r in db.query(ActualTransaction).filter_by(cost_center_id=cc.id, transaction_type="SALE").all()
    }
    
    # Buscamos as unidades locais para fazer o vínculo rápido
    local_units = {
        u.id_sienge: u.id
        for u in db.query(Unit.id_sienge, Unit.id).filter_by(cost_center_id=cc.id).all()
    }
    
    situations = ["SOLD", "CANCELED"]
    
    for situation_param in situations:
        url = f"{SIENGE_BASE_URL}/sales?enterpriseId={cc.id_sienge}&createdAfter={start_date}&createdBefore={end_date}&situation={situation_param}"
        
        for page in _fetch_paginated_bulk(url):
            for item in page:
                source_id = f"SALE-{item.get('id')}"
                situation = item.get("situation", situation_param)
                
                value = float(item.get("totalSellingValue", 0))
                
                # Tentar vincular à primeira unidade
                unit_id = None
                units = item.get("units", [])
                if units:
                    sienge_unit_id = units[0].get("id")
                    unit_id = local_units.get(sienge_unit_id)
                
                # Encontrar o maior número de parcelas no plano de pagamento
                installments_number = 0
                conditions = item.get("paymentConditions", [])
                for cond in conditions:
                    inst_num = cond.get("installmentsNumber")
                    if inst_num and isinstance(inst_num, int) and inst_num > installments_number:
                        installments_number = inst_num
                
                # 1. Registrar a Venda Original (sempre ocorre)
                venda_date_str = item.get("contractDate", item.get("issueDate"))
                if venda_date_str:
                    v_dt = datetime.strptime(venda_date_str[:10], "%Y-%m-%d").date()
                    
                    record = existing.get(source_id)
                    if not record:
                        record = ActualTransaction(
                            cost_center_id=cc.id,
                            source_id=source_id,
                            transaction_type="SALE"
                        )
                        db.add(record)
                        existing[source_id] = record
                        
                    record.transaction_date = v_dt
                    record.value = abs(value)
                    record.unit_id = unit_id
                    record.installments_number = installments_number
                    record.category = "VGV Vendido"
                
                # 2. Se for cancelado, registrar também o Distrato separadamente
                is_canceled = situation and situation.upper() in ["CANCELED", "CANCELADO", "DISTRATADO"]
                if is_canceled:
                    canc_source_id = f"{source_id}-CANC"
                    canc_date_str = item.get("cancellationDate")
                    if not canc_date_str:
                        canc_date_str = venda_date_str
                        
                    if canc_date_str:
                        c_dt = datetime.strptime(canc_date_str[:10], "%Y-%m-%d").date()
                        
                        canc_record = existing.get(canc_source_id)
                        if not canc_record:
                            canc_record = ActualTransaction(
                                cost_center_id=cc.id,
                                source_id=canc_source_id,
                                transaction_type="SALE"
                            )
                            db.add(canc_record)
                            existing[canc_source_id] = canc_record
                            
                        canc_record.transaction_date = c_dt
                        canc_record.value = -abs(value)
                        canc_record.unit_id = unit_id
                        canc_record.installments_number = installments_number
                        canc_record.category = "Distrato"
                    
    db.commit()

def sync_outcomes(db: Session, cc: CostCenter, start_date: str, end_date: str):
    """
    Contas a Pagar realizados: operationTypeId 1 e 8 + retenções bancárias.
    Valor = grossAmount × (financialCategoryRate / 100) por categoria do CC.
    """
    from datetime import datetime as dt_cls

    from app.services.sienge_outcome_parse import iter_outcome_realizado_lines

    url = outcome_contas_pagar_url(str(cc.id_sienge), start_date, end_date)

    try:
        start_d = dt_cls.strptime(start_date[:10], "%Y-%m-%d").date()
        end_d = dt_cls.strptime(end_date[:10], "%Y-%m-%d").date()
    except Exception:
        start_d = end_d = None

    # Remove Contas a Pagar (OUT-…-PMT-… / OUT-…-RET-…); preserva OUT-TARIFA-* e OUT-AFAC-*
    if start_d and end_d:
        from sqlalchemy import or_

        db.query(ActualTransaction).filter(
            ActualTransaction.cost_center_id == cc.id,
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,
            or_(
                ActualTransaction.source_id.like("OUT-%-PMT-%"),
                ActualTransaction.source_id.like("OUT-%-RET-%"),
            ),
            ActualTransaction.transaction_date >= start_d,
            ActualTransaction.transaction_date <= end_d,
        ).delete(synchronize_session=False)
        db.flush()

    existing = {
        r.source_id: r
        for r in db.query(ActualTransaction).filter_by(
            cost_center_id=cc.id, transaction_type="OUTCOME"
        ).all()
        if r.source_id
        and r.source_id.startswith("OUT-")
        and ("-PMT-" in r.source_id or "-RET-" in r.source_id)
    }

    for page in _fetch_paginated_bulk(url):
        for item in page:
            for line in iter_outcome_realizado_lines(item, str(cc.id_sienge)):
                date_str = line["payment_date"]
                try:
                    dtx = dt_cls.strptime(date_str[:10], "%Y-%m-%d").date()
                except Exception:
                    continue

                source_id = line["source_id"]
                record = existing.get(source_id)
                if not record:
                    record = ActualTransaction(
                        cost_center_id=cc.id,
                        source_id=source_id,
                        transaction_type="OUTCOME",
                    )
                    db.add(record)
                    existing[source_id] = record

                record.transaction_date = dtx
                record.value = line["value"]
                record.category = line["category_name"]
                record.bill_id = str(line["bill_id"]) if line["bill_id"] else None
                record.creditor_name = line["creditor_name"]
                record.document_name = line["document_name"]
                record.document_number = line["document_number"]
                record.authorization_name = line.get("authorization_name")
                record.is_forecast = False

    db.commit()


def mirror_afac_income_as_outcome(
    db: Session,
    cc: CostCenter,
    start_date: str,
    end_date: str,
):
    """
    SP trata AFAC como despesa/transferência nos dois CCs.
    Espelha INC-* categoria AFAC → OUT-AFAC-INC-* (OUTCOME) no mesmo CC/mês/valor.
    """
    from datetime import datetime as dt_cls

    try:
        start_d = dt_cls.strptime(start_date[:10], "%Y-%m-%d").date()
        end_d = dt_cls.strptime(end_date[:10], "%Y-%m-%d").date()
    except Exception:
        return

    db.query(ActualTransaction).filter(
        ActualTransaction.cost_center_id == cc.id,
        ActualTransaction.transaction_type == "OUTCOME",
        ActualTransaction.is_forecast == False,
        ActualTransaction.source_id.like("OUT-AFAC-INC-%"),
        ActualTransaction.transaction_date >= start_d,
        ActualTransaction.transaction_date <= end_d,
    ).delete(synchronize_session=False)
    db.flush()

    incomes = (
        db.query(ActualTransaction)
        .filter(
            ActualTransaction.cost_center_id == cc.id,
            ActualTransaction.transaction_type == "INCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like("INC-%"),
            ActualTransaction.transaction_date >= start_d,
            ActualTransaction.transaction_date <= end_d,
        )
        .all()
    )

    for inc in incomes:
        if str(inc.category or "").strip().upper() != "AFAC":
            continue
        if not inc.source_id or not inc.source_id.startswith("INC-"):
            continue
        mirror_id = "OUT-AFAC-" + inc.source_id
        record = ActualTransaction(
            cost_center_id=cc.id,
            source_id=mirror_id,
            transaction_type="OUTCOME",
            transaction_date=inc.transaction_date,
            value=float(inc.value or 0),
            category="AFAC",
            bill_id=inc.bill_id,
            creditor_name=inc.creditor_name,
            document_name=inc.document_name,
            document_number=inc.document_number,
            is_forecast=False,
        )
        db.add(record)

    db.commit()


def sync_bank_movements(db: Session, cc: CostCenter, start_date: str, end_date: str):
    """
    Caixa e Bancos realizados (receitas SP-MIG) para um CC.
    Preferir sync_bank_movements_batch ao resync de muitos CCs.
    """
    sync_bank_movements_batch(db, start_date, end_date, cost_centers=[cc])


def sync_bank_movements_batch(
    db: Session,
    start_date: str,
    end_date: str,
    *,
    cost_centers: Optional[list] = None,
):
    """
    Uma passagem na API bank-movement; grava BM-* por CC (rendimentos, descontos, reembolso)
    e OUT-BM-* para saídas que não passam pelo Contas a Pagar (IR sobre Aplicação).
    """
    from collections import defaultdict
    from datetime import datetime as dt_cls

    from app.services.sienge_bank_movement_parse import (
        build_inc_reembolso_keys,
        build_outcome_cobertura_keys,
        iter_bank_movement_despesa_lines,
        iter_bank_movement_receita_lines,
    )

    if cost_centers is None:
        cost_centers = db.query(CostCenter).filter(CostCenter.id_sienge.isnot(None)).all()

    cc_by_sienge = {str(c.id_sienge): c for c in cost_centers if c.id_sienge}
    if not cc_by_sienge:
        return

    url = f"{SIENGE_BASE_URL}/bank-movement?startDate={start_date}&endDate={end_date}"

    try:
        start_d = dt_cls.strptime(start_date[:10], "%Y-%m-%d").date()
        end_d = dt_cls.strptime(end_date[:10], "%Y-%m-%d").date()
    except Exception:
        start_d = end_d = None

    cc_ids = [c.id for c in cc_by_sienge.values()]
    inc_reembolso_by_cc: dict = defaultdict(lambda: defaultdict(float))
    out_cp_by_cc: dict = defaultdict(lambda: defaultdict(float))

    if start_d and end_d:
        for row in (
            db.query(ActualTransaction)
            .filter(
                ActualTransaction.cost_center_id.in_(cc_ids),
                ActualTransaction.transaction_type == "INCOME",
                ActualTransaction.is_forecast == False,
                ActualTransaction.source_id.like("INC-%"),
                ActualTransaction.category.ilike("%reembolso%"),
                ActualTransaction.transaction_date >= start_d,
                ActualTransaction.transaction_date <= end_d,
            )
            .all()
        ):
            if not row.transaction_date:
                continue
            key = (row.transaction_date.month, (row.category or "").strip())
            inc_reembolso_by_cc[row.cost_center_id][key] += float(row.value or 0)

        # Despesa já vinda do Contas a Pagar: não repetir a partir do extrato
        for row in (
            db.query(ActualTransaction)
            .filter(
                ActualTransaction.cost_center_id.in_(cc_ids),
                ActualTransaction.transaction_type == "OUTCOME",
                ActualTransaction.is_forecast == False,
                ActualTransaction.source_id.like("OUT-%"),
                ActualTransaction.transaction_date >= start_d,
                ActualTransaction.transaction_date <= end_d,
            )
            .all()
        ):
            sid = row.source_id or ""
            if not row.transaction_date or sid.startswith("OUT-BM-"):
                continue
            key = (row.transaction_date.month, (row.category or "").strip())
            out_cp_by_cc[row.cost_center_id][key] += float(row.value or 0)

        db.query(ActualTransaction).filter(
            ActualTransaction.cost_center_id.in_(cc_ids),
            ActualTransaction.transaction_type == "INCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like("BM-%"),
            ActualTransaction.transaction_date >= start_d,
            ActualTransaction.transaction_date <= end_d,
        ).delete(synchronize_session=False)

        db.query(ActualTransaction).filter(
            ActualTransaction.cost_center_id.in_(cc_ids),
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like("OUT-BM-%"),
            ActualTransaction.transaction_date >= start_d,
            ActualTransaction.transaction_date <= end_d,
        ).delete(synchronize_session=False)
        db.flush()

    from sqlalchemy import or_ as _or

    existing = {
        (r.cost_center_id, r.source_id): r
        for r in db.query(ActualTransaction)
        .filter(
            ActualTransaction.cost_center_id.in_(cc_ids),
            _or(
                ActualTransaction.source_id.like("BM-%"),
                ActualTransaction.source_id.like("OUT-BM-%"),
            ),
        )
        .all()
        if r.source_id
    }

    for page in _fetch_paginated_bulk(url):
        for item in page:
            fcs = item.get("financialCategories") or []
            cc_sienge_ids = {str(fc.get("costCenterId")) for fc in fcs if fc.get("costCenterId") is not None}
            for sid in cc_sienge_ids:
                cc = cc_by_sienge.get(sid)
                if not cc:
                    continue
                skip = build_inc_reembolso_keys(dict(inc_reembolso_by_cc.get(cc.id, {})))
                for line in iter_bank_movement_receita_lines(
                    item, sid, skip_reembolso_keys=skip
                ):
                    date_str = line["payment_date"]
                    try:
                        dtx = dt_cls.strptime(date_str[:10], "%Y-%m-%d").date()
                    except Exception:
                        continue

                    source_id = line["source_id"]
                    ex_key = (cc.id, source_id)
                    record = existing.get(ex_key)
                    if not record:
                        record = ActualTransaction(
                            cost_center_id=cc.id,
                            source_id=source_id,
                            transaction_type="INCOME",
                        )
                        db.add(record)
                        existing[ex_key] = record

                    record.transaction_type = "INCOME"
                    record.transaction_date = dtx
                    record.value = line["value"]
                    record.category = line["category_name"]
                    record.bill_id = line.get("bill_id") or None
                    record.creditor_name = line.get("creditor_name") or ""
                    record.document_name = line.get("document_name") or ""
                    record.document_number = line.get("document_number") or ""
                    record.is_forecast = False

                # Saídas do extrato sem título no Contas a Pagar (IR sobre Aplicação)
                skip_out = build_outcome_cobertura_keys(dict(out_cp_by_cc.get(cc.id, {})))
                for line in iter_bank_movement_despesa_lines(item, sid, skip_keys=skip_out):
                    date_str = line["payment_date"]
                    try:
                        dtx = dt_cls.strptime(date_str[:10], "%Y-%m-%d").date()
                    except Exception:
                        continue

                    source_id = line["source_id"]
                    ex_key = (cc.id, source_id)
                    record = existing.get(ex_key)
                    if not record:
                        record = ActualTransaction(
                            cost_center_id=cc.id,
                            source_id=source_id,
                            transaction_type="OUTCOME",
                        )
                        db.add(record)
                        existing[ex_key] = record

                    record.transaction_type = "OUTCOME"
                    record.transaction_date = dtx
                    record.value = line["value"]
                    record.category = line["category_name"]
                    record.bill_id = line.get("bill_id") or None
                    record.creditor_name = line.get("creditor_name") or ""
                    record.document_name = line.get("document_name") or ""
                    record.document_number = line.get("document_number") or ""
                    record.is_forecast = False

    db.commit()


def sync_incomes(db: Session, cc: CostCenter, start_date: str, end_date: str):
    """
    Contas a Receber realizados:
    - receipt Recebimento + bankMovement E → INCOME (rateio financialCategoryRate)
    - bankMovement S (tarifa bancária) → OUTCOME com source OUT-TARIFA-*
    """
    from datetime import datetime as dt_cls
    from sqlalchemy import or_

    from app.services.sienge_income_parse import iter_income_bank_lines

    url = (
        f"{SIENGE_BASE_URL}/income?startDate={start_date}&endDate={end_date}"
        f"&selectionType=P&correctionIndexerId=0&correctionDate=2019-01-01"
        f"&costCentersId={cc.id_sienge}&withAuthorizations=false&withBankMovements=true"
    )

    try:
        start_d = dt_cls.strptime(start_date[:10], "%Y-%m-%d").date()
        end_d = dt_cls.strptime(end_date[:10], "%Y-%m-%d").date()
    except Exception:
        start_d = end_d = None

    if start_d and end_d:
        # Limpa receitas INC-* e tarifas geradas por este fluxo no período
        db.query(ActualTransaction).filter(
            ActualTransaction.cost_center_id == cc.id,
            ActualTransaction.is_forecast == False,
            ActualTransaction.transaction_date >= start_d,
            ActualTransaction.transaction_date <= end_d,
            or_(
                ActualTransaction.source_id.like("INC-%"),
                ActualTransaction.source_id.like("OUT-TARIFA-%"),
            ),
        ).delete(synchronize_session=False)
        db.flush()

    existing = {
        r.source_id: r
        for r in db.query(ActualTransaction)
        .filter(
            ActualTransaction.cost_center_id == cc.id,
            or_(
                ActualTransaction.source_id.like("INC-%"),
                ActualTransaction.source_id.like("OUT-TARIFA-%"),
            ),
        )
        .all()
        if r.source_id
    }

    for page in _fetch_paginated_bulk(url):
        for item in page:
            for line in iter_income_bank_lines(item, str(cc.id_sienge)):
                date_str = line["payment_date"]
                try:
                    dtx = dt_cls.strptime(date_str[:10], "%Y-%m-%d").date()
                except Exception:
                    continue

                source_id = line["source_id"]
                record = existing.get(source_id)
                if not record:
                    record = ActualTransaction(
                        cost_center_id=cc.id,
                        source_id=source_id,
                        transaction_type=line["transaction_type"],
                    )
                    db.add(record)
                    existing[source_id] = record

                record.transaction_type = line["transaction_type"]
                record.transaction_date = dtx
                record.value = line["value"]
                record.category = line["category_name"]
                record.bill_id = str(line["bill_id"]) if line["bill_id"] else None
                record.creditor_name = line["creditor_name"]
                record.document_name = line["document_name"]
                record.document_number = line["document_number"]
                record.is_forecast = False

    db.commit()

def sync_receivables_forecast(db: Session, cc: CostCenter):
    from datetime import datetime
    current_year = datetime.now().year
    from sqlalchemy import text as sa_text
    db.execute(
        sa_text("DELETE FROM actual_transactions WHERE cost_center_id=:cc AND transaction_type='INCOME' AND is_forecast=1"),
        {"cc": cc.id}
    )
    db.commit()

    count = 0
    try:
        for offset in range(15):
            year = current_year + offset
            start_date = datetime.now().strftime("%Y-%m-%d") if offset == 0 else f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            url = f"{SIENGE_BASE_URL}/income?startDate={start_date}&endDate={end_date}&selectionType=D&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId={cc.id_sienge}"
            print(f"[Forecast] Buscando contas a receber futuras ({year}) para CC {cc.id_sienge}...")
            
            year_count = 0
            for page in _fetch_paginated_bulk(url):
                for item in page:
                    bill_id = item.get('billId')
                    installment_id = item.get('installmentId', item.get('installmentNumber', count))
                    
                    due_date_str = item.get('dueDate') or item.get('installmentBaseDate')
                    
                    bal = item.get('balanceAmount')
                    corr = item.get('correctedBalanceAmount')
                    
                    if bal is not None:
                        amount = max(float(bal or 0), float(corr or 0))
                    else:
                        amount = float(item.get('originalAmount') or 0)
                    
                    if not due_date_str or amount <= 0:
                        continue
                    
                    try:
                        dt = datetime.strptime(due_date_str[:10], "%Y-%m-%d").date()
                    except Exception:
                        continue

                    fcs = item.get("receiptsCategories", item.get("financialCategories", []))
                    cat_name = "Receita de Venda de Lotes"
                    is_for_cc = len(fcs) == 0
                    
                    for fc in fcs:
                        if str(fc.get("costCenterId")) == str(cc.id_sienge):
                            is_for_cc = True
                            cat_name = fc.get("financialCategoryName", cat_name)
                            break
                    
                    if not is_for_cc:
                        continue

                    source_id = f"FCST-INC-{bill_id}-{installment_id}"
                    
                    record = ActualTransaction(
                        cost_center_id=cc.id,
                        source_id=source_id,
                        transaction_type="INCOME",
                        transaction_date=dt,
                        value=amount,
                        category=cat_name,
                        is_forecast=True
                    )
                    db.add(record)
                    count += 1
                    year_count += 1
            
            print(f"[Forecast] Ano {year}: {year_count} parcelas de recebimento")
            
    except Exception as e:
        print(f"[Sienge Sync] Exception forecast income: {str(e)}")

    db.commit()
    print(f"[Forecast] {count} parcelas de recebimento futuras sincronizadas para CC {cc.id_sienge}")

def sync_payables_forecast(db: Session, cc: CostCenter):
    """
    Sincroniza Contas a Pagar EM ABERTO (parcelas futuras de obras/despesas).
    Usa selectionType=D (Due date) — nessa API cada item JÁ É a parcela,
    com campos dueDate, balanceAmount na raiz do item.
    Armazena com is_forecast=True para diferenciar do realizado.
    """
    from datetime import datetime
    current_year = datetime.now().year

    # Limpar previsões antigas para este CC
    from sqlalchemy import text as sa_text
    db.execute(
        sa_text("DELETE FROM actual_transactions WHERE cost_center_id=:cc AND transaction_type='OUTCOME' AND is_forecast=1"),
        {"cc": cc.id}
    )
    db.commit()

    count = 0
    try:
        for offset in range(15): # Busca até 15 anos à frente, ano a ano
            year = current_year + offset
            start_date = datetime.now().strftime("%Y-%m-%d") if offset == 0 else f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            url = f"{SIENGE_BASE_URL}/outcome?startDate={start_date}&endDate={end_date}&selectionType=D&correctionIndexerId=0&correctionDate=2019-01-01&costCentersId={cc.id_sienge}&withAuthorizations=false&withBankMovements=false"
            print(f"[Forecast] Buscando contas a pagar futuras ({year}) para CC {cc.id_sienge}...")
            
            year_count = 0
            for page in _fetch_paginated_bulk(url):
                for item in page:
                    # Na API selectionType=D, cada item JÁ É a parcela
                    bill_id = item.get('billId', item.get('documentId'))
                    installment_id = item.get('installmentId', item.get('installmentNumber', count))
                
                    # Categoria financeira
                    cat_name = "Obras"
                    cats = item.get("paymentsCategories", [])
                    if cats:
                        for c in cats:
                            if str(c.get("costCenterId")) == str(cc.id_sienge):
                                cat_name = c.get("financialCategoryName", "Obras")
                                break

                    # Dada de vencimento e valor em aberto
                    due_date_str = item.get('dueDate') or item.get('installmentBaseDate')
                    
                    # Valor em aberto: usar balanceAmount para determinar se está pago/distratado
                    bal = item.get('balanceAmount')
                    corr = item.get('correctedBalanceAmount')
                    
                    if bal is not None:
                        amount = max(float(bal or 0), float(corr or 0))
                    elif item.get('openValue') is not None:
                        amount = max(float(item.get('openValue') or 0), float(item.get('correctedAmount') or 0))
                    else:
                        amount = float(item.get('originalAmount') or 0)
                    
                    if not due_date_str or amount <= 0:
                        continue
                    
                    try:
                        dt = datetime.strptime(due_date_str[:10], "%Y-%m-%d").date()
                    except Exception:
                        continue

                    source_id = f"FCST-OUT-{bill_id}-{installment_id}"
                    
                    record = ActualTransaction(
                        cost_center_id=cc.id,
                        source_id=source_id,
                        transaction_type="OUTCOME",
                        transaction_date=dt,
                        value=amount,
                        category=cat_name,
                        is_forecast=True
                    )
                    db.add(record)
                    count += 1
                    year_count += 1
            
            print(f"[Forecast] Ano {year}: {year_count} parcelas a pagar")
            # DO NOT BREAK IF ZERO, AS FUTURE YEARS MIGHT HAVE DATA
            
    except Exception as e:
        print(f"[Sienge Sync] Exception forecast outcome: {str(e)}")

    db.commit()
    db.commit()
    print(f"[Forecast] {count} parcelas de pagamento futuras sincronizadas para CC {cc.id_sienge}")

def sync_sienge_colaboradores(db: Session):
    from app.services.sienge_api import get_colaboradores
    from app.models.sienge_colaborador import SiengeColaborador
    
    colaboradores = get_colaboradores()
    
    existing = {
        c.sienge_id: c
        for c in db.query(SiengeColaborador).all()
    }
    
    for colab in colaboradores:
        sienge_id = colab.get("sienge_id")
        record = existing.get(sienge_id)
        if not record:
            record = SiengeColaborador(sienge_id=sienge_id)
            db.add(record)
            existing[sienge_id] = record
            
        record.name = colab.get("name")
        record.trade_name = colab.get("trade_name")
        record.cpf = colab.get("cpf")
        record.phone_ddd = colab.get("phone_ddd")
        record.phone_number = colab.get("phone_number")
        record.address_json = colab.get("address_json")
        record.email = colab.get("email")
        
    db.commit()
    print(f"[Sienge Sync] {len(colaboradores)} colaboradores sincronizados com sucesso.")
