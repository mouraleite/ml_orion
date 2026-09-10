import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.db.database import SessionLocal
from app.models.viability import Viability
from app.models.phase import Phase
from app.models.revenue import ViabilityRevenue
from app.models.construction import ViabilityConstruction
from app.models.expenses import ViabilityExpenses
from app.models.phase_details import PhaseTaxes, PhaseExchanges, PhaseFunding, PhasePhysicalData, PhaseDates

def run():
    db = SessionLocal()

    # Deletar qualquer viabilidade de teste anterior
    olds = db.query(Viability).filter(Viability.project_name.like('%VIABILIDADE STRESS TEST%')).all()
    for o in olds:
        db.delete(o)
    db.commit()

    # Criar Viabilidade
    v = Viability(project_name='VIABILIDADE STRESS TEST', tem_multiplas_fases=True, taxa_desconto_vpl=15.0, status='Em Andamento')
    db.add(v)
    db.commit()
    db.refresh(v)

    # -----------------------------------------------------
    # FASE 1
    # -----------------------------------------------------
    p1 = Phase(viability_id=v.id, name='Fase 1 - Lotes Mistos')
    db.add(p1)
    db.commit()
    db.refresh(p1)

    # Physical Data
    db.add(PhasePhysicalData(
        phase_id=p1.id, 
        area_total=40000,
        area_lotes_residenciais=20000,
        qtde_lotes_residenciais=100, 
        valor_venda_residencial_m2=750, 
        area_lotes_comerciais=4000,
        qtde_lotes_comerciais=20, 
        valor_venda_comercial_m2=1500
    ))
    
    # Revenue
    # VGV: Residencial (20000 * 750) = 15.000.000 | Comercial (4000 * 1500) = 6.000.000 | Total = 21.000.000
    db.add(ViabilityRevenue(
        phase_id=p1.id, 
        vgv_total=21000000,
        plano_ativo='Sinal + Mensais',
        condicoes_pagamento_json=[{"nome": "Sinal + Mensais", "condicoes": [{"nome": "Sinal", "perc": 10}, {"nome": "Mensais", "perc": 90}]}],
        velocidade_vendas_json={"mes_inicio": 4, "meses": [5.0]*20}
    ))

    # Construction
    db.add(ViabilityConstruction(
        phase_id=p1.id, 
        custo_obras=5000000, 
        custo_obras_tipo='R$',
        curva_obras_json={"mes_inicio": 1, "meses": [4.166]*24},
        extra_constructions_json=[{'nome': 'Licenças Extras', 'valor': 500000, 'tipo': 'R$', 'curva_json': {'mes_inicio': 1, 'meses': [10.0]*10}}]
    ))

    # Expenses
    db.add(ViabilityExpenses(
        phase_id=p1.id, 
        marketing_valor=3.0, 
        marketing_tipo='%', 
        comercial_valor=5.0, 
        comercial_tipo='%',
        curva_marketing_json={"mes_inicio": 1, "meses": [5.0]*20},
        curva_comercial_json={"mes_inicio": 4, "meses": [5.0]*20}
    ))

    # Taxes
    db.add(PhaseTaxes(phase_id=p1.id, regime_tributario='RET', aliquota_total=4.0))
    
    # Exchanges
    db.add(PhaseExchanges(
        phase_id=p1.id, 
        modalidade='Permuta Financeira', 
        perc_parceria_terrenista=35.0, 
        rateios_config_json={'vincular_permuta_parceria': True},
        abertura_terrenistas_json=[{'nome': 'Investidor', 'percentual': 15}, {'nome': 'João', 'percentual': 10}, {'nome': 'Maria', 'percentual': 10}]
    ))

    # Funding
    db.add(PhaseFunding(phase_id=p1.id, tipo_funding='CRI', modo_volume='fixo', volume_fixo=3000000, prazo_meses=12))
    
    # Dates
    db.add(PhaseDates(phase_id=p1.id, data_inicio_obras='2026-03-01', data_lancamento='2026-06-01'))

    # -----------------------------------------------------
    # FASE 2
    # -----------------------------------------------------
    p2 = Phase(viability_id=v.id, name='Fase 2 - Casas')
    db.add(p2)
    db.commit()
    db.refresh(p2)

    db.add(PhasePhysicalData(
        phase_id=p2.id, 
        area_total=20000,
        area_lotes_residenciais=10000,
        qtde_lotes_residenciais=50, 
        valor_venda_residencial_m2=2000
    ))
    
    # VGV: Casas = 10000 * 2000 = 20.000.000
    db.add(ViabilityRevenue(
        phase_id=p2.id, 
        vgv_total=20000000,
        plano_ativo='Sinal + Mensais',
        condicoes_pagamento_json=[{"nome": "Sinal + Mensais", "condicoes": [{"nome": "Sinal", "perc": 10}, {"nome": "Mensais", "perc": 90}]}],
        velocidade_vendas_json={"mes_inicio": 4, "meses": [10.0]*10}
    ))

    db.add(ViabilityConstruction(
        phase_id=p2.id, 
        custo_obras=8000000, 
        custo_obras_tipo='R$',
        curva_obras_json={"mes_inicio": 1, "meses": [8.333]*12}
    ))

    db.add(ViabilityExpenses(
        phase_id=p2.id, 
        marketing_valor=3.0, 
        marketing_tipo='%', 
        comercial_valor=5.0, 
        comercial_tipo='%',
        curva_marketing_json={"mes_inicio": 1, "meses": [10.0]*10},
        curva_comercial_json={"mes_inicio": 4, "meses": [10.0]*10}
    ))

    db.add(PhaseTaxes(phase_id=p2.id, regime_tributario='RET', aliquota_total=4.0))
    
    db.add(PhaseExchanges(
        phase_id=p2.id, 
        modalidade='Permuta Física', 
        permuta_fisica_unidades=5, 
        permuta_fisica_valor_unidade=400000
    ))

    db.add(PhaseFunding(phase_id=p2.id))
    
    db.add(PhaseDates(phase_id=p2.id, data_inicio_obras='2026-03-01', data_lancamento='2026-06-01'))

    db.commit()
    print(f'Sucesso! Criado projeto COMPLETO ID: {v.id}')

if __name__ == '__main__':
    run()
