from app.models import user, viability, phase, revenue, construction, expenses, phase_details, snapshot, company, custom_field, cost_center, financial_plan, scenario, economic_indicator, tax_regime, actual_transaction, payment_plan, departamento
from app.models.vision import Vision
from app.models import partnership as pm, migration as mm
from app.models.orcamento import Orcamento, OrcamentoVendaItem
from app.models.forecast import Forecast, ForecastVendaItem
from app.models.cost_center import CostCenter
from app.db.database import SessionLocal
from sqlalchemy import func

db = SessionLocal()

def cc_nome(cc_id):
    cc = db.query(CostCenter).filter_by(id=cc_id).first()
    return cc.nome if cc else "DESCONHECIDO"

print("=== VERIFICACAO VERSOES E NOMENCLATURA ===")
orcs = db.query(Orcamento).filter_by(ano=2026, tipo='VENDAS').all()
for o in orcs:
    print(f"  ORC [{o.id}] descricao={o.descricao!r} status={o.status}")

fcs = db.query(Forecast).filter_by(ano=2026, tipo='VENDAS').all()
for f in fcs:
    print(f"  FC  [{f.id}] descricao={f.descricao!r} status={f.status} mes_corte={f.mes_corte}")

print()
print("=== ITENS SEM TICKET MEDIO (numero_vendas != 0) ===")
for o in orcs:
    sem_tk = db.query(OrcamentoVendaItem).filter(
        OrcamentoVendaItem.orcamento_id==o.id,
        OrcamentoVendaItem.numero_vendas != 0,
        OrcamentoVendaItem.ticket_medio == 0
    ).all()
    if sem_tk:
        print(f"  ORC [{o.id}] {o.descricao}: {len(sem_tk)} itens sem ticket:")
        for i in sem_tk:
            print(f"    mes={i.mes} produto={cc_nome(i.produto_id)} qtd={i.numero_vendas}")

for f in fcs:
    sem_tk = db.query(ForecastVendaItem).filter(
        ForecastVendaItem.forecast_id==f.id,
        ForecastVendaItem.numero_vendas != 0,
        ForecastVendaItem.ticket_medio == 0
    ).all()
    if sem_tk:
        print(f"  FC  [{f.id}] {f.descricao}: {len(sem_tk)} itens sem ticket:")
        for i in sem_tk[:3]:
            print(f"    mes={i.mes} produto={cc_nome(i.produto_id)} qtd={i.numero_vendas}")
        if len(sem_tk) > 3:
            print(f"    ... e mais {len(sem_tk)-3}")

print()
print("=== CLASSIFICACAO ORCAMENTO vs FORECAST (Cross-check) ===")
erros_class = 0
for o in orcs:
    if 'forecast' in (o.descricao or '').lower():
        print(f"  ALERTA! Orcamento com descricao de Forecast: [{o.id}] {o.descricao}")
        erros_class += 1
for f in fcs:
    if '1\u00aa vers\u00e3o' in (f.descricao or '').lower():
        print(f"  ALERTA! Forecast com descricao de Orcamento: [{f.id}] {f.descricao}")
        erros_class += 1
if erros_class == 0:
    print("  OK! Nenhum cruzamento de classificacao detectado.")

print()
print("=== CONSISTENCIA VGV = Qtd x Ticket ===")
inconsistentes = 0
for o in orcs:
    itens = db.query(OrcamentoVendaItem).filter_by(orcamento_id=o.id).all()
    for i in itens:
        if i.ticket_medio > 0:
            expected = abs(i.numero_vendas) * i.ticket_medio
            actual = abs(i.vgv)
            if abs(expected - actual) > 1.0:
                inconsistentes += 1
                print(f"  ORC INCONSISTENTE: [{o.id}] mes={i.mes} prod={cc_nome(i.produto_id)} qtd={i.numero_vendas} ticket={i.ticket_medio:.0f} vgv={i.vgv:.0f} esperado={expected:.0f}")

for f in fcs:
    itens = db.query(ForecastVendaItem).filter_by(forecast_id=f.id).all()
    for i in itens:
        if i.ticket_medio > 0:
            expected = abs(i.numero_vendas) * i.ticket_medio
            actual = abs(i.vgv)
            if abs(expected - actual) > 1.0:
                inconsistentes += 1
                if inconsistentes <= 5:
                    print(f"  FC INCONSISTENTE: [{f.id}] mes={i.mes} prod={cc_nome(i.produto_id)} qtd={i.numero_vendas} ticket={i.ticket_medio:.0f} vgv={i.vgv:.0f} esperado={expected:.0f}")

if inconsistentes == 0:
    print("  OK! Todos os VGVs sao consistentes com Qtd x Ticket.")
else:
    print(f"  TOTAL INCONSISTENCIAS: {inconsistentes}")

print()
print("=== SINAIS (Positivo/Negativo) ===")
orc = orcs[-1] if orcs else None
if orc:
    venda_pos = db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id==orc.id, OrcamentoVendaItem.numero_vendas > 0, OrcamentoVendaItem.vgv < 0).count()
    dist_pos  = db.query(OrcamentoVendaItem).filter(OrcamentoVendaItem.orcamento_id==orc.id, OrcamentoVendaItem.numero_vendas < 0, OrcamentoVendaItem.vgv > 0).count()
    if venda_pos > 0:
        print(f"  ALERTA ORC: {venda_pos} vendas (qtd+) com VGV negativo!")
    if dist_pos > 0:
        print(f"  ALERTA ORC: {dist_pos} distratos (qtd-) com VGV positivo!")
    if venda_pos == 0 and dist_pos == 0:
        print(f"  OK! Sinais de VGV e Qtd estao coerentes no orcamento.")

for f in fcs[:2]:
    venda_pos = db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id==f.id, ForecastVendaItem.numero_vendas > 0, ForecastVendaItem.vgv < 0).count()
    dist_pos  = db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id==f.id, ForecastVendaItem.numero_vendas < 0, ForecastVendaItem.vgv > 0).count()
    if venda_pos > 0:
        print(f"  ALERTA FC [{f.id}] {f.descricao}: {venda_pos} vendas com VGV negativo!")
    if dist_pos > 0:
        print(f"  ALERTA FC [{f.id}] {f.descricao}: {dist_pos} distratos com VGV positivo!")
    if venda_pos == 0 and dist_pos == 0:
        print(f"  OK! Sinais do Forecast [{f.id}] {f.descricao} estao coerentes.")

db.close()
