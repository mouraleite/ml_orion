import sys
import os
import json
from sqlalchemy import text

# Load environment first
from dotenv import load_dotenv
load_dotenv()

from app.db.database import engine
from app.models.system_settings import SystemSettings
from sqlalchemy.orm import Session

def seed_settings():
    default_rates = {
        "CVM": {
            "ICVM_400": 0.0005,
            "ICVM_476": 0.0003,
            "Mínimo": 809.16
        },
        "ANBIMA": {
            "Taxa_Registro": 0.000044,
            "Min_400": 15700,
            "Max_400": 109910,
            "Min_476": 1568,
            "Max_476": 3136
        },
        "B3": {
            "Registro": [
                {"max": 1000000000, "rate": 0.00001},
                {"max": 5000000000, "rate": 0.000008},
                {"max": 50000000, "rate": 0.000007},
                {"max": 250000000, "rate": 0.000005},
                {"max": 500000000, "rate": 0.000004},
                {"max": float('inf'), "rate": 0.000003}
            ],
            "Custodia": [
                {"max": 300000000, "rate": 0.000011},
                {"max": 1000000000, "rate": 0.00001},
                {"max": 3000000000, "rate": 0.000008},
                {"max": 10000000000, "rate": 0.000007},
                {"max": 100000000000, "rate": 0.000006},
                {"max": float('inf'), "rate": 0.000002}
            ]
        },
        "Securitizadoras": {
            "Vórtx (Não Guarda-Chuva)": {
                "Agente_Fiduciario_Implantacao": 16000,
                "Agente_Fiduciario_Recorrente": 10000,
                "Instituicao_Custodiante": 5000,
                "Registro_Lastro": 5000,
                "Liquidante": 500
            },
            "Oliveira Trust (Guarda-Chuva)": {
                "Agente_Fiduciario_Implantacao": 15000,
                "Agente_Fiduciario_Recorrente": 4000,
                "Instituicao_Custodiante": 5000,
                "Registro_Lastro": 5000,
                "Liquidante": 500
            },
            "Vórtx (Guarda-Chuva)": {
                "Agente_Fiduciario_Implantacao": 16000,
                "Agente_Fiduciario_Recorrente": 10000,
                "Instituicao_Custodiante": 0,
                "Registro_Lastro": 0,
                "Liquidante": 500
            }
        },
        "Prestador_GrossUp": {
            "Opea - Estruturação": 0.0965,
            "Opea - Administração": 0.1953,
            "Oliveira Trust": 0.1633,
            "Vórtx": 0.1633
        }
    }

    with Session(engine) as db:
        setting = db.query(SystemSettings).filter(SystemSettings.key == "funding_rates").first()
        if not setting:
            setting = SystemSettings(key="funding_rates", value=default_rates)
            db.add(setting)
        else:
            setting.value = default_rates
        db.commit()
        print("Rates seeded successfully.")

if __name__ == "__main__":
    seed_settings()
