from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api import deps
from app.models.user import User
from app.models.viability import Viability
from app.models.phase import Phase
from app.models.revenue import ViabilityRevenue
from app.models.construction import ViabilityConstruction
from app.models.expenses import ViabilityExpenses
from app.models.phase_details import (
    PhaseTaxes, PhaseExchanges, PhaseFunding, PhasePhysicalData, PhaseDates
)
from app.models.curves import PhaseCurve
from app.schemas.viability import ViabilityCreate, ViabilityUpdate, ViabilityResponse
from app.schemas.phase import PhaseResponse, PhaseCreate
from app.schemas.curves import PhaseCurvesUpdate, PhaseCurveResponse
from app.schemas.revenue import ViabilityRevenueUpdate, ViabilityRevenueResponse
from app.schemas.construction import PhaseConstructionUpdate, PhaseConstructionResponse
from app.schemas.expenses import PhaseExpensesUpdate, PhaseExpensesResponse
from app.schemas.phase_details import (
    PhaseTaxesUpdate, PhaseTaxesResponse, 
    PhaseExchangesUpdate, PhaseExchangesResponse, 
    PhaseFundingUpdate, PhaseFundingResponse,
    PhasePhysicalDataUpdate, PhasePhysicalDataResponse,
    PhaseDatesUpdate, PhaseDatesResponse
)

router = APIRouter()

# ---- VIABILITIES (Capa) ----

from typing import Optional

