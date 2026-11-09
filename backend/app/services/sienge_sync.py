import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.cost_center import CostCenter
from app.models.actual_transaction import ActualTransaction
from app.models.unit import Unit
from app.services.sienge_client import bulk_base_url, get_default_client
from app.services.sienge_income_parse import rateio_previsto_do_cc

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

def _fetch_paginated_bulk_direto(url: str):
    # strict: se uma página falhar, levanta erro e a transação é desfeita (nada é apagado com leitura parcial)
    yield from get_default_client().paginate_bulk(url, strict=True)


def _fetch_paginated_bulk(url: str):
    """Auxiliar para buscar todas as páginas de um endpoint Bulk Data. Retorna em blocos.
    Dentro de sienge_busca_unica.busca_unica(), URLs com costCentersId são servidas
    pela busca única da empresa toda (ver sienge_busca_unica.py)."""
    from app.services.sienge_busca_unica import ativa

    cache = ativa()
    if cache is not None:
        yield from cache.paginas_do_cc(url)
        return
    yield from _fetch_paginated_bulk_direto(url)

def centros_do_sync(db: Session) -> list:
    """Todos os centros de custo com código no Sienge (passo 5, 09/11/2026).

    Antes eram só os CCs com o mesmo prefixo de 3 dígitos dos acompanhados no
    dashboard (~10 grupos); os demais ficavam sem realizado novo. Com a busca
    única, incluir todos não aumenta as buscas no Sienge.
    """
    return (
        db.query(CostCenter)
        .filter(CostCenter.id_sienge.isnot(None), CostCenter.id_sienge != "")
        .order_by(CostCenter.id_sienge)
        .all()
    )


