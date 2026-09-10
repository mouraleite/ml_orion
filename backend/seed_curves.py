import json
import math
from app.db.database import SessionLocal
from app.models.curves import StandardCurve

def generate_s_curve(months=36):
    """
    Gera uma Curva S baseada na função logística.
    """
    curve = []
    total = 0
    k = 0.3 # Fator de inclinação
    x0 = months / 2 # Ponto médio
    
    for i in range(1, months + 1):
        # Derivada da função logística (distribuição do esforço no mês)
        val = (math.exp(-k * (i - x0))) / ((1 + math.exp(-k * (i - x0))) ** 2)
        curve.append(val)
        total += val
        
    # Normaliza para que a soma seja exatamente 1.0 (100%)
    return [v / total for v in curve]

def generate_bell_curve(months=36):
    """
    Gera uma Curva de Sino (Gaussiana).
    """
    curve = []
    total = 0
    mean = months / 3 # Pico ocorre no primeiro terço (lançamento)
    std_dev = months / 5
    
    for i in range(1, months + 1):
        val = (1 / (std_dev * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((i - mean) / std_dev) ** 2)
        curve.append(val)
        total += val
        
    return [v / total for v in curve]

def seed_curves():
    db = SessionLocal()
    
    # Verifica se já existe
    existing = db.query(StandardCurve).first()
    if existing:
        print("Curvas já existem no banco de dados.")
        db.close()
        return

    s_curve_36 = generate_s_curve(36)
    bell_curve_36 = generate_bell_curve(36)
    
    c1 = StandardCurve(
        nome="Curva S (36 meses) - Obras Padrão",
        tipo="obras",
        valores_meses_json={"meses": s_curve_36}
    )
    
    c2 = StandardCurve(
        nome="Curva de Sino (36 meses) - Lançamento Acelerado",
        tipo="vendas",
        valores_meses_json={"meses": bell_curve_36}
    )
    
    db.add_all([c1, c2])
    db.commit()
    print("Curvas injetadas com sucesso!")
    db.close()

if __name__ == "__main__":
    seed_curves()
