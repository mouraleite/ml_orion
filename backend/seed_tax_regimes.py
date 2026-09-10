from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.tax_regime import TaxRegime

db = SessionLocal()

regimes = [
    {
        "nome": "RET (Regime Especial de Tributação)",
        "pis": 0.37,
        "cofins": 1.71,
        "irpj": 1.26,
        "csll": 0.66,
        "outros": 0.00,
    },
    {
        "nome": "Lucro Presumido",
        "pis": 0.65,
        "cofins": 3.00,
        "irpj": 1.20,
        "csll": 1.08,
        "outros": 0.00,
    },
    {
        "nome": "Lucro Real",
        "pis": 1.65,
        "cofins": 7.60,
        "irpj": 0.00,
        "csll": 0.00,
        "outros": 0.00,
    }
]

for r in regimes:
    existing = db.query(TaxRegime).filter(TaxRegime.nome == r['nome']).first()
    if not existing:
        new_reg = TaxRegime(**r)
        db.add(new_reg)

db.commit()
print('Regimes adicionados com sucesso!')
