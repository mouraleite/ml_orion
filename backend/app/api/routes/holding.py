"""API da estrutura societária MLDU (Onda B)."""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.company import Company, CompanyOwnershipLink
from app.schemas.user import UserResponse
from app.services.mldu_ownership import (
    build_tree,
    child_has_other_parent,
    seed_reference_links,
    serialize_company_brief,
    sync_company_effective_percentages,
    would_create_cycle,
)
from app.services.mldu_ownership_periods import PeriodoInvalido, record_percentage_change

router = APIRouter()


class OwnershipLinkCreate(BaseModel):
    parent_company_id: int
    child_company_id: int
    percentage: float = Field(..., ge=0, le=100)
    consolidates: bool = True
    notes: Optional[str] = None


class OwnershipLinkUpdate(BaseModel):
    parent_company_id: Optional[int] = None
    percentage: Optional[float] = Field(None, ge=0, le=100)
    consolidates: Optional[bool] = None
    notes: Optional[str] = None
    valid_from: Optional[str] = None


class ParticipacaoManualUpdate(BaseModel):
    usa_participacao_manual: bool
    participacao_mldu_manual: Optional[float] = Field(None, ge=0, le=100)


def _get_link_or_404(db: Session, link_id: int) -> CompanyOwnershipLink:
    link = db.query(CompanyOwnershipLink).filter(CompanyOwnershipLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    return link


def _validate_link(db: Session, parent_id: int, child_id: int, percentage: float, exclude_link_id: int | None = None) -> None:
    parent = db.query(Company).filter(Company.id == parent_id).first()
    child = db.query(Company).filter(Company.id == child_id).first()
    if not parent or not child:
        raise HTTPException(status_code=404, detail="Empresa pai ou filha não encontrada.")
    if would_create_cycle(db, parent_id, child_id, exclude_link_id=exclude_link_id):
        raise HTTPException(status_code=400, detail="Vínculo criaria ciclo na árvore.")
    other = child_has_other_parent(db, child_id, exclude_link_id=exclude_link_id)
    if other and other.parent_company_id != parent_id:
        raise HTTPException(status_code=400, detail="Empresa filha já possui outro vínculo pai na árvore MLDU.")


@router.get("/fatores")
def get_holding_fatores(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mapa empresa/centro → fator MLDU (Onda C)."""
    from app.services.holding_consolidation import list_holding_factors

    return list_holding_factors(db)


@router.get("/estrutura-mldu")
def get_estrutura_mldu(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return build_tree(db)


@router.get("/ownership-links", response_model=List[dict])
def list_ownership_links(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[dict]:
    links = db.query(CompanyOwnershipLink).order_by(CompanyOwnershipLink.id.asc()).all()
    companies = {c.id: c for c in db.query(Company).all()}
    result = []
    for link in links:
        parent = companies.get(link.parent_company_id)
        child = companies.get(link.child_company_id)
        result.append(
            {
                "id": link.id,
                "parent_company_id": link.parent_company_id,
                "child_company_id": link.child_company_id,
                "parent_nome": (parent.nome_fantasia or parent.razao_social) if parent else "?",
                "child_nome": (child.nome_fantasia or child.razao_social) if child else "?",
                "percentage": link.percentage,
                "consolidates": link.consolidates,
                "notes": link.notes,
            }
        )
    return result


@router.post("/ownership-links")
def create_ownership_link(
    data: OwnershipLinkCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _validate_link(db, data.parent_company_id, data.child_company_id, data.percentage)
    link = CompanyOwnershipLink(
        parent_company_id=data.parent_company_id,
        child_company_id=data.child_company_id,
        percentage=data.percentage,
        consolidates=data.consolidates,
        notes=data.notes,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    sync_company_effective_percentages(db)
    return {"message": "Vínculo criado.", "id": link.id}


@router.put("/ownership-links/{link_id}")
def update_ownership_link(
    link_id: int,
    data: OwnershipLinkUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    link = _get_link_or_404(db, link_id)
    parent_id = data.parent_company_id if data.parent_company_id is not None else link.parent_company_id
    percentage = data.percentage if data.percentage is not None else link.percentage
    _validate_link(db, parent_id, link.child_company_id, percentage, exclude_link_id=link_id)

    if data.parent_company_id is not None:
        link.parent_company_id = data.parent_company_id
    if data.percentage is not None and abs(float(data.percentage) - float(link.percentage)) >= 1e-9:
        if not data.valid_from:
            raise HTTPException(
                status_code=400,
                detail="Informe o mês a partir do qual o novo % vale (AAAA-MM). O passado permanece com o % anterior.",
            )
        try:
            record_percentage_change(db, link, float(data.percentage), data.valid_from)
        except PeriodoInvalido as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data.consolidates is not None:
        link.consolidates = data.consolidates
    if data.notes is not None:
        link.notes = data.notes
        child = db.query(Company).filter(Company.id == link.child_company_id).first()
        if child:
            child.organograma_nota = data.notes

    db.commit()
    sync_company_effective_percentages(db)
    return {"message": "Vínculo atualizado."}


@router.delete("/ownership-links/{link_id}")
def delete_ownership_link(
    link_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    link = _get_link_or_404(db, link_id)
    db.delete(link)
    db.commit()
    sync_company_effective_percentages(db)
    return {"message": "Vínculo removido."}


@router.put("/empresas/{company_id}/participacao-manual")
def update_participacao_manual(
    company_id: int,
    data: ParticipacaoManualUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    if data.usa_participacao_manual and data.participacao_mldu_manual is None:
        raise HTTPException(status_code=400, detail="Informe participacao_mldu_manual ao ativar override.")

    company.usa_participacao_manual = data.usa_participacao_manual
    company.participacao_mldu_manual = data.participacao_mldu_manual if data.usa_participacao_manual else None
    db.commit()
    return serialize_company_brief(company)


@router.post("/estrutura-mldu/recalcular")
def recalcular_estrutura(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    sync_company_effective_percentages(db)
    return {"message": "Participações efetivas recalculadas."}


@router.post("/estrutura-mldu/seed")
def seed_estrutura_referencia(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Carga inicial conforme organograma (empresas devem existir no cadastro)."""
    return seed_reference_links(db)


@router.get("/validacao-organograma")
def get_validacao_organograma(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compara árvore atual vs organograma de referência (Onda E)."""
    from app.services.mldu_organograma_validacao import validate_organograma

    return validate_organograma(db)
