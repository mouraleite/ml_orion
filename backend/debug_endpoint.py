from app.models import user, viability, phase, revenue, construction, expenses, phase_details, snapshot, company, custom_field, cost_center, financial_plan, scenario, economic_indicator, tax_regime, actual_transaction, payment_plan, departamento
from app.models.forecast import Forecast, ForecastVendaItem
from app.models.orcamento import Orcamento, OrcamentoVendaItem
from app.models.departamento import Departamento
from app.models.cost_center import CostCenter
from app.models.payment_plan import PaymentPlan
from app.models.fechamento import ClosedMonth
from app.db.database import SessionLocal
from sqlalchemy import or_
import traceback

db = SessionLocal()
try:
    dept = db.query(Departamento).filter_by(id=1).first()
    ano = 2026

    forecast = db.query(Forecast).filter(
        Forecast.ano == ano,
        Forecast.tipo == 'VENDAS',
        or_(Forecast.departamento_id == dept.id, Forecast.departamento_id == None)
    ).order_by(Forecast.versao_numero.desc()).first()

    print(f'forecast: {forecast.id} - {forecast.descricao}')
    print(f'  versao_base_orcamento_id: {forecast.versao_base_orcamento_id}')
    print(f'  versao_base_forecast_id:  {forecast.versao_base_forecast_id}')
    print(f'  usuario_edicao_id:        {forecast.usuario_edicao_id}')
    print(f'  data_inicio_edicao:       {forecast.data_inicio_edicao}')
    print(f'  motivo_reabertura:        {forecast.motivo_reabertura}')
    print(f'  data_criacao:             {forecast.data_criacao}')

    planos_venda = db.query(PaymentPlan).all()
    produtos = db.query(CostCenter).all()
    print(f'planos: {len(planos_venda)} | produtos: {len(produtos)}')

    itens_db = db.query(ForecastVendaItem).filter(ForecastVendaItem.forecast_id == forecast.id).all()
    print(f'itens: {len(itens_db)}')

    # Tenta serializar items
    linhas_dict = {}
    for item in itens_db:
        key = (item.produto_id, item.plano_venda_id)
        if key not in linhas_dict:
            linhas_dict[key] = {
                'produto_id': item.produto_id,
                'plano_venda_id': item.plano_venda_id,
                'observacao': item.observacao,
                'meses': []
            }
        linhas_dict[key]['meses'].append({
            'mes': item.mes,
            'ticket_medio': item.ticket_medio,
            'numero_vendas': item.numero_vendas,
            'vgv': item.vgv,
            'origem_venda': getattr(item, 'origem_venda', None)
        })

    print(f'linhas agrupadas: {len(linhas_dict)}')

    meses_fechados = [mf.mes for mf in db.query(ClosedMonth).filter(ClosedMonth.ano == ano).all()]
    print(f'meses_fechados: {meses_fechados}')

    # Simula o check de trava
    from datetime import datetime
    is_locked_by_other = False
    if getattr(forecast, 'usuario_edicao_id', None) and getattr(forecast, 'data_inicio_edicao', None):
        if (datetime.utcnow() - forecast.data_inicio_edicao).total_seconds() < 1800:
            is_locked_by_other = True

    # Monta resposta
    resp = {
        'forecast_id': forecast.id,
        'ano': forecast.ano,
        'tipo': forecast.tipo,
        'status': forecast.status,
        'versao_numero': forecast.versao_numero,
        'motivo_reabertura': forecast.motivo_reabertura,
        'data_criacao': forecast.data_criacao.isoformat() if forecast.data_criacao else None,
        'is_locked_by_other': is_locked_by_other,
        'usuario_edicao_nome': None,
        'is_consolidado': False,
        'meses_fechados': meses_fechados,
        'itens': list(linhas_dict.values()),
        'itens_base': [],
        'opcoes_produtos': [{'id': p.id, 'nome': p.nome} for p in produtos],
        'opcoes_planos': [{'id': p.id, 'nome': p.nome} for p in planos_venda],
    }
    print(f'RESPONSE OK! itens={len(resp["itens"])}')
except Exception as e:
    print(f'ERRO: {e}')
    traceback.print_exc()
finally:
    db.close()
