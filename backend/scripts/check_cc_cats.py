from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Verificar a tabela actual_transactions para dados de plano de pagamento
print("=== TRANSACTIONS MAIS RECENTES CC 206 ===")
result = db.execute(text(
    "SELECT transaction_type, category, transaction_date, value FROM actual_transactions WHERE cost_center_id=206 ORDER BY transaction_date DESC LIMIT 20"
)).fetchall()
for r in result:
    print(r)

# Ver se temos tabela de contas a receber ou parcelas
print("\n=== TABELAS COM 'parcel' OU 'receber' OU 'pagar' ===")
result2 = db.execute(text(
    "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%parcel%' OR name LIKE '%receber%' OR name LIKE '%pagar%' OR name LIKE '%recebivel%')"
)).fetchall()
for r in result2:
    print(r[0])
    
# Ver se planos financeiros tem parcelas 
print("\n=== COLUNAS PLANOS FINANCEIROS ===")
result3 = db.execute(text("PRAGMA table_info(planos_financeiros)")).fetchall()
for r in result3:
    print(r)
    
# Ver se fp_vision_links tem parcelas
print("\n=== COLUNAS FP_VISION_LINKS ===")
result4 = db.execute(text("PRAGMA table_info(fp_vision_links)")).fetchall()
for r in result4:
    print(r)
    
print("\n=== AMOSTRA FP_VISION_LINKS ===")
result5 = db.execute(text("SELECT * FROM fp_vision_links LIMIT 5")).fetchall()
for r in result5:
    print(r)