def sync_all_sienge_data(db: Session, full_load: bool = False, desde: Optional[str] = None):
    """
    Roda o sincronismo de Vendas, Recebimentos e Pagamentos.
    Se full_load for True, busca desde 2001. Se False, busca os últimos 3 dias por segurança.
    desde (AAAA-MM-DD): recarga a partir dessa data até hoje (ex.: preencher um buraco).
    """
    if full_load:
        start_date = "2001-01-01"
        end_date = "2050-12-31"
    elif desde:
        start_date = datetime.strptime(desde[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
    else:
        hoje = datetime.now()
        start_date = (hoje - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = hoje.strftime("%Y-%m-%d")

    centros = centros_do_sync(db)
    
    falhas: list[str] = []
    from app.services.sienge_busca_unica import busca_unica

    # Uma busca bulk para a empresa toda em vez de ~34 por centro de custo (passo 5).
    with busca_unica(_fetch_paginated_bulk_direto):
        for cc in centros:
            if not cc.id_sienge:
                continue
            try:
                sync_single_cc_sienge_data(db, cc, start_date, end_date, include_engineering=False)
            except Exception as exc:
                db.rollback()
                falhas.append(f"{cc.id_sienge}: {exc}")
                print(f"[Sienge Sync] Falha no CC {cc.id_sienge} ({cc.nome}): {exc}")

    print("Sincronizando cronograma de engenharia (TRK-ENG, só acompanhamento)...")
    try:
        from app.services.tracking_engineering import sync_engineering_disbursements
        eng = sync_engineering_disbursements(db)
        print(f"[Sienge Sync] TRK-ENG buildings: {eng}")
    except Exception as e:
        print(f"[Sienge Sync] Aviso: cronograma de engenharia não aplicado: {e}")

    # Caixa e Bancos — uma passagem para todos os CCs do sync
    print("Sincronizando Caixa e Bancos (BM-*)...")
    sync_bank_movements_batch(db, start_date, end_date, cost_centers=centros)

    print("Sincronizando saldos de caixa 31/12 (B+I+C)...")
    try:
        from app.services.sienge_account_balances import persist_closed_year_balances

        snap = persist_closed_year_balances(db)
        print(f"[Sienge Sync] snapshot caixa: {snap}")
    except Exception as e:
        print(f"[Sienge Sync] Aviso: snapshot caixa não aplicado: {e}")

    # Ao final do sincronismo de centros de custo, sincroniza também os colaboradores
    print("Sincronizando Colaboradores (Credores) do Sienge...")
    sync_sienge_colaboradores(db)

    if falhas:
        raise RuntimeError(
            "Sincronização Sienge incompleta: " + "; ".join(falhas[:8])
        )

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


def sync_single_cc_sienge_data(db: Session, cc: CostCenter, start_date: str = "2001-01-01", end_date: str = "2050-12-31", include_engineering: bool = True):
    if not cc.id_sienge:
        return
        
    print(f"Sincronizando CC {cc.nome} (Sienge ID: {cc.id_sienge})...")
    
    # 0. SINCRONIZAR UNIDADES (Estoque) — API REST tem cota diária curta:
    # CC com unidades 1x/dia; CC sem unidades 1x/semana (para achar obra nova).
    sync_units_se_preciso(db, cc)
    
    # 1. SINCRONIZAR VENDAS (Sales) - realizadas. /sales exige enterpriseId (uma busca
    # por CC), então só para CC com unidades: em 09/11/2026 todo CC com venda tinha
    # unidades; obra nova ganha unidades na checagem semanal acima e entra no mesmo dia.
    if db.query(Unit.id).filter_by(cost_center_id=cc.id).first() is not None:
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

    # 6. Títulos vencidos em aberto — só o DFC de empreendimentos (não é forecast)
    sync_overdue_open_tracking(db, cc)

    # 7. Cronograma da engenharia — só acompanhamento, nunca FCST/OP1
    if include_engineering:
        try:
            from app.services.tracking_engineering import sync_engineering_disbursement_for_cc
            n = sync_engineering_disbursement_for_cc(db, cc)
            print(f"[Sienge Sync] TRK-ENG {cc.id_sienge}: {n} linhas")
        except Exception as e:
            print(f"[Sienge Sync] Aviso TRK-ENG {cc.id_sienge}: {e}")

UNITS_SYNC_KEY = "__units_sync_at"
DIAS_ENTRE_CHECAGENS_SEM_UNIDADES = 7


def precisa_sincronizar_unidades(ultima: Optional[str], tem_unidades: bool, hoje) -> bool:
    """Decide se busca as unidades do CC hoje (a API REST do Sienge tem cota diária).

    ultima: data ISO (AAAA-MM-DD) da última busca bem-sucedida, ou None.
    """
    if not ultima:
        return True
    try:
        ultima_data = datetime.strptime(str(ultima)[:10], "%Y-%m-%d").date()
    except ValueError:
        return True
    if ultima_data >= hoje:
        return False
    if tem_unidades:
        return True
    return (hoje - ultima_data).days >= DIAS_ENTRE_CHECAGENS_SEM_UNIDADES


def _dia_da_primeira_checagem(cc: CostCenter, hoje) -> bool:
    digitos = "".join(ch for ch in str(cc.id_sienge or "") if ch.isdigit())
    base = int(digitos) if digitos else (cc.id or 0)
    return base % DIAS_ENTRE_CHECAGENS_SEM_UNIDADES == hoje.toordinal() % DIAS_ENTRE_CHECAGENS_SEM_UNIDADES


def sync_units_se_preciso(db: Session, cc: CostCenter, hoje=None) -> bool:
    """Chama sync_units só quando precisa; grava a data da busca no custom_data do CC.
    Retorna True se buscou."""
    hoje = hoje or datetime.now().date()
    custom = dict(cc.custom_data or {})
    tem_unidades = db.query(Unit.id).filter_by(cost_center_id=cc.id).first() is not None
    ultima = custom.get(UNITS_SYNC_KEY)
    if not ultima and not tem_unidades and not _dia_da_primeira_checagem(cc, hoje):
        # Primeira checagem de CC sem unidades espalhada pelos 7 dias da semana:
        # na estreia não chamamos /units dos ~250 CCs sem lote no mesmo dia (cota REST).
        return False
    if not precisa_sincronizar_unidades(ultima, tem_unidades, hoje):
        return False
    if sync_units(db, cc):
        custom[UNITS_SYNC_KEY] = hoje.isoformat()
        cc.custom_data = custom  # novo dict: o SQLAlchemy percebe a mudança no JSON
        db.commit()
    return True


def sync_units(db: Session, cc: CostCenter) -> bool:
    """Sincroniza as unidades (Lotes/Apartamentos) do Centro de Custo. Retorna True se leu sem erro."""
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
        return False

    db.commit()
    return True

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


def apply_pmt_historico_rateio_lines(db: Session, cc: CostCenter, lines, start_d, end_d) -> dict:
    """Atualiza só OUT-{titulo}-PMT-{n} legado. Não cria/apaga OP1 (orçamento não lê PMT)."""
    from datetime import datetime as dt_cls

    from app.services.sienge_outcome_parse import is_legacy_pmt_source_id

    existing = {
        r.source_id: r
        for r in db.query(ActualTransaction).filter(
            ActualTransaction.cost_center_id == cc.id,
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like("OUT-%-PMT-%"),
            ~ActualTransaction.source_id.like("OUT-%-OP%"),
        ).all()
        if is_legacy_pmt_source_id(r.source_id)
    }

    seen: set[str] = set()
    updated = inserted = 0
    for line in lines:
        source_id = line["source_id"]
        if not is_legacy_pmt_source_id(source_id):
            continue
        date_str = line.get("payment_date") or ""
        try:
            dtx = dt_cls.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        seen.add(source_id)
        record = existing.get(source_id)
        if not record:
            record = ActualTransaction(
                cost_center_id=cc.id,
                source_id=source_id,
                transaction_type="OUTCOME",
            )
            db.add(record)
            existing[source_id] = record
            inserted += 1
        else:
            updated += 1
        record.transaction_date = dtx
        record.value = line["value"]
        record.category = line.get("category_name") or "Obras"
        record.bill_id = str(line["bill_id"]) if line.get("bill_id") else None
        record.creditor_name = line.get("creditor_name")
        record.document_name = line.get("document_name")
        record.document_number = line.get("document_number")
        record.is_forecast = False

    deleted = 0
    if seen:
        for sid, rec in list(existing.items()):
            if sid in seen:
                continue
            if rec.transaction_date and start_d <= rec.transaction_date <= end_d:
                db.delete(rec)
                deleted += 1

    db.commit()
    return {"updated": updated, "inserted": inserted, "deleted": deleted}


def rewrite_pmt_historico_rateio(db: Session, cc: CostCenter, start_date: str, end_date: str) -> dict:
    """Busca o título na Sienge e regrava o PMT legado com financialCategoryRate.

    Não chama sync_outcomes: aquele fluxo grava OP1, que o orçamento lê.
    """
    from datetime import datetime as dt_cls

    from app.services.sienge_outcome_parse import iter_pmt_historico_lines

    try:
        start_d = dt_cls.strptime(start_date[:10], "%Y-%m-%d").date()
        end_d = dt_cls.strptime(end_date[:10], "%Y-%m-%d").date()
    except Exception:
        return {"updated": 0, "inserted": 0, "deleted": 0}

    url = outcome_contas_pagar_url(str(cc.id_sienge), start_date, end_date)
    lines = []
    for page in _fetch_paginated_bulk(url):
        for item in page:
            lines.extend(iter_pmt_historico_lines(item, str(cc.id_sienge)))
    return apply_pmt_historico_rateio_lines(db, cc, lines, start_d, end_d)


_PMT_RATEIO_DONE_KEY = "pmt_historico_rateio_done"


def _pmt_rateio_done_ids(db) -> set[str]:
    from app.models.system_settings import SystemSettings

    row = db.query(SystemSettings).filter_by(key=_PMT_RATEIO_DONE_KEY).first()
    if not row or not isinstance(row.value, dict):
        return set()
    return {str(x) for x in (row.value.get("ids") or [])}


def _pmt_rateio_mark_done(db, id_sienge: str) -> None:
    from datetime import datetime as dt_cls

    from app.models.system_settings import SystemSettings

    row = db.query(SystemSettings).filter_by(key=_PMT_RATEIO_DONE_KEY).first()
    ids = []
    if row and isinstance(row.value, dict):
        ids = [str(x) for x in (row.value.get("ids") or [])]
    if id_sienge not in ids:
        ids.append(id_sienge)
    payload = {"ids": ids}
    if not row:
        db.add(SystemSettings(key=_PMT_RATEIO_DONE_KEY, value=payload))
    else:
        row.value = payload
        row.updated_at = dt_cls.utcnow()
    db.commit()


def rewrite_pmt_historico_todos_ccs(
    db: Session, start_year: int = 2016, end_year: int = 2026
) -> dict:
    """Regrava PMT legado em todos os CCs que já têm esse source_id. Só acompanhamento.

    CCs já gravados em system_settings (pmt_historico_rateio_done) são pulados —
    o plano free do Render mata o job; o próximo disparo continua de onde parou.
    """
    from sqlalchemy import distinct

    ids = [
        row[0]
        for row in db.query(distinct(ActualTransaction.cost_center_id))
        .filter(
            ActualTransaction.transaction_type == "OUTCOME",
            ActualTransaction.is_forecast == False,
            ActualTransaction.source_id.like("OUT-%-PMT-%"),
            ~ActualTransaction.source_id.like("OUT-%-OP%"),
        )
        .all()
        if row[0] is not None
    ]
    ccs = (
        db.query(CostCenter).filter(CostCenter.id.in_(ids)).order_by(CostCenter.id_sienge).all()
        if ids
        else []
    )
    tot = {"updated": 0, "inserted": 0, "deleted": 0, "ccs": 0, "fail": 0, "skipped": 0}
    already = _pmt_rateio_done_ids(db)
    for cc in ccs:
        if not cc.id_sienge:
            continue
        if cc.id_sienge in already:
            tot["skipped"] += 1
            continue
        print(f"[PMT rateio] {cc.id_sienge} {(cc.nome or '')[:40]}", flush=True)
        ok_cc = True
        try:
            for year in range(start_year, end_year + 1):
                try:
                    stats = rewrite_pmt_historico_rateio(db, cc, f"{year}-01-01", f"{year}-12-31")
                    tot["updated"] += stats["updated"]
                    tot["inserted"] += stats["inserted"]
                    tot["deleted"] += stats["deleted"]
                except Exception as year_exc:
                    db.rollback()
                    ok_cc = False
                    tot["fail"] += 1
                    print(f"[PMT rateio] Falha {cc.id_sienge} {year}: {year_exc}", flush=True)
            if ok_cc:
                _pmt_rateio_mark_done(db, cc.id_sienge)
                already.add(cc.id_sienge)
                tot["ccs"] += 1
        except Exception as exc:
            db.rollback()
            tot["fail"] += 1
            print(f"[PMT rateio] Falha {cc.id_sienge}: {exc}", flush=True)
    print(f"[PMT rateio] fim {tot}", flush=True)
    return tot


def run_rewrite_pmt_historico_rateio_job():
    """Job em background: sessão própria (a do request HTTP fecha)."""
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        rewrite_pmt_historico_todos_ccs(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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

    from sqlalchemy import or_ as _or

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
                _or(
                    ActualTransaction.category.ilike("%reembolso%"),
                    ActualTransaction.category.ilike("%duplicidade%"),
                ),
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

def _clear_open_forecast(db: Session, cost_center_id: int, transaction_type: str) -> None:
    """Apaga só FCST-* (previsão futura). Não apaga TRK-VENC-* do DFC de empreendimentos.
    Só flush: a exclusão vale apenas se a nova busca terminar (commit no fim da função chamadora)."""
    db.query(ActualTransaction).filter(
        ActualTransaction.cost_center_id == cost_center_id,
        ActualTransaction.transaction_type == transaction_type,
        ActualTransaction.is_forecast.is_(True),
        ActualTransaction.source_id.like("FCST-%"),
    ).delete(synchronize_session=False)
    db.flush()


def sync_receivables_forecast(db: Session, cc: CostCenter):
    from datetime import datetime
    current_year = datetime.now().year
    _clear_open_forecast(db, cc.id, "INCOME")

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
                    fatia = rateio_previsto_do_cc(fcs, cc.id_sienge, "Receita de Venda de Lotes")
                    if not fatia:
                        continue
                    ratio, cat_name = fatia
                    amount = amount * ratio

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
        db.rollback()
        raise

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

    _clear_open_forecast(db, cc.id, "OUTCOME")

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
                
                    cats = item.get("paymentsCategories") or item.get("financialCategories") or []
                    fatia = rateio_previsto_do_cc(cats, cc.id_sienge, "Obras")
                    if not fatia:
                        continue
                    ratio, cat_name = fatia

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
                    amount = amount * ratio
                    
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
        db.rollback()
        raise

    db.commit()
    db.commit()
    print(f"[Forecast] {count} parcelas de pagamento futuras sincronizadas para CC {cc.id_sienge}")


def _clear_trk_venc(db: Session, cost_center_id: int) -> None:
    db.query(ActualTransaction).filter(
        ActualTransaction.cost_center_id == cost_center_id,
        ActualTransaction.is_forecast.is_(True),
        ActualTransaction.source_id.like("TRK-VENC-%"),
    ).delete(synchronize_session=False)
    db.flush()


def sync_overdue_open_tracking(db: Session, cc: CostCenter, start_year: Optional[int] = None) -> int:
    """Títulos vencidos com saldo, para o DFC de empreendimentos.

    Não grava FCST-* e não entra nas telas de forecast/orçamento.
    """
    if not cc.id_sienge:
        return 0
    today = datetime.now().date()
    year0 = start_year if start_year is not None else today.year
    _clear_trk_venc(db, cc.id)
    count = 0
    try:
        for year in range(year0, today.year + 1):
            start = f"{year}-01-01"
            end = today.isoformat() if year == today.year else f"{year}-12-31"
            url_in = (
                f"{SIENGE_BASE_URL}/income?startDate={start}&endDate={end}"
                f"&selectionType=D&correctionIndexerId=0&correctionDate=2019-01-01"
                f"&costCentersId={cc.id_sienge}"
            )
            for page in _fetch_paginated_bulk(url_in):
                for item in page:
                    n = _add_overdue_line(db, cc, item, "INCOME", today)
                    count += n
            url_out = (
                f"{SIENGE_BASE_URL}/outcome?startDate={start}&endDate={end}"
                f"&selectionType=D&correctionIndexerId=0&correctionDate=2019-01-01"
                f"&costCentersId={cc.id_sienge}&withAuthorizations=false&withBankMovements=false"
            )
            for page in _fetch_paginated_bulk(url_out):
                for item in page:
                    n = _add_overdue_line(db, cc, item, "OUTCOME", today)
                    count += n
    except Exception as exc:
        print(f"[Sienge Sync] Exception overdue tracking CC {cc.id_sienge}: {exc}")
        db.rollback()
        raise
    db.commit()
    print(f"[Tracking] {count} títulos vencidos em aberto para CC {cc.id_sienge}")
    return count


def _add_overdue_line(db: Session, cc: CostCenter, item: dict, tipo: str, today) -> int:
    due_date_str = item.get("dueDate") or item.get("installmentBaseDate")
    if not due_date_str:
        return 0
    try:
        dt = datetime.strptime(str(due_date_str)[:10], "%Y-%m-%d").date()
    except Exception:
        return 0
    if dt >= today:
        return 0
    bal = item.get("balanceAmount")
    corr = item.get("correctedBalanceAmount")
    if bal is not None:
        amount = max(float(bal or 0), float(corr or 0))
    else:
        amount = float(item.get("originalAmount") or item.get("openValue") or 0)
    if amount <= 0:
        return 0
    if tipo == "INCOME":
        cats = item.get("receiptsCategories") or item.get("financialCategories") or []
        default = "Receita de Venda de Lotes"
        prefix = "TRK-VENC-INC"
    else:
        cats = item.get("paymentsCategories") or item.get("financialCategories") or []
        default = "Obras"
        prefix = "TRK-VENC-OUT"
    fatia = rateio_previsto_do_cc(cats, cc.id_sienge, default)
    if not fatia:
        return 0
    ratio, cat_name = fatia
    amount = amount * ratio
    if amount <= 0:
        return 0
    bill_id = item.get("billId") or item.get("documentId")
    installment_id = item.get("installmentId", item.get("installmentNumber", 0))
    db.add(
        ActualTransaction(
            cost_center_id=cc.id,
            source_id=f"{prefix}-{bill_id}-{installment_id}",
            transaction_type=tipo,
            transaction_date=dt,
            value=amount,
            category=cat_name,
            is_forecast=True,
        )
    )
    return 1


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
