import pandas as pd
from app.db.database import SessionLocal
from app.models.phase import Phase
from app.services.math_engine import calculate_cash_flow_and_indicators

db = SessionLocal()
phase = db.query(Phase).filter(Phase.id == 6).first()
if phase:
    res = calculate_cash_flow_and_indicators(db, phase)
    df = pd.DataFrame(res["monthly_cashflow"])
    # Export to Excel
    export_path = "../bases/Fluxo_de_Caixa_ERP_Fase6.xlsx"
    df.to_excel(export_path, index=True, index_label="Mês")
    print(f"Exportado com sucesso para {export_path}")
else:
    print("Fase não encontrada")