@router.get("/", response_model=List[ViabilityResponse])
def read_viabilities(
    status: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    query = db.query(Viability).options(joinedload(Viability.versions)).filter(
        Viability.version_of_id == None
    )
    if status:
        query = query.filter(Viability.status == status)
    return query.all()

@router.get("/{id}", response_model=ViabilityResponse)
def read_viability(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
    return viability

@router.put("/{id}", response_model=ViabilityResponse)
def update_viability(
    *,
    id: int,
    db: Session = Depends(deps.get_db),
    viability_in: ViabilityUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
    
    update_data = viability_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(viability, field, value)
        
    db.add(viability)
    db.commit()
    db.refresh(viability)
    return viability

from pydantic import BaseModel
class ViabilityStatusUpdate(BaseModel):
    status: str

@router.put("/{id}/status", response_model=ViabilityResponse)
def update_viability_status(
    *,
    id: int,
    db: Session = Depends(deps.get_db),
    status_in: ViabilityStatusUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
    
    valid_statuses = ["Em Andamento", "Em Aprovação", "Aprovado"]
    if status_in.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Status inválido.")
        
    viability.status = status_in.status
    db.add(viability)
    db.commit()
    db.refresh(viability)
    return viability


@router.post("/", response_model=ViabilityResponse)
def create_viability(
    *,
    db: Session = Depends(deps.get_db),
    viability_in: ViabilityCreate,
    current_user: User = Depends(deps.get_current_analista_user),
) -> Any:
    # 1. Cria a capa
    viability = Viability(**viability_in.model_dump())
    db.add(viability)
    db.commit()
    db.refresh(viability)
    
    # 2. Inicializa a Fase Padrão
    phase = Phase(viability_id=viability.id, name="Fase Única")
    db.add(phase)
    db.commit()
    db.refresh(phase)
    
    # 3. Inicializa as abas vazias atreladas à fase
    revenue = ViabilityRevenue(phase_id=phase.id)
    construction = ViabilityConstruction(phase_id=phase.id)
    expenses = ViabilityExpenses(phase_id=phase.id)
    taxes = PhaseTaxes(phase_id=phase.id)
    exchanges = PhaseExchanges(phase_id=phase.id)
    funding = PhaseFunding(phase_id=phase.id)
    physical_data = PhasePhysicalData(phase_id=phase.id)
    dates = PhaseDates(phase_id=phase.id)
    db.add_all([revenue, construction, expenses, taxes, exchanges, funding, physical_data, dates])
    db.commit()
    
    return viability

@router.delete("/{id}")
def delete_viability(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
    db.delete(viability)
    db.commit()
    return {"ok": True}

from datetime import datetime

from pydantic import BaseModel

class CloneRequest(BaseModel):
    custom_name: str | None = None

@router.post("/{id}/clone", response_model=ViabilityResponse)
def clone_viability(
    id: int,
    req: CloneRequest | None = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_analista_user),
) -> Any:
    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
    
    # 1. Clone Viability Capa
    base_name = req.custom_name.strip() if req and req.custom_name and req.custom_name.strip() else viability.project_name
    final_name = f"{datetime.now().strftime('%d/%m/%Y')} - {base_name}"
    
    new_viability = Viability(
        project_name=final_name,
        status="Em Andamento",
        version_of_id=viability.id,
        tem_multiplas_fases=viability.tem_multiplas_fases,
        aplicar_ipca_receitas=viability.aplicar_ipca_receitas,
        aplicar_ipca_despesas=viability.aplicar_ipca_despesas,
        aplicar_incc_obras=viability.aplicar_incc_obras,
        aplicar_ipca_projetos=viability.aplicar_ipca_projetos,
        aplicar_ipca_aquisicao=viability.aplicar_ipca_aquisicao,
        aplicar_ipca_adm=viability.aplicar_ipca_adm,
        taxa_desconto_vpl=viability.taxa_desconto_vpl,
        parecer_executivo=viability.parecer_executivo,
        parecer_original_ia=viability.parecer_original_ia
    )
    db.add(new_viability)
    db.commit()
    db.refresh(new_viability)
    
    # 2. Clone Fases e Abas
    for old_phase in viability.phases:
        new_phase = Phase(
            viability_id=new_viability.id,
            name=old_phase.name,
            curva_vendas_id=old_phase.curva_vendas_id,
            curva_obras_id=old_phase.curva_obras_id
        )
        db.add(new_phase)
        db.flush()
        db.refresh(new_phase)
        
        # Helper to clone 1:1 relations
        def clone_relation(model_class, old_instance):
            if not old_instance:
                return model_class(phase_id=new_phase.id)
            data = {k: v for k, v in old_instance.__dict__.items() if k not in ['id', 'phase_id', '_sa_instance_state']}
            return model_class(phase_id=new_phase.id, **data)
        
        revenue = clone_relation(ViabilityRevenue, old_phase.revenue)
        construction = clone_relation(ViabilityConstruction, old_phase.construction)
        expenses = clone_relation(ViabilityExpenses, old_phase.expenses)
        taxes = clone_relation(PhaseTaxes, old_phase.taxes)
        exchanges = clone_relation(PhaseExchanges, old_phase.exchanges)
        funding = clone_relation(PhaseFunding, old_phase.funding)
        physical_data = clone_relation(PhasePhysicalData, old_phase.physical_data)
        dates = clone_relation(PhaseDates, old_phase.dates)
        
        db.add_all([revenue, construction, expenses, taxes, exchanges, funding, physical_data, dates])
        
        # Clone phase_curves (curvas dinâmicas com mês de início)
        for old_pc in old_phase.curves:
            new_pc = PhaseCurve(
                phase_id=new_phase.id,
                standard_curve_id=old_pc.standard_curve_id,
                mes_inicio=old_pc.mes_inicio
            )
            db.add(new_pc)
        
        db.flush()
        
    db.commit()
    return new_viability

@router.get("/{id}/scenarios")
def get_viability_scenarios(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get all scenarios belonging to the same project family."""
    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
    
    # Determine the root viability
    root_id = viability.version_of_id if viability.version_of_id else viability.id
    
    # Fetch root and all its versions
    family = db.query(Viability).filter(
        (Viability.id == root_id) | (Viability.version_of_id == root_id)
    ).order_by(Viability.created_at).all()
    
    return [
        {
            "id": v.id,
            "project_name": v.project_name,
            "status": v.status,
            "is_root": v.id == root_id
        }
        for v in family
    ]

# ---- FASES ----

@router.get("/{id}/phases", response_model=List[PhaseResponse])
def read_phases(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    return db.query(Phase).filter(Phase.viability_id == id).all()

@router.post("/{viability_id}/phases", response_model=PhaseResponse)
def create_phase(
    *,
    db: Session = Depends(deps.get_db),
    viability_id: int,
    phase_in: PhaseCreate,
    current_user: User = Depends(deps.get_current_analista_user),
) -> Any:
    phase = Phase(viability_id=viability_id, **phase_in.model_dump())
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase

from app.schemas.phase import PhaseUpdate

@router.get("/phases/{phase_id}", response_model=PhaseResponse)
def read_phase(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Fase não encontrada.")
    return phase


@router.put("/phases/{phase_id}", response_model=PhaseResponse)
def update_phase(
    *,
    db: Session = Depends(deps.get_db),
    phase_id: int,
    phase_in: PhaseUpdate,
    current_user: User = Depends(deps.get_current_analista_user),
) -> Any:
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Fase não encontrada.")
    
    update_data = phase_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(phase, field, value)
        
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase

# ---- ABA 1: REVENUES (Receitas) vinculada a uma Fase ----

@router.get("/phases/{phase_id}/revenue", response_model=ViabilityRevenueResponse)
def read_phase_revenue(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    revenue = db.query(ViabilityRevenue).filter(ViabilityRevenue.phase_id == phase_id).first()
    if not revenue:
        revenue = ViabilityRevenue(phase_id=phase_id)
        db.add(revenue)
        db.commit()
        db.refresh(revenue)
    
    physical = db.query(PhasePhysicalData).filter(PhasePhysicalData.phase_id == phase_id).first()
    if physical:
        vgv_residencial = (physical.area_lotes_residenciais or 0) * (physical.valor_venda_residencial_m2 or 0)
        vgv_comercial = (physical.area_lotes_comerciais or 0) * (physical.valor_venda_comercial_m2 or 0)
        vgv_misto = (physical.area_lotes_mistos or 0) * (physical.valor_venda_misto_m2 or 0)
        revenue.vgv_total = vgv_residencial + vgv_comercial + vgv_misto
    
    return revenue

@router.put("/phases/{phase_id}/revenue", response_model=ViabilityRevenueResponse)
def update_phase_revenue(
    *,
    phase_id: int,
    db: Session = Depends(deps.get_db),
    revenue_in: ViabilityRevenueUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    revenue = db.query(ViabilityRevenue).filter(ViabilityRevenue.phase_id == phase_id).first()
    if not revenue:
        revenue = ViabilityRevenue(phase_id=phase_id)
        db.add(revenue)
    
    update_data = revenue_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(revenue, field, value)
        
    db.add(revenue)
    db.commit()
    db.refresh(revenue)
    return revenue

# ---- ABA 2: OBRAS (Construção) vinculada a uma Fase ----

@router.get("/phases/{phase_id}/construction", response_model=PhaseConstructionResponse)
def read_phase_construction(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    construction = db.query(ViabilityConstruction).filter(ViabilityConstruction.phase_id == phase_id).first()
    if not construction:
        raise HTTPException(status_code=404, detail="Aba de obras não encontrada.")
    return construction

@router.put("/phases/{phase_id}/construction", response_model=PhaseConstructionResponse)
def update_phase_construction(
    *,
    phase_id: int,
    db: Session = Depends(deps.get_db),
    construction_in: PhaseConstructionUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    construction = db.query(ViabilityConstruction).filter(ViabilityConstruction.phase_id == phase_id).first()
    if not construction:
        construction = ViabilityConstruction(phase_id=phase_id, **construction_in.dict(exclude_unset=True))
        db.add(construction)
    else:
        update_data = construction_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(construction, field, value)
    
    db.commit()
    db.refresh(construction)
    return construction

# ---- ABA 3: DESPESAS (Expenses) vinculada a uma Fase ----

@router.get("/phases/{phase_id}/expenses", response_model=PhaseExpensesResponse)
def read_phase_expenses(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    expenses = db.query(ViabilityExpenses).filter(ViabilityExpenses.phase_id == phase_id).first()
    if not expenses:
        raise HTTPException(status_code=404, detail="Aba de despesas não encontrada.")
    return expenses

@router.put("/phases/{phase_id}/expenses", response_model=PhaseExpensesResponse)
def update_phase_expenses(
    *,
    phase_id: int,
    db: Session = Depends(deps.get_db),
    expenses_in: PhaseExpensesUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    expenses = db.query(ViabilityExpenses).filter(ViabilityExpenses.phase_id == phase_id).first()
    
    if not expenses:
        expenses = ViabilityExpenses(phase_id=phase_id, **expenses_in.model_dump(exclude_unset=True))
        db.add(expenses)
    else:
        update_data = expenses_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(expenses, field, value)
        
    db.commit()
    db.refresh(expenses)
    return expenses

# ---- ABA 4: IMPOSTOS (Taxes) ----
@router.get("/phases/{phase_id}/taxes", response_model=PhaseTaxesResponse)
def read_phase_taxes(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    taxes = db.query(PhaseTaxes).filter(PhaseTaxes.phase_id == phase_id).first()
    if not taxes:
        taxes = PhaseTaxes(phase_id=phase_id)
        db.add(taxes)
        db.commit()
        db.refresh(taxes)
    return taxes

@router.put("/phases/{phase_id}/taxes", response_model=PhaseTaxesResponse)
def update_phase_taxes(
    *,
    phase_id: int,
    db: Session = Depends(deps.get_db),
    taxes_in: PhaseTaxesUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    taxes = db.query(PhaseTaxes).filter(PhaseTaxes.phase_id == phase_id).first()
    if not taxes:
        taxes = PhaseTaxes(phase_id=phase_id, **taxes_in.model_dump(exclude_unset=True))
        db.add(taxes)
    else:
        for field, value in taxes_in.model_dump(exclude_unset=True).items():
            setattr(taxes, field, value)
        db.add(taxes)
    db.commit()
    db.refresh(taxes)
    return taxes

# ---- ABA 5: PERMUTAS (Exchanges) ----
@router.get("/phases/{phase_id}/exchanges", response_model=PhaseExchangesResponse)
def read_phase_exchanges(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    exchanges = db.query(PhaseExchanges).filter(PhaseExchanges.phase_id == phase_id).first()
    if not exchanges:
        exchanges = PhaseExchanges(phase_id=phase_id)
        db.add(exchanges)
        db.commit()
        db.refresh(exchanges)
    return exchanges

@router.put("/phases/{phase_id}/exchanges", response_model=PhaseExchangesResponse)
def update_phase_exchanges(
    *,
    phase_id: int,
    db: Session = Depends(deps.get_db),
    exchanges_in: PhaseExchangesUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    exchanges = db.query(PhaseExchanges).filter(PhaseExchanges.phase_id == phase_id).first()
    if not exchanges:
        exchanges = PhaseExchanges(phase_id=phase_id, **exchanges_in.model_dump(exclude_unset=True))
        db.add(exchanges)
    else:
        for field, value in exchanges_in.model_dump(exclude_unset=True).items():
            setattr(exchanges, field, value)
        db.add(exchanges)
    db.commit()
    db.refresh(exchanges)
    return exchanges

# ---- ABA 6: FUNDING (Financiamento) ----
@router.get("/phases/{phase_id}/funding", response_model=PhaseFundingResponse)
def read_phase_funding(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    funding = db.query(PhaseFunding).filter(PhaseFunding.phase_id == phase_id).first()
    if not funding:
        funding = PhaseFunding(phase_id=phase_id)
        db.add(funding)
        db.commit()
        db.refresh(funding)
    return funding

@router.put("/phases/{phase_id}/funding", response_model=PhaseFundingResponse)
def update_phase_funding(
    *,
    phase_id: int,
    db: Session = Depends(deps.get_db),
    funding_in: PhaseFundingUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    funding = db.query(PhaseFunding).filter(PhaseFunding.phase_id == phase_id).first()
    if not funding:
        funding = PhaseFunding(phase_id=phase_id, **funding_in.model_dump(exclude_unset=True))
        db.add(funding)
    else:
        for field, value in funding_in.model_dump(exclude_unset=True).items():
            setattr(funding, field, value)
        db.add(funding)
    db.commit()
    db.refresh(funding)
    return funding
# ---- PHYSICAL DATA ----

@router.get("/phases/{id}/physical_data", response_model=PhasePhysicalDataResponse)
def read_phase_physical_data(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    physical_data = db.query(PhasePhysicalData).filter(PhasePhysicalData.phase_id == id).first()
    if not physical_data:
        physical_data = PhasePhysicalData(phase_id=id)
        db.add(physical_data)
        db.commit()
        db.refresh(physical_data)
    return physical_data

@router.put("/phases/{id}/physical_data", response_model=PhasePhysicalDataResponse)
def update_phase_physical_data(
    *,
    id: int,
    db: Session = Depends(deps.get_db),
    physical_data_in: PhasePhysicalDataUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    physical_data = db.query(PhasePhysicalData).filter(PhasePhysicalData.phase_id == id).first()
    if not physical_data:
        raise HTTPException(status_code=404, detail="Dados Físicos não encontrados.")
    
    update_data = physical_data_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(physical_data, field, value)
        
    db.add(physical_data)
    db.commit()
    db.refresh(physical_data)
    return physical_data

# ---- CURVAS DINÂMICAS DA FASE ----

@router.get("/phases/{phase_id}/curves", response_model=List[PhaseCurveResponse])
def read_phase_curves(
    phase_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retorna todas as curvas vinculadas a esta fase, com seus meses de início."""
    return db.query(PhaseCurve).filter(PhaseCurve.phase_id == phase_id).all()

@router.put("/phases/{phase_id}/curves", response_model=List[PhaseCurveResponse])
def update_phase_curves(
    *,
    phase_id: int,
    db: Session = Depends(deps.get_db),
    payload: PhaseCurvesUpdate,
    current_user: User = Depends(deps.get_current_analista_user),
) -> Any:
    """Substitui todas as curvas da fase de uma vez (estratégia delete+insert)."""
    phase = db.query(Phase).filter(Phase.id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Fase não encontrada.")
    
    # Remove curvas antigas
    db.query(PhaseCurve).filter(PhaseCurve.phase_id == phase_id).delete()
    
    # Insere as novas
    new_records = []
    for item in payload.curves:
        pc = PhaseCurve(
            phase_id=phase_id,
            standard_curve_id=item.standard_curve_id,
            mes_inicio=item.mes_inicio
        )
        db.add(pc)
        new_records.append(pc)
    
    db.commit()
    for pc in new_records:
        db.refresh(pc)
    
    return new_records

# ---- RESULTADOS MATEMÁTICOS ----
from app.services.math_engine import calculate_viability_results

@router.get("/phases/{phase_id}/results")
def read_phase_results(
    phase_id: int,
    scenario_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    results = calculate_viability_results(db, phase_id, scenario_id)
    if "error" in results:
        raise HTTPException(status_code=404, detail=results["error"])
    return results


# ---- DATES ----

@router.get("/phases/{id}/dates", response_model=PhaseDatesResponse)
def read_phase_dates(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    dates = db.query(PhaseDates).filter(PhaseDates.phase_id == id).first()
    if not dates:
        dates = PhaseDates(phase_id=id)
        db.add(dates)
        db.commit()
        db.refresh(dates)
    return dates

@router.put("/phases/{id}/dates", response_model=PhaseDatesResponse)
def update_phase_dates(
    *,
    id: int,
    db: Session = Depends(deps.get_db),
    dates_in: PhaseDatesUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    dates = db.query(PhaseDates).filter(PhaseDates.phase_id == id).first()
    if not dates:
        raise HTTPException(status_code=404, detail="Datas não encontradas.")
    
    update_data = dates_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dates, field, value)
        
    db.add(dates)
    db.commit()
    db.refresh(dates)
    
    # Auto-update offsets in curves
    date_strs = [
        dates.data_registro, dates.data_lancamento, dates.data_inicio_obras,
        dates.data_inicio_projetos, dates.data_inicio_aquisicao, dates.data_inicio_comercial, dates.data_inicio_mkt
    ]
    date_strs = [d for d in date_strs if d]
    base_date = None
    if date_strs:
        from datetime import datetime
        parsed_dates = []
        for d in date_strs:
            try:
                parsed_dates.append(datetime.strptime(d, '%Y-%m-%d'))
            except:
                pass
        if parsed_dates:
            base_date = min(parsed_dates)
            
    if base_date:
        def get_offset(target_date_str):
            if not target_date_str: return 1
            try:
                target = datetime.strptime(target_date_str, '%Y-%m-%d')
                months = (target.year - base_date.year) * 12 + (target.month - base_date.month)
                return max(1, months + 1)
            except:
                return 1
                
        # 1. Update Construction Curves
        from app.models.construction import ViabilityConstruction
        import json
        construction = db.query(ViabilityConstruction).filter(ViabilityConstruction.phase_id == id).first()
        if construction:
            changed = False
            if dates.data_inicio_obras and construction.curva_obras_json:
                c_data = json.loads(construction.curva_obras_json) if isinstance(construction.curva_obras_json, str) else construction.curva_obras_json
                if isinstance(c_data, dict):
                    c_data['mes_inicio'] = get_offset(dates.data_inicio_obras)
                    construction.curva_obras_json = c_data
                    changed = True
                    
            if dates.data_inicio_projetos and construction.curva_projetos_json:
                c_data = json.loads(construction.curva_projetos_json) if isinstance(construction.curva_projetos_json, str) else construction.curva_projetos_json
                if isinstance(c_data, dict):
                    c_data['mes_inicio'] = get_offset(dates.data_inicio_projetos)
                    construction.curva_projetos_json = c_data
                    changed = True
                    
            if dates.data_inicio_aquisicao and construction.curva_aquisicao_json:
                c_data = json.loads(construction.curva_aquisicao_json) if isinstance(construction.curva_aquisicao_json, str) else construction.curva_aquisicao_json
                if isinstance(c_data, dict):
                    c_data['mes_inicio'] = get_offset(dates.data_inicio_aquisicao)
                    construction.curva_aquisicao_json = c_data
                    changed = True
                    
            if changed: db.add(construction)
            
        # 2. Update Revenue Curves
        from app.models.revenue import ViabilityRevenue
        revenue = db.query(ViabilityRevenue).filter(ViabilityRevenue.phase_id == id).first()
        if revenue and dates.data_lancamento and revenue.velocidade_vendas_json:
            r_data = json.loads(revenue.velocidade_vendas_json) if isinstance(revenue.velocidade_vendas_json, str) else revenue.velocidade_vendas_json
            if isinstance(r_data, dict):
                r_data['mes_inicio'] = get_offset(dates.data_lancamento)
                revenue.velocidade_vendas_json = r_data
                db.add(revenue)
                
        # 3. Update Expenses Curves
        from app.models.expenses import ViabilityExpenses
        expenses = db.query(ViabilityExpenses).filter(ViabilityExpenses.phase_id == id).first()
        if expenses:
            changed = False
            if dates.data_inicio_mkt and expenses.curva_marketing_json:
                e_data = json.loads(expenses.curva_marketing_json) if isinstance(expenses.curva_marketing_json, str) else expenses.curva_marketing_json
                if isinstance(e_data, dict):
                    e_data['mes_inicio'] = get_offset(dates.data_inicio_mkt)
                    expenses.curva_marketing_json = e_data
                    changed = True
            if dates.data_inicio_comercial and expenses.curva_comercial_json:
                e_data = json.loads(expenses.curva_comercial_json) if isinstance(expenses.curva_comercial_json, str) else expenses.curva_comercial_json
                if isinstance(e_data, dict):
                    e_data['mes_inicio'] = get_offset(dates.data_inicio_comercial)
                    expenses.curva_comercial_json = e_data
                    changed = True
            if changed: db.add(expenses)
            
        db.commit()

    return dates


# ---- AI SUMMARY GENERATION ----
import os
import json
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from pydantic import BaseModel

class GenerateSummaryRequest(BaseModel):
    api_key: Optional[str] = None

@router.post("/{id}/generate-summary")
def generate_viability_summary(
    id: int,
    request: GenerateSummaryRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    try:
        if genai is None:
            raise HTTPException(status_code=500, detail="A biblioteca do Google Gemini não está instalada no servidor.")

        viability = db.query(Viability).filter(Viability.id == id).first()
        if not viability:
            raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
            
        api_key = request.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="Chave de API do Gemini não configurada. Por favor, forneça a chave.")
            
        genai.configure(api_key=api_key)
        
        # Coletar dados dos cenários (phases) e snapshots se houver
        master = viability.original_viability if viability.version_of_id else viability
        all_viabilities = [master] + (master.versions if hasattr(master, 'versions') else [])
        
        cenarios_text = ""
        cenario_counter = 1
        
        from app.models.snapshot import PhaseSnapshot
        for v in all_viabilities:
            for phase in v.phases:
                nome_cenario = f"{v.project_name} - {phase.name}" if len(all_viabilities) > 1 else phase.name
                cenarios_text += f"\n--- Cenário {cenario_counter}: {nome_cenario} ---\n"
                
                # Tentar buscar o snapshot mais recente para pegar TIR e Payback
                snapshot = db.query(PhaseSnapshot).filter(PhaseSnapshot.phase_id == phase.id).order_by(PhaseSnapshot.created_at.desc()).first() if hasattr(PhaseSnapshot, 'phase_id') else None
                
                data = snapshot.snapshot_data if snapshot else None
                
                # Se não houver snapshot, calculamos na hora
                if not data:
                    from app.services.math_engine import calculate_viability_results
                    math_results = calculate_viability_results(db, phase.id)
                    if "error" not in math_results:
                        data = math_results
                
                if not data:
                    # Como fallback final, colocamos os dados estáticos
                    cenarios_text += f"Resumo financeiro não encontrado para esta fase/cenário.\n"
                else:
                    # Tentamos extrair os indicadores para o prompt
                    if isinstance(data, dict):
                        inds = data.get("indicators", {}) or data.get("global_indicators", {})
                        totals = data.get("totals", {}) or data.get("global_totals", {})
                        
                        if totals: cenarios_text += f"Totais do Cenário (VGV, Obras, Despesas, etc): {json.dumps(totals)}\n"
                        if inds: cenarios_text += f"Indicadores Financeiros da Visão Global (TIR, Payback, Margem, etc): {json.dumps(inds)}\n"
                        
                        inds_emp = data.get("indicators_empreendedor", {})
                        if inds_emp: cenarios_text += f"Indicadores da Visão Empreendedor: {json.dumps(inds_emp)}\n"
                        
                        inds_parc = data.get("indicators_parceiros", {})
                        if inds_parc: cenarios_text += f"Indicadores das Visões dos Parceiros/Terrenistas: {json.dumps(inds_parc)}\n"
                    else:
                        cenarios_text += f"Dados não estruturados.\n"
                
                cenario_counter += 1
                
        # Prompt mais elaborado
        prompt = f"""Você é um diretor financeiro especialista em loteamentos urbanos (como a Moura Leite Loteamentos).
O usuário precisa de um Parecer Técnico / Resumo Executivo para abrir o Relatório de Viabilidade do projeto {viability.project_name}.

O estudo possui múltiplos cenários (fases). Analise os dados fornecidos (os totais de obras, despesas, VGV e os indicadores financeiros como TIR, Payback) e crie um texto contendo exatamente a seguinte ordem:

1. Resumo executivo (Análise dos Números): Inicie fazendo uma análise comparativa e detalhada dos grandes números (VGV, Custo de Obras, Despesas e Margem) e avaliando a Exposição de Caixa e o Payback. Indique as principais diferenças entre os cenários.
2. Tabela de Leitura sugerida (Visão Global) comparando os totais e indicadores de cada cenário.
3. Racional de cada cenário e Riscos qualitativos.
4. Análise das Visões (Empreendedor e Parceiros): Apenas se houver dados de parceiros/terrenistas, adicione no final do parecer uma nova tabela (nos mesmos moldes da tabela Global) exibindo exclusivamente os indicadores da ótica de cada participante no negócio, seguida de uma breve análise sobre o equilíbrio da parceria.
5. Sugestões de Melhoria e Recomendação Final: Com base na análise numérica e qualitativa acima, identifique a melhor estratégia de execução e comercialização, ponderando rentabilidade, necessidade de capital e mitigação de riscos operacionais. Forneça sugestões práticas de como melhorar o cenário escolhido.

Seja extremamente profissional, use formatação Markdown (com headers h3 e tabelas se necessário).
Não escreva saudações nem encerramentos, apenas o texto do relatório.

Dados de Entrada:
{cenarios_text}
"""
        
        try:
            available_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao listar modelos: {str(e)}")
            
        if not available_models:
            raise HTTPException(status_code=400, detail="Nenhum modelo de geração de texto disponível para esta chave de API.")
            
        # Prioriza modelos "flash" (mais rápidos/baratos), depois "pro", e tenta o resto se tudo falhar
        flash_models = [m for m in available_models if "flash" in m.lower()]
        pro_models = [m for m in available_models if "pro" in m.lower() and m not in flash_models]
        other_models = [m for m in available_models if m not in flash_models and m not in pro_models]
        
        models_to_try = flash_models + pro_models + other_models
        
        response = None
        errors = []
        
        # Tenta gerar o conteúdo iterando sobre os modelos disponíveis
        for m_name in models_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt)
                break # Sucesso, sai do loop
            except Exception as e:
                # Simplifica o erro para caber na tela
                error_str = str(e).split(']')[0] + ']' if ']' in str(e) else str(e)
                errors.append(f"[{m_name}: {error_str}]")
                continue # Tenta o próximo modelo
                
        if not response:
            error_msg = " ".join(errors)
            raise HTTPException(status_code=400, detail=f"Falha ao gerar o resumo. Todos os modelos tentados falharam. Detalhes: {error_msg}")
            
        # Adiciona a nota de rodapé e remove da parte original para não sujar a comparação
        final_text = response.text
        
        # Salva no banco de dados como o texto original da IA
        viability.parecer_original_ia = final_text
        db.commit()
        
        return {"summary": final_text}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar a IA: {str(e)}")
