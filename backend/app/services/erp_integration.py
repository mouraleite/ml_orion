import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.actual_transaction import ActualTransaction
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.services.sienge_api_service import SiengeApiService
import json

logger = logging.getLogger(__name__)

class DummyErpService:
    def fetch_empresas(self): return []
    def fetch_centros_custo(self): return []
    def fetch_enterprises(self): return []
    def fetch_planos_financeiros(self): return []

erp_service = DummyErpService()

class ErpIntegrationService:
    def __init__(self, db: Session, subdomain: str, auth_string: str):
        self.db = db
        self.api = SiengeApiService(subdomain, auth_string)

    def sync_realizado_outcome(self, start_date: str, end_date: str, company_id: int = 1):
        """
        Sincroniza o Contas a Pagar (Realizado/Outcome) usando a API Padrão
        porque a API Massiva retornou 0 na PoC.
        """
        logger.info(f"Iniciando sincronização de despesas (Sienge API Padrão) {start_date} a {end_date}")
        
        ccs = self.db.query(CostCenter).all()
        cc_map = {}
        for cc in ccs:
            if cc.custom_data:
                try:
                    cdata = cc.custom_data if isinstance(cc.custom_data, dict) else json.loads(cc.custom_data)
                    if str(cdata.get('__id_empresa')) == str(company_id):
                        if cc.id_sienge:
                            cc_map[str(cc.id_sienge)] = cc.id
                except:
                    pass

        # Buscamos o ID dos planos financeiros (pelo nome)
        planos = self.db.query(FinancialPlan).all()
        plano_map = {p.name.lower(): p.name for p in planos}
        
        total_synced = 0
        
        for id_sienge, cc_db_id in cc_map.items():
            bills = self.api.get_bills(start_date, end_date, id_sienge)
            for bill in bills:
                bill_id = bill['id']
                
                installments = self.api.get_bill_installments(bill_id)
                budget_categories = self.api.get_bill_budget_categories(bill_id)
                
                for inst in installments:
                    if inst.get('situation') != 'Totalmente paga':
                        continue
                        
                    amount = float(inst.get('amount', 0.0))
                    date_str = inst.get('paymentDate') or inst.get('dueDate') or inst.get('baseDate')
                    if not date_str:
                        continue
                        
                    try:
                        t_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except:
                        t_date = datetime.now().date()
                        
                    source_id = f"SIENGE-OUT-{bill_id}-{inst.get('installmentNumber', 0)}"
                    
                    for cat in budget_categories:
                        cat_cc_id = str(cat.get('costCenterId'))
                        if cat_cc_id != id_sienge:
                            continue
                            
                        perc = float(cat.get('percentage', 100.0)) / 100.0
                        cat_amount = amount * perc
                        
                        cat_name = cat.get('paymentCategoriesName')
                        db_cat_name = cat_name
                        if cat_name and cat_name.lower() in plano_map:
                            db_cat_name = plano_map[cat_name.lower()]
                            
                        # Upsert ActualTransaction
                        existing = self.db.query(ActualTransaction).filter(
                            ActualTransaction.source_id == source_id,
                            ActualTransaction.category == db_cat_name
                        ).first()
                        
                        if existing:
                            existing.value = cat_amount
                            existing.transaction_date = t_date
                        else:
                            new_tx = ActualTransaction(
                                cost_center_id=cc_db_id,
                                source_id=source_id,
                                transaction_type="OUTCOME",
                                category=db_cat_name,
                                transaction_date=t_date,
                                value=cat_amount,
                                is_forecast=False
                            )
                            self.db.add(new_tx)
                        
                        total_synced += 1
                        
            self.db.commit()
            
        logger.info(f"Sincronização concluída. {total_synced} parcelas importadas/atualizadas.")
        return total_synced

    def sync_realizado_income(self, start_date: str, end_date: str, company_id: int = 1):
        """
        Sincroniza o Contas a Receber (Realizado/Income) usando a API Bulk Data
        """
        logger.info(f"Iniciando sincronização de receitas (Sienge Bulk API) {start_date} a {end_date}")
        
        ccs = self.db.query(CostCenter).all()
        cc_map = {}
        for cc in ccs:
            if cc.id_sienge:
                cc_map[str(cc.id_sienge)] = cc.id

        planos = self.db.query(FinancialPlan).all()
        plano_map = {p.name.lower(): p.name for p in planos}
        
        incomes = self.api.get_bulk_income(company_id, start_date, end_date)
        total_synced = 0
        
        for item in incomes:
            bill_id = item.get('billId')
            receipts = item.get('receipts', [])
            
            for receipt in receipts:
                date_str = receipt.get('paymentDate')
                if not date_str or not (start_date <= date_str <= end_date):
                    continue
                    
                try:
                    t_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    t_date = datetime.now().date()
                    
                # We need to process each bank movement
                bank_movements = receipt.get('bankMovements', [])
                for bm in bank_movements:
                    op_type = bm.get('operationType')
                    if op_type not in ('E', 'S'):
                        continue
                        
                    bm_id = bm.get('id')
                    amount = float(bm.get('correctedAmount', 0.0))
                    
                    categories = bm.get('financialCategories', [])
                    for cat in categories:
                        cat_cc_id = str(cat.get('costCenterId', ''))
                        if cat_cc_id not in cc_map:
                            continue
                            
                        db_cc_id = cc_map[cat_cc_id]
                        
                        rate = float(cat.get('financialCategoryRate', 100)) / 100.0
                        cat_amount = amount * rate
                        
                        cat_name = cat.get('financialCategoryName', '')
                        db_cat_name = cat_name
                        if cat_name and cat_name.lower() in plano_map:
                            db_cat_name = plano_map[cat_name.lower()]
                            
                        source_id = f"SIENGE-INC-{bill_id}-{bm_id}-{cat.get('financialCategoryId', '0')}"
                        
                        # In Sienge, 'E' is income (+), 'S' is a deduction from income (-)
                        final_value = cat_amount if op_type == 'E' else -cat_amount
                        
                        existing = self.db.query(ActualTransaction).filter(
                            ActualTransaction.source_id == source_id
                        ).first()
                        
                        if existing:
                            existing.value = final_value
                            existing.transaction_date = t_date
                            existing.category = db_cat_name
                        else:
                            new_tx = ActualTransaction(
                                cost_center_id=db_cc_id,
                                source_id=source_id,
                                transaction_type="INCOME",
                                category=db_cat_name,
                                transaction_date=t_date,
                                value=final_value,
                                is_forecast=False
                            )
                            self.db.add(new_tx)
                        
                        total_synced += 1
                        
        self.db.commit()
        logger.info(f"Sincronização de receitas concluída. {total_synced} registros de categorias financeiras importados.")
        return total_synced
