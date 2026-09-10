import json
import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.services.sienge_sync import _fetch_paginated_bulk, SIENGE_BASE_URL
from app.models.integracao import RealizadoSienge, IntegracaoLog
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan

def run_integracao_sienge(db: Session, start_date: str, end_date: str):
    log = IntegracaoLog(
        processo="CARGA_REALIZADO_SIENGE",
        inicio=datetime.utcnow(),
        status="PROCESSANDO"
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    erros = []
    volume = 0

    try:
        # Load known IDs
        known_ccs = {cc.id_sienge for cc in db.query(CostCenter).filter(CostCenter.id_sienge != None).all()}
        known_fps = {fp.db_id for fp in db.query(FinancialPlan).filter(FinancialPlan.db_id != None).all()}

        # Dictionary to store upserts before committing
        # Key: id_sienge (unique)
        upserts = {}

        # 1. OUTCOMES (Despesas)
        url_outcome = f"{SIENGE_BASE_URL}/outcome?startDate={start_date}&endDate={end_date}&selectionType=P&withBankMovements=true"
        for page in _fetch_paginated_bulk(url_outcome):
            for item in page:
                bill_id = item.get('billId', item.get('documentId'))
                
                payments = item.get("payments", [])
                for pmt in payments:
                    bms = pmt.get("bankMovements", [])
                    for bm in bms:
                        # Extrai categorias financeiras deste bank movement
                        fcs = bm.get("financialCategories", [])
                        if not fcs:
                            # Tenta pegar da raiz do bill se não tiver no bank movement
                            fcs = item.get("paymentsCategories", [])

                        for fc in fcs:
                            cc_id = str(fc.get("costCenterId")) if fc.get("costCenterId") else None
                            fp_id = str(fc.get("financialCategoryId")) if fc.get("financialCategoryId") else None
                            value = float(fc.get("amount", bm.get("amount", 0)))
                            
                            bm_id = bm.get("id", bm.get("sequencialNumber", "0"))
                            source_id = f"OUT-{bill_id}-BM-{bm_id}-CC-{cc_id}-FC-{fp_id}"
                            
                            date_str = bm.get("bankMovementDate", pmt.get("paymentDate"))
                            if not date_str:
                                continue
                            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")

                            upserts[source_id] = {
                                "id_sienge": source_id,
                                "produto_id_sienge": cc_id,
                                "plano_financeiro_id_sienge": fp_id,
                                "mes": dt.month,
                                "ano": dt.year,
                                "valor": abs(value), # despesa -> positivo em módulo, ou mantemos como vem? Mantemos positivo
                                "vgv": 0.0,
                                "tipo": "Despesa"
                            }

        # 2. INCOMES (Receitas)
        url_income = f"{SIENGE_BASE_URL}/income?startDate={start_date}&endDate={end_date}&selectionType=P"
        for page in _fetch_paginated_bulk(url_income):
            for item in page:
                bill_id = item.get('billId', item.get('documentId'))
                receipts = item.get('receipts', [])
                for rec in receipts:
                    bms = rec.get('bankMovements', [])
                    for bm in bms:
                        fcs = bm.get("financialCategories", [])
                        if not fcs:
                            # Caso venha nulo no bank movement, tentamos na raiz
                            pass
                        
                        for fc in fcs:
                            cc_id = str(fc.get("costCenterId")) if fc.get("costCenterId") else None
                            fp_id = str(fc.get("financialCategoryId")) if fc.get("financialCategoryId") else None
                            value = float(fc.get("amount", bm.get("amount", 0)))
                            
                            bm_id = bm.get("id", bm.get("sequencialNumber", "0"))
                            source_id = f"INC-{bill_id}-BM-{bm_id}-CC-{cc_id}-FC-{fp_id}"
                            
                            date_str = bm.get("bankMovementDate")
                            if not date_str:
                                continue
                            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")

                            upserts[source_id] = {
                                "id_sienge": source_id,
                                "produto_id_sienge": cc_id,
                                "plano_financeiro_id_sienge": fp_id,
                                "mes": dt.month,
                                "ano": dt.year,
                                "valor": abs(value),
                                "vgv": 0.0,
                                "tipo": "Receita"
                            }

        # 3. SALES (Vendas)
        # Sienge API para vendas exige informar enterpriseId, não dá pra puxar todos.
        # Vamos rodar sales por CostCenter mapeado localmente
        for cc_id in known_ccs:
            situations = ["SOLD", "CANCELED"]
            for sit in situations:
                url_sales = f"{SIENGE_BASE_URL}/sales?enterpriseId={cc_id}&createdAfter={start_date}&createdBefore={end_date}&situation={sit}"
                for page in _fetch_paginated_bulk(url_sales):
                    for item in page:
                        sale_id = item.get("id")
                        source_id = f"SALE-{sale_id}-{sit}"
                        
                        value = float(item.get("totalSellingValue") or 0.0) # VGV original do Sienge
                        
                        date_str = item.get("contractDate", item.get("issueDate"))
                        if not date_str:
                            continue
                        
                        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")

                        upserts[source_id] = {
                            "id_sienge": source_id,
                            "produto_id_sienge": str(cc_id),
                            "plano_financeiro_id_sienge": None, # Vendas não tem categoria no bulk de sales
                            "mes": dt.month,
                            "ano": dt.year,
                            "valor": 0.0,
                            "vgv": value if sit == "SOLD" else -abs(value), # Distrato negativo
                            "tipo": "Venda"
                        }


        # 4. Carga: Upsert
        # Prepara todos os IDs existentes para atualizar
        existing_records = db.query(RealizadoSienge).filter(
            RealizadoSienge.id_sienge.in_(list(upserts.keys()))
        ).all()
        
        existing_map = {r.id_sienge: r for r in existing_records}
        
        new_records = []
        for sid, data in upserts.items():
            if sid in existing_map:
                record = existing_map[sid]
                record.produto_id_sienge = data["produto_id_sienge"]
                record.plano_financeiro_id_sienge = data["plano_financeiro_id_sienge"]
                record.mes = data["mes"]
                record.ano = data["ano"]
                record.valor = data["valor"]
                record.vgv = data["vgv"]
                record.tipo = data["tipo"]
                record.data_integracao = datetime.utcnow()
            else:
                new_records.append(RealizadoSienge(**data, data_integracao=datetime.utcnow()))
        
        if new_records:
            db.add_all(new_records)
            
        db.commit()
        volume = len(upserts)

        log.status = "SUCESSO" if not erros else "PARCIAL"

    except Exception as e:
        db.rollback()
        log.status = "ERRO"
        erros.append(str(e))
        erros.append(traceback.format_exc())

    finally:
        log.fim = datetime.utcnow()
        log.volume_processado = volume
        if erros:
            log.erros = json.dumps(erros)
        
        db.commit()

    return {
        "status": log.status,
        "volume_processado": log.volume_processado,
        "erros": erros
    }
