from datetime import datetime, date
from collections import defaultdict
from sqlalchemy import func
from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.models.actual_transaction import ActualTransaction
from app.models.unit import Unit

def calc_cost_center_actuals(db, cc_id: int):
    # DRE e Fluxo de Caixa
    transactions = db.query(ActualTransaction).filter_by(cost_center_id=cc_id).all()
    
    anual_cf = defaultdict(lambda: {"Entradas": 0, "Tributos": 0, "Obras": 0, "Projetos": 0, "Marketing": 0, "Comercial": 0, "Saidas": 0})
    
    vgv_vendido = 0.0
    distratos = 0.0
    impostos = 0.0
    recebimentos = 0.0
    obras = 0.0
    terreno = 0.0
    comercial_mkt = 0.0
    administrativas = 0.0
    
    sales_by_month = defaultdict(list)
    
    for t in transactions:
        ano = str(t.transaction_date.year) if t.transaction_date else "N/A"
        mes = t.transaction_date.strftime("%Y-%m") if t.transaction_date else "N/A"
        
        if t.transaction_type == "SALE":
            if t.category == "VGV Vendido":
                vgv_vendido += t.value
                if t.unit_id:
                    sales_by_month[mes].append(t)
            elif t.category == "Distrato":
                distratos += abs(t.value)
                
        elif t.transaction_type == "INCOME":
            recebimentos += t.value
            if ano != "N/A":
                anual_cf[ano]["Entradas"] += t.value
                
        elif t.transaction_type == "OUTCOME":
            cat = t.category.lower() if t.category else ""
            val = abs(t.value)
            
            if ano != "N/A":
                anual_cf[ano]["Saidas"] += val
                
            if "imposto" in cat or "tributo" in cat or "irpj" in cat or "csll" in cat or "pis" in cat or "cofins" in cat:
                impostos += val
                if ano != "N/A": anual_cf[ano]["Tributos"] += val
            elif "terreno" in cat:
                terreno += val
                if ano != "N/A": anual_cf[ano]["Obras"] += val
            elif "marketing" in cat or "publicidade" in cat:
                comercial_mkt += val
                if ano != "N/A": anual_cf[ano]["Marketing"] += val
            elif "comercial" in cat or "venda" in cat or "comiss" in cat:
                comercial_mkt += val
                if ano != "N/A": anual_cf[ano]["Comercial"] += val
            elif "adm" in cat or "despesa" in cat or "escritório" in cat:
                administrativas += val
            elif "projeto" in cat:
                obras += val # Agrupando projetos em obras ou separado?
                if ano != "N/A": anual_cf[ano]["Projetos"] += val
            else:
                # Default para obras
                obras += val
                if ano != "N/A": anual_cf[ano]["Obras"] += val

    # Calcular preço médio dos ultimos 6 meses com vendas
    sorted_months = sorted(sales_by_month.keys(), reverse=True)
    last_6_months = sorted_months[:6]
    
    total_sales_value = 0.0
    total_sales_area = 0.0
    
    for m in last_6_months:
        for s in sales_by_month[m]:
            # precisamos da área da unidade
            if s.unit and s.unit.private_area > 0:
                total_sales_value += s.value
                total_sales_area += s.unit.private_area
                
    avg_price = (total_sales_value / total_sales_area) if total_sales_area > 0 else 0.0
    
    # Calcular VGV de Estoque
    available_units = db.query(Unit).filter_by(cost_center_id=cc_id, status="D").all()
    available_area = sum(u.private_area for u in available_units)
    vgv_estoque = available_area * avg_price
    
    print(f"VGV Vendido: {vgv_vendido}")
    print(f"Preço Médio (Ultimos {len(last_6_months)} meses c/ vendas): {avg_price} R$/m2")
    print(f"Estoque Disponível: {len(available_units)} unidades ({available_area} m2)")
    print(f"VGV Estoque: {vgv_estoque}")
    
    # DRE
    print("\n--- DRE ---")
    print(f"Receita Bruta (VGV): {vgv_vendido}")
    print(f"Distratos: {distratos}")
    print(f"Recebimentos: {recebimentos}")
    print(f"Impostos: {impostos}")
    print(f"Obras: {obras}")
    print(f"Terreno: {terreno}")
    print(f"Comercial/MKT: {comercial_mkt}")
    print(f"Administrativas: {administrativas}")
    print(f"Resultado Operacional (Caixa): {recebimentos - impostos - obras - terreno - comercial_mkt - administrativas}")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        cc = db.query(CostCenter).filter_by(id_sienge=14100).first()
        if cc:
            calc_cost_center_actuals(db, cc.id)
    finally:
        db.close()
