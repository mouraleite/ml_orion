import re

with open(r'c:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\backend\app\api\routes\viabilities.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Models Import
content = re.sub(
    r'from app\.models\.phase_details import \(\n    PhaseTaxes, PhaseExchanges, PhaseFunding, PhasePhysicalData\n\)',
    'from app.models.phase_details import (\n    PhaseTaxes, PhaseExchanges, PhaseFunding, PhasePhysicalData, PhaseDates\n)',
    content
)

# 2. Update Schemas Import
content = re.sub(
    r'    PhasePhysicalDataUpdate, PhasePhysicalDataResponse\n\)',
    '    PhasePhysicalDataUpdate, PhasePhysicalDataResponse,\n    PhaseDatesUpdate, PhaseDatesResponse\n)',
    content
)

# 3. Update create_viability
content = re.sub(
    r'physical_data = PhasePhysicalData\(phase_id=phase\.id\)\n    db\.add_all\(\[revenue, construction, expenses, taxes, exchanges, funding, physical_data\]\)',
    'physical_data = PhasePhysicalData(phase_id=phase.id)\n    dates = PhaseDates(phase_id=phase.id)\n    db.add_all([revenue, construction, expenses, taxes, exchanges, funding, physical_data, dates])',
    content
)

# 4. Update clone_relation
content = re.sub(
    r'physical_data = clone_relation\(PhasePhysicalData, old_phase\.physical_data\)\n        \n        db\.add_all\(\[revenue, construction, expenses, taxes, exchanges, funding, physical_data\]\)',
    'physical_data = clone_relation(PhasePhysicalData, old_phase.physical_data)\n        dates = clone_relation(PhaseDates, old_phase.dates)\n        \n        db.add_all([revenue, construction, expenses, taxes, exchanges, funding, physical_data, dates])',
    content
)

# 5. Add endpoints at the bottom
endpoints = """
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
    return dates
"""

content += endpoints

with open(r'c:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\backend\app\api\routes\viabilities.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
