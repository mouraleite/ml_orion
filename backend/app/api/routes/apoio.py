from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.api.deps import get_current_user, get_db
from app.schemas.user import UserResponse
from app.services.erp_integration import erp_service
from app.models.company import Company, CompanyPartner
from app.models.user import User
from app.models.custom_field import CustomField
from app.models.cost_center import CostCenter
from app.models.financial_plan import FinancialPlan
from app.models.vision import Vision, VisionNode, FinancialPlanVisionLink
from app.models.payment_plan import PaymentPlan
from app.schemas.payment_plan import PaymentPlanCreate, PaymentPlanUpdate, PaymentPlanResponse
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate, ScenarioResponse
from app.models.scenario import Scenario
from app.models.economic_indicator import EconomicIndicator
from app.schemas.economic_indicator import EconomicIndicatorCreate, EconomicIndicatorUpdate, EconomicIndicator as EconomicIndicatorSchema

router = APIRouter()

class PartnerCreate(BaseModel):
    tipo: str
    partner_company_id: Optional[int] = None
    partner_name: Optional[str] = None
    partner_user_id: Optional[int] = None
    percentage: float
    is_consolidated: bool = False

@router.get("/empresas", response_model=List[Dict])
def get_empresas(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna a lista de empresas lendo rapidamente do banco local."""
    try:
        db_companies = db.query(Company).all()
        results = []
        for c in db_companies:
            results.append({
                "id": c.id_sienge,
                "db_id": c.id,
                "cnpj": c.cnpj,
                "razaoSocial": c.razao_social,
                "nomeFantasia": c.nome_fantasia,
                "status": c.status,
                "is_consolidated": c.is_consolidated,
                "tipo_empresa": c.tipo_empresa,
                "participacao_mldu_efetiva": c.participacao_mldu_efetiva,
                "participacao_mldu_manual": c.participacao_mldu_manual,
                "usa_participacao_manual": c.usa_participacao_manual,
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar empresas: {str(e)}")

def run_sync_empresas(db: Session):
    sienge_empresas = erp_service.fetch_empresas()
    
    for emp in sienge_empresas:
        db_company = db.query(Company).filter(Company.id_sienge == emp["id"]).first()
        if not db_company:
            db_company = Company(
                id_sienge=emp["id"],
                cnpj=emp["cnpj"],
                razao_social=emp["razaoSocial"],
                nome_fantasia=emp["nomeFantasia"],
                status=emp["status"]
            )
            db.add(db_company)
        else:
            if emp["cnpj"] and emp["cnpj"] != "N/A":
                db_company.cnpj = emp["cnpj"]
            if emp["razaoSocial"] and emp["razaoSocial"] != "N/A":
                db_company.razao_social = emp["razaoSocial"]
            
            if not db_company.nome_fantasia or db_company.nome_fantasia == "N/A" or db_company.nome_fantasia == "":
                db_company.nome_fantasia = emp["nomeFantasia"]
            
    db.commit()

@router.post("/empresas/sync")
def sync_empresas(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sincroniza empresas com a API do Sienge sob demanda."""
    try:
        run_sync_empresas(db)
        return {"message": "Sincronização concluída com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar empresas: {str(e)}")

@router.get("/empresas/{db_id}/socios")
def get_company_partners(db_id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == db_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada no banco local.")
    
    partners = db.query(CompanyPartner).filter(CompanyPartner.company_id == db_id).all()
    results = []
    for p in partners:
        partner_data = {
            "id": p.id,
            "tipo": p.tipo,
            "percentage": p.percentage,
            "is_consolidated": p.is_consolidated,
            "partner_user_id": getattr(p, "partner_user_id", None),
        }
        if p.partner_company_id:
            pc = db.query(Company).filter(Company.id == p.partner_company_id).first()
            partner_data["partner_name"] = pc.nome_fantasia if pc else "Desconhecido"
            partner_data["partner_company_id"] = p.partner_company_id
            partner_data["natureza"] = "PJ"
        elif getattr(p, "partner_user_id", None):
            user = db.query(User).filter(User.id == p.partner_user_id).first()
            partner_data["partner_name"] = (user.full_name if user else None) or p.partner_name or "Usuário"
            partner_data["natureza"] = "PF"
        else:
            partner_data["partner_name"] = p.partner_name
            partner_data["natureza"] = "PF" if (p.tipo or "").upper().find("PF") >= 0 else "PJ"
        results.append(partner_data)
        
    return results

@router.get("/usuarios-para-socios")
def list_users_for_partners(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista enxuta de usuários ativos para vincular como sócio pessoa física."""
    users = (
        db.query(User)
        .filter(User.is_active == True)
        .order_by(User.full_name.asc())
        .all()
    )
    return [
        {
            "id": u.id,
            "full_name": u.full_name or u.email,
            "email": u.email,
        }
        for u in users
        if (u.role or "") != "Integracao"
    ]

@router.post("/empresas/{db_id}/socios")
def add_company_partner(db_id: int, partner: PartnerCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == db_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada no banco local.")

    partner_name = partner.partner_name
    partner_user_id = partner.partner_user_id
    if partner_user_id:
        user = db.query(User).filter(User.id == partner_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        partner_name = user.full_name or user.email
    elif (partner.tipo or "") == "Sócio PF":
        raise HTTPException(status_code=400, detail="Selecione o usuário pessoa física.")
        
    new_partner = CompanyPartner(
        company_id=db_id,
        tipo=partner.tipo,
        partner_company_id=partner.partner_company_id,
        partner_name=partner_name,
        partner_user_id=partner_user_id,
        percentage=partner.percentage,
        is_consolidated=partner.is_consolidated
    )
    db.add(new_partner)
    db.commit()
    db.refresh(new_partner)
    return {"message": "Sócio adicionado com sucesso!", "id": new_partner.id}

@router.delete("/empresas/{db_id}/socios/{partner_id}")
def delete_company_partner(db_id: int, partner_id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    partner = db.query(CompanyPartner).filter(CompanyPartner.id == partner_id, CompanyPartner.company_id == db_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Sócio não encontrado.")
    
    db.delete(partner)
    db.commit()
    return {"message": "Sócio removido com sucesso!"}

class CompanyUpdate(BaseModel):
    nome_fantasia: Optional[str] = None
    is_consolidated: Optional[bool] = None
    tipo_empresa: Optional[str] = None
    status: Optional[str] = None

@router.put("/empresas/{db_id}")
def update_company(db_id: int, data: CompanyUpdate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == db_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada no banco local.")
        
    if data.nome_fantasia is not None:
        company.nome_fantasia = data.nome_fantasia
    if data.is_consolidated is not None:
        company.is_consolidated = data.is_consolidated
    if data.tipo_empresa is not None:
        company.tipo_empresa = data.tipo_empresa
    if data.status is not None:
        company.status = data.status
        
    db.commit()
    return {"message": "Empresa atualizada com sucesso!"}


# ─── Centros de Custo ─────────────────────────────────────────────────────────

# Modelos Pydantic para colunas
class CustomFieldCreate(BaseModel):
    field_name: str
    field_type: str = "text" # "text", "number", "boolean", "select"
    entity_type: str = "centro_custo"

class CostCenterUpdate(BaseModel):
    custom_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    track_in_dashboard: Optional[bool] = None
    project_phase: Optional[str] = None
    manual_land_cost: Optional[float] = None
    land_payment_curve_id: Optional[int] = None
    land_payment_start_date: Optional[str] = None
    apportionment_rules: Optional[List[Dict[str, Any]]] = None

@router.get("/centros-custo/colunas")
def get_custom_columns(entity_type: str = "centro_custo", db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """Busca as definições de colunas customizadas"""
    fields = db.query(CustomField).filter(CustomField.entity_type == entity_type).all()
    return [{"id": f.id, "field_name": f.field_name, "field_type": f.field_type} for f in fields]

@router.post("/centros-custo/colunas")
def create_custom_column(field: CustomFieldCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """Cria uma nova coluna customizada"""
    # Verifica se já existe
    exist = db.query(CustomField).filter(CustomField.entity_type == field.entity_type, CustomField.field_name == field.field_name).first()
    if exist:
        raise HTTPException(status_code=400, detail="Coluna já existe")
    
    new_field = CustomField(
        entity_type=field.entity_type,
        field_name=field.field_name,
        field_type=field.field_type
    )
    db.add(new_field)
    db.commit()
    db.refresh(new_field)
    return {"message": "Coluna criada", "id": new_field.id, "field_name": new_field.field_name}

@router.delete("/centros-custo/colunas/{field_id}")
def delete_custom_column(field_id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """Exclui uma coluna customizada"""
    field = db.query(CustomField).filter(CustomField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Coluna não encontrada")
    db.delete(field)
    db.commit()
    return {"message": "Coluna excluída"}

@router.get("/centros-custo")
def get_centros_custo(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Busca Centros de Custo do banco local de forma rápida."""
    try:
        db_centros = db.query(CostCenter).all()
        results = []
        for c in db_centros:
            custom = c.custom_data or {}
            results.append({
                "id": int(c.id_sienge) if c.id_sienge.isdigit() else c.id_sienge,
                "db_id": c.id,
                "nome": c.nome,
                "status": c.status,
                "cnpj": custom.get("__cnpj"),
                "id_empresa": custom.get("__id_empresa"),
                "nome_empresa": custom.get("__nome_empresa"),
                "tipo_sienge": custom.get("__tipo_override") or custom.get("__tipo_sienge_cache") or "Desconhecido",
                "custom_data": custom,
                "track_in_dashboard": c.track_in_dashboard,
                "project_phase": c.project_phase,
                "manual_land_cost": c.manual_land_cost,
                "land_payment_curve_id": custom.get("land_payment_curve_id"),
                "land_payment_start_date": custom.get("land_payment_start_date"),
                "apportionment_rules": c.apportionment_rules or []
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar centros de custo locais: {str(e)}")

def run_sync_centros_custo(db: Session):
    sienge_centros = erp_service.fetch_centros_custo()
    sienge_obras = erp_service.fetch_enterprises()
    
    TIPO_MAP = {
        "1": "Obra e Centro de Custo",
        "2": "Somente Obra",
        "3": "Somente Centro de Custo",
        "4": "Centro de Custo associado à Obra"
    }
    
    obras_map = {str(o["id"]): o for o in sienge_obras}
    centros_map = {str(c["id"]): c for c in sienge_centros}
    
    merged_list = []
    for cc in sienge_centros:
        cc_id = str(cc["id"])
        if cc_id in obras_map:
            obra = obras_map[cc_id]
            cc["tipo_sienge"] = TIPO_MAP.get(obra["tipo"], "Desconhecido")
            cc["cnpj"] = obra.get("cnpj")
            cc["id_empresa"] = obra.get("id_empresa")
            cc["nome_empresa"] = obra.get("nome_empresa")
        else:
            cc["tipo_sienge"] = "Somente Centro de Custo"
        merged_list.append(cc)
        
    for obra in sienge_obras:
        o_id = str(obra["id"])
        if o_id not in centros_map:
            merged_list.append({
                "id": obra["id"],
                "nome": obra["nome"],
                "cnpj": obra["cnpj"],
                "id_empresa": obra["id_empresa"],
                "nome_empresa": obra.get("nome_empresa"),
                "tipo_sienge": TIPO_MAP.get(obra["tipo"], "Somente Obra")
            })
    
    # Sincroniza com banco
    for item in merged_list:
        db_cc = db.query(CostCenter).filter(CostCenter.id_sienge == str(item["id"])).first()
        
        custom_update = {
            "__cnpj": item.get("cnpj"),
            "__id_empresa": item.get("id_empresa"),
            "__nome_empresa": item.get("nome_empresa"),
            "__tipo_sienge_cache": item.get("tipo_sienge")
        }
        
        if not db_cc:
            db_cc = CostCenter(
                id_sienge=str(item["id"]),
                nome=item["nome"],
                status="Ativo",
                custom_data=custom_update
            )
            db.add(db_cc)
        else:
            db_cc.nome = item["nome"]
            custom = dict(db_cc.custom_data) if db_cc.custom_data else {}
            custom.update(custom_update)
            db_cc.custom_data = custom
            
    db.commit()

@router.post("/centros-custo/sync")
def sync_centros_custo(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sincroniza Centros de Custo e Obras com a API do Sienge."""
    try:
        run_sync_centros_custo(db)
        return {"message": "Sincronização concluída com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar centros de custo: {str(e)}")

from fastapi import BackgroundTasks

@router.put("/centros-custo/{db_id}")
def update_centro_custo(
    db_id: int, 
    data: CostCenterUpdate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db), 
    current_user: UserResponse = Depends(get_current_user)
):
    """Atualiza as colunas customizadas e status de um Centro de Custo"""
    cc = db.query(CostCenter).filter(CostCenter.id == db_id).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Centro de Custo não encontrado")
    
    # Verifica se houve transição de track_in_dashboard para True
    was_tracked = cc.track_in_dashboard
    
    if data.custom_data is not None:
        # Atualiza o JSON
        current_data = dict(cc.custom_data) if cc.custom_data else {}
        current_data.update(data.custom_data)
        cc.custom_data = current_data
        
    if data.status is not None:
        cc.status = data.status
        
    if data.track_in_dashboard is not None:
        cc.track_in_dashboard = data.track_in_dashboard
    if data.project_phase is not None:
        cc.project_phase = data.project_phase
    if data.manual_land_cost is not None:
        cc.manual_land_cost = data.manual_land_cost
    if data.apportionment_rules is not None:
        cc.apportionment_rules = data.apportionment_rules
    
    current_data = dict(cc.custom_data) if cc.custom_data else {}
    update_dict = data.model_dump(exclude_unset=True)
    
    needs_custom_update = False
    if "land_payment_curve_id" in update_dict:
        current_data["land_payment_curve_id"] = update_dict["land_payment_curve_id"]
        needs_custom_update = True
    if "land_payment_start_date" in update_dict:
        current_data["land_payment_start_date"] = update_dict["land_payment_start_date"]
        needs_custom_update = True
        
    if needs_custom_update:
        cc.custom_data = current_data
    
    db.commit()
    
    # Se passou a ser rastreado, dispara sync imediato
    if not was_tracked and cc.track_in_dashboard:
        from app.services.sienge_sync import sync_single_cc_sienge_data
        background_tasks.add_task(sync_single_cc_sienge_data, db, cc)
        
    return {
        "message": "Atualizado com sucesso", 
        "custom_data": cc.custom_data, 
        "status": cc.status,
        "track_in_dashboard": cc.track_in_dashboard,
        "project_phase": cc.project_phase,
        "manual_land_cost": cc.manual_land_cost,
        "land_payment_curve_id": current_data.get("land_payment_curve_id"),
        "land_payment_start_date": current_data.get("land_payment_start_date"),
        "apportionment_rules": cc.apportionment_rules
    }

# ----------------- PLANOS FINANCEIROS -----------------

@router.get("/planos-financeiros")
def get_planos_financeiros(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Busca Planos Financeiros do banco local."""
    try:
        db_planos = db.query(FinancialPlan).all()
        results = []
        for p in db_planos:
            results.append({
                "id": p.id,
                "db_id": p.id,
                "db_sienge_id": p.db_id,
                "name": p.name,
                "tpConta": p.tp_conta,
                "flRedutora": p.fl_redutora,
                "flAtiva": p.fl_ativa,
                "flAdiantamento": p.fl_adiantamento,
                "flImposto": p.fl_imposto
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar planos financeiros locais: {str(e)}")

@router.post("/planos-financeiros/sync")
def sync_planos_financeiros(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sincroniza Planos Financeiros com a API do Sienge."""
    try:
        sienge_planos = erp_service.fetch_planos_financeiros()
        
        for item in sienge_planos:
            db_plano = db.query(FinancialPlan).filter(FinancialPlan.db_id == item["id"]).first()
            
            if not db_plano:
                db_plano = FinancialPlan(
                    db_id=item["id"],
                    name=item["name"],
                    tp_conta=item["tpConta"],
                    fl_redutora=item["flRedutora"],
                    fl_ativa=item["flAtiva"],
                    fl_adiantamento=item["flAdiantamento"],
                    fl_imposto=item["flImposto"]
                )
                db.add(db_plano)
            else:
                db_plano.name = item["name"]
                db_plano.tp_conta = item["tpConta"]
                db_plano.fl_redutora = item["flRedutora"]
                db_plano.fl_ativa = item["flAtiva"]
                db_plano.fl_adiantamento = item["flAdiantamento"]
                db_plano.fl_imposto = item["flImposto"]
                
        db.commit()
        return {"message": "Sincronização concluída com sucesso", "total": len(sienge_planos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar planos financeiros: {str(e)}")


# ── Visões (Cenários DRE) ─────────────────────────────────────────────────────

from app.models.vision import Vision, VisionNode, FinancialPlanVisionLink
from sqlalchemy import and_

class VisionCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    copiar_de_id: Optional[int] = None  # Se preenchido, clona a visão

class VisionNodeCreate(BaseModel):
    codigo: str
    descricao: str

class MovePlanRequest(BaseModel):
    vision_node_id: Optional[int] = None

def _serialize_node(node: VisionNode) -> Dict:
    """Serializa um nó com seus planos financeiros vinculados nesta visão."""
    planos = []
    for link in node.plan_links:
        p = link.financial_plan
        planos.append({"id": p.id, "db_id": p.db_id, "name": p.name, "tp_conta": p.tp_conta, "link_id": link.id})
    return {
        "id": node.id,
        "codigo": node.codigo,
        "descricao": node.descricao,
        "planos_financeiros": planos
    }

@router.get("/visoes", response_model=List[Dict])
def list_visoes(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista todas as visões cadastradas."""
    try:
        visoes = db.query(Vision).order_by(Vision.is_padrao.desc(), Vision.criado_em.asc()).all()
        result = []
        for v in visoes:
            total_nodes = len(v.nodes)
            total_links = sum(len(n.plan_links) for n in v.nodes)
            # criado_em pode ser datetime, string ou None dependendo do SQLite
            criado_em_str = None
            if v.criado_em:
                criado_em_str = v.criado_em.isoformat() if hasattr(v.criado_em, 'isoformat') else str(v.criado_em)
            result.append({
                "id": v.id,
                "nome": v.nome,
                "descricao": v.descricao,
                "is_padrao": bool(v.is_padrao),
                "criado_em": criado_em_str,
                "total_categorias": total_nodes,
                "total_planos": total_links,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visoes", response_model=Dict)
def create_visao(request: VisionCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cria uma nova visão (vazia ou clonada de outra)."""
    try:
        nova_visao = Vision(nome=request.nome, descricao=request.descricao, is_padrao=False)
        db.add(nova_visao)
        db.flush()

        if request.copiar_de_id:
            # Clonar estrutura da visão origem
            origem = db.query(Vision).filter(Vision.id == request.copiar_de_id).first()
            if not origem:
                raise HTTPException(status_code=404, detail="Visão de origem não encontrada")
            
            node_id_map = {}
            for orig_node in origem.nodes:
                new_node = VisionNode(
                    codigo=orig_node.codigo,
                    descricao=orig_node.descricao,
                    vision_id=nova_visao.id
                )
                db.add(new_node)
                db.flush()
                node_id_map[orig_node.id] = new_node.id
            
            # Clonar vínculos de planos financeiros
            for orig_node in origem.nodes:
                for link in orig_node.plan_links:
                    new_link = FinancialPlanVisionLink(
                        financial_plan_id=link.financial_plan_id,
                        vision_id=nova_visao.id,
                        vision_node_id=node_id_map.get(link.vision_node_id)
                    )
                    db.add(new_link)

        db.commit()
        db.refresh(nova_visao)
        return {"id": nova_visao.id, "nome": nova_visao.nome, "descricao": nova_visao.descricao, "is_padrao": nova_visao.is_padrao}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/visoes/{id}", response_model=Dict)
def update_visao(id: int, request: VisionCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Edita nome/descrição de uma visão."""
    visao = db.query(Vision).filter(Vision.id == id).first()
    if not visao:
        raise HTTPException(status_code=404, detail="Visão não encontrada")
    visao.nome = request.nome
    visao.descricao = request.descricao
    db.commit()
    return {"id": visao.id, "nome": visao.nome}

@router.delete("/visoes/{id}")
def delete_visao(id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exclui uma visão (apenas não-padrão)."""
    visao = db.query(Vision).filter(Vision.id == id).first()
    if not visao:
        raise HTTPException(status_code=404, detail="Visão não encontrada")
    if visao.is_padrao:
        raise HTTPException(status_code=400, detail="A Visão Padrão não pode ser excluída")
    db.delete(visao)
    db.commit()
    return {"message": "Visão excluída com sucesso"}

@router.get("/visoes/{id}/arvore", response_model=List[Dict])
def get_arvore_visao(id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna a árvore hierárquica de uma visão específica."""
    try:
        visao = db.query(Vision).filter(Vision.id == id).first()
        if not visao:
            raise HTTPException(status_code=404, detail="Visão não encontrada")
        nodes = db.query(VisionNode).filter(VisionNode.vision_id == id).order_by(VisionNode.codigo.asc()).all()
        return [_serialize_node(n) for n in nodes]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/visoes/{id}/nao-mapeados", response_model=List[Dict])
def get_nao_mapeados_visao(id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna planos financeiros de resultado que não estão mapeados nesta visão."""
    try:
        # IDs já vinculados nesta visão
        linked_ids = db.query(FinancialPlanVisionLink.financial_plan_id).filter(
            FinancialPlanVisionLink.vision_id == id
        ).subquery()
        
        planos = db.query(FinancialPlan).filter(
            FinancialPlan.tp_conta != 'T',
            ~FinancialPlan.id.in_(linked_ids)
        ).order_by(FinancialPlan.name.asc()).all()
        
        return [{"id": p.id, "db_id": p.db_id, "name": p.name, "tp_conta": p.tp_conta} for p in planos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/visoes/{vision_id}/planos/{plano_id}/move")
def move_plano_in_visao(vision_id: int, plano_id: int, request: MovePlanRequest,
                        current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Move um plano financeiro dentro de uma visão (ou o desvincula)."""
    # Verificar se visão existe
    visao = db.query(Vision).filter(Vision.id == vision_id).first()
    if not visao:
        raise HTTPException(status_code=404, detail="Visão não encontrada")
    
    plano = db.query(FinancialPlan).filter(FinancialPlan.id == plano_id).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano financeiro não encontrado")

    # Remover link existente (se houver)
    db.query(FinancialPlanVisionLink).filter(
        FinancialPlanVisionLink.financial_plan_id == plano_id,
        FinancialPlanVisionLink.vision_id == vision_id
    ).delete()

    # Criar novo link se tiver destino
    if request.vision_node_id is not None:
        link = FinancialPlanVisionLink(
            financial_plan_id=plano_id,
            vision_id=vision_id,
            vision_node_id=request.vision_node_id
        )
        db.add(link)

    db.commit()
    return {"message": "Plano movido com sucesso"}

# ── Nós de uma Visão ──────────────────────────────────────────────────────────

@router.post("/visoes/{vision_id}/categorias", response_model=Dict)
def create_categoria(vision_id: int, request: VisionNodeCreate,
                     current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cria uma nova categoria (nó) dentro de uma visão."""
    visao = db.query(Vision).filter(Vision.id == vision_id).first()
    if not visao:
        raise HTTPException(status_code=404, detail="Visão não encontrada")
    
    existing = db.query(VisionNode).filter(
        VisionNode.vision_id == vision_id,
        VisionNode.codigo == request.codigo
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Código já existe nesta visão")
    
    node = VisionNode(codigo=request.codigo, descricao=request.descricao, vision_id=vision_id)
    db.add(node)
    db.commit()
    db.refresh(node)
    return {"id": node.id, "codigo": node.codigo, "descricao": node.descricao, "planos_financeiros": []}

@router.put("/visoes/{vision_id}/categorias/{node_id}", response_model=Dict)
def update_categoria(vision_id: int, node_id: int, request: VisionNodeCreate,
                     current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Edita uma categoria."""
    node = db.query(VisionNode).filter(VisionNode.id == node_id, VisionNode.vision_id == vision_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    node.codigo = request.codigo
    node.descricao = request.descricao
    db.commit()
    return {"id": node.id, "codigo": node.codigo, "descricao": node.descricao}

@router.delete("/visoes/{vision_id}/categorias/{node_id}")
def delete_categoria(vision_id: int, node_id: int,
                     current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exclui uma categoria. Os planos vinculados ficam órfãos nesta visão."""
    node = db.query(VisionNode).filter(VisionNode.id == node_id, VisionNode.vision_id == vision_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    # Desvincular planos (delete-orphan vai cuidar dos links)
    db.delete(node)
    db.commit()
    return {"message": "Categoria excluída"}

# ── Planos de Pagamento (Templates Globais) ───────────────────────────────────

@router.get("/planos-pagamento", response_model=List[PaymentPlanResponse])
def get_payment_plans(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    plans = db.query(PaymentPlan).order_by(PaymentPlan.id.asc()).all()
    # Convert condicoes_json back to list if it's stored as something else, but sqlalchemy handles JSON seamlessly
    return plans

@router.post("/planos-pagamento", response_model=PaymentPlanResponse)
def create_payment_plan(plan: PaymentPlanCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(PaymentPlan).filter(PaymentPlan.nome == plan.nome).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plano já existe com esse nome")
    
    new_plan = PaymentPlan(
        nome=plan.nome,
        condicoes_json=[c.model_dump() for c in plan.condicoes_json]
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan

@router.put("/planos-pagamento/{plan_id}", response_model=PaymentPlanResponse)
def update_payment_plan(plan_id: int, plan: PaymentPlanUpdate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    db_plan = db.query(PaymentPlan).filter(PaymentPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plano de pagamento não encontrado")
    
    if plan.nome is not None:
        db_plan.nome = plan.nome
    if plan.condicoes_json is not None:
        db_plan.condicoes_json = [c.model_dump() for c in plan.condicoes_json]
        
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.delete("/planos-pagamento/{plan_id}")
def delete_payment_plan(plan_id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    db_plan = db.query(PaymentPlan).filter(PaymentPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plano de pagamento não encontrado")
    
    db.delete(db_plan)
    db.commit()
    return {"message": "Plano excluído com sucesso"}

@router.post("/planos-pagamento/seed", response_model=List[PaymentPlanResponse])
def seed_payment_plans(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Semeia os planos de pagamento padrões se não existirem."""
    existing_count = db.query(PaymentPlan).count()
    if existing_count > 0:
        return db.query(PaymentPlan).order_by(PaymentPlan.id.asc()).all()
        
    DEFAULT_PLANS = [
        { "nome": "Neutro (65/20/15) - ABERTO", "condicoes": [{"nome":"A VISTA", "perc":3.8}, {"nome":"24", "perc":6.6}, {"nome":"36", "perc":12.8}, {"nome":"48", "perc":18.0}, {"nome":"60", "perc":2.4}, {"nome":"120", "perc":7.9}, {"nome":"180", "perc":48.6}] },
        { "nome": "Neutro (65/20/15) - ABERTO POPULAR", "condicoes": [{"nome":"A VISTA", "perc":0.6}, {"nome":"24", "perc":5.6}, {"nome":"36", "perc":2.4}, {"nome":"48", "perc":3.4}, {"nome":"60", "perc":4.6}, {"nome":"120", "perc":9.5}, {"nome":"180", "perc":73.8}] },
        { "nome": "Neutro (65/20/15) - FECHADO", "condicoes": [{"nome":"A VISTA", "perc":3.5}, {"nome":"24", "perc":12.8}, {"nome":"36", "perc":15.9}, {"nome":"48", "perc":20.7}, {"nome":"60", "perc":2.5}, {"nome":"120", "perc":5.2}, {"nome":"180", "perc":39.3}] },
        { "nome": "Pessimista (50/30/20) - ABERTO", "condicoes": [{"nome":"A VISTA", "perc":3.8}, {"nome":"24", "perc":6.6}, {"nome":"36", "perc":12.8}, {"nome":"48", "perc":18.0}, {"nome":"60", "perc":2.4}, {"nome":"120", "perc":7.9}, {"nome":"180", "perc":48.6}] },
        { "nome": "Pessimista (50/30/20) - ABERTO POPULAR", "condicoes": [{"nome":"A VISTA", "perc":0.6}, {"nome":"24", "perc":5.6}, {"nome":"36", "perc":2.4}, {"nome":"48", "perc":3.4}, {"nome":"60", "perc":4.6}, {"nome":"120", "perc":9.5}, {"nome":"180", "perc":73.8}] },
        { "nome": "Pessimista (50/30/20) - FECHADO", "condicoes": [{"nome":"A VISTA", "perc":3.5}, {"nome":"24", "perc":12.8}, {"nome":"36", "perc":15.9}, {"nome":"48", "perc":20.7}, {"nome":"60", "perc":2.5}, {"nome":"120", "perc":5.2}, {"nome":"180", "perc":39.3}] },
        { "nome": "Otimista (75/25) - ABERTO", "condicoes": [{"nome":"A VISTA", "perc":3.8}, {"nome":"24", "perc":6.6}, {"nome":"36", "perc":12.8}, {"nome":"48", "perc":18.0}, {"nome":"60", "perc":2.4}, {"nome":"120", "perc":7.9}, {"nome":"180", "perc":48.6}] },
        { "nome": "Otimista (75/25) - ABERTO POPULAR", "condicoes": [{"nome":"A VISTA", "perc":0.6}, {"nome":"24", "perc":5.6}, {"nome":"36", "perc":2.4}, {"nome":"48", "perc":3.4}, {"nome":"60", "perc":4.6}, {"nome":"120", "perc":9.5}, {"nome":"180", "perc":73.8}] },
        { "nome": "Otimista (75/25) - FECHADO", "condicoes": [{"nome":"A VISTA", "perc":3.5}, {"nome":"24", "perc":12.8}, {"nome":"36", "perc":15.9}, {"nome":"48", "perc":20.7}, {"nome":"60", "perc":2.5}, {"nome":"120", "perc":5.2}, {"nome":"180", "perc":39.3}] },
        { "nome": "Otimista (75/30) - ABERTO", "condicoes": [{"nome":"A VISTA", "perc":3.8}, {"nome":"24", "perc":6.6}, {"nome":"36", "perc":12.8}, {"nome":"48", "perc":18.0}, {"nome":"60", "perc":2.4}, {"nome":"120", "perc":7.9}, {"nome":"180", "perc":48.6}] },
        { "nome": "Otimista (75/30) - ABERTO POPULAR", "condicoes": [{"nome":"A VISTA", "perc":0.6}, {"nome":"24", "perc":5.6}, {"nome":"36", "perc":2.4}, {"nome":"48", "perc":3.4}, {"nome":"60", "perc":4.6}, {"nome":"120", "perc":9.5}, {"nome":"180", "perc":73.8}] },
        { "nome": "Otimista (75/30) - FECHADO", "condicoes": [{"nome":"A VISTA", "perc":3.5}, {"nome":"24", "perc":12.8}, {"nome":"36", "perc":15.9}, {"nome":"48", "perc":20.7}, {"nome":"60", "perc":2.5}, {"nome":"120", "perc":5.2}, {"nome":"180", "perc":39.3}] },
        { "nome": "Otimista + (75/25) - ABERTO", "condicoes": [{"nome":"A VISTA", "perc":3.8}, {"nome":"24", "perc":6.6}, {"nome":"36", "perc":12.8}, {"nome":"48", "perc":18.0}, {"nome":"60", "perc":2.4}, {"nome":"120", "perc":7.9}, {"nome":"180", "perc":48.6}] },
        { "nome": "Otimista + (75/25) - ABERTO POPULAR", "condicoes": [{"nome":"A VISTA", "perc":0.6}, {"nome":"24", "perc":5.6}, {"nome":"36", "perc":2.4}, {"nome":"48", "perc":3.4}, {"nome":"60", "perc":4.6}, {"nome":"120", "perc":9.5}, {"nome":"180", "perc":73.8}] },
        { "nome": "Otimista + (75/25) - FECHADO", "condicoes": [{"nome":"A VISTA", "perc":3.5}, {"nome":"24", "perc":12.8}, {"nome":"36", "perc":15.9}, {"nome":"48", "perc":20.7}, {"nome":"60", "perc":2.5}, {"nome":"120", "perc":5.2}, {"nome":"180", "perc":39.3}] },
        { "nome": "Pessimista + (56/25/19) - ABERTO", "condicoes": [{"nome":"A VISTA", "perc":3.8}, {"nome":"24", "perc":6.6}, {"nome":"36", "perc":12.8}, {"nome":"48", "perc":18.0}, {"nome":"60", "perc":2.4}, {"nome":"120", "perc":7.9}, {"nome":"180", "perc":48.6}] },
        { "nome": "Pessimista + (56/25/19) - ABERTO POPULAR", "condicoes": [{"nome":"A VISTA", "perc":0.6}, {"nome":"24", "perc":5.6}, {"nome":"36", "perc":2.4}, {"nome":"48", "perc":3.4}, {"nome":"60", "perc":4.6}, {"nome":"120", "perc":9.5}, {"nome":"180", "perc":73.8}] },
        { "nome": "Pessimista + (56/25/19) - FECHADO", "condicoes": [{"nome":"A VISTA", "perc":3.5}, {"nome":"24", "perc":12.8}, {"nome":"36", "perc":15.9}, {"nome":"48", "perc":20.7}, {"nome":"60", "perc":2.5}, {"nome":"120", "perc":5.2}, {"nome":"180", "perc":39.3}] },
    ]
    
    for plan_data in DEFAULT_PLANS:
        new_plan = PaymentPlan(
            nome=plan_data["nome"],
            condicoes_json=plan_data["condicoes"]
        )
        db.add(new_plan)
        
    db.commit()
    return db.query(PaymentPlan).order_by(PaymentPlan.id.asc()).all()

# ── Cenários Globais ──────────────────────────────────────────────────────────

@router.get("/cenarios", response_model=List[ScenarioResponse])
def get_scenarios(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna todos os cenários."""
    return db.query(Scenario).order_by(Scenario.id.asc()).all()

@router.post("/cenarios", response_model=ScenarioResponse)
def create_scenario(scenario: ScenarioCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cria um novo cenário."""
    existing = db.query(Scenario).filter(Scenario.nome == scenario.nome).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cenário já existe com esse nome.")
    
    new_scenario = Scenario(
        nome=scenario.nome,
        vgv_multiplier=scenario.vgv_multiplier,
        construction_cost_multiplier=scenario.construction_cost_multiplier,
        sales_speed_multiplier=scenario.sales_speed_multiplier
    )
    db.add(new_scenario)
    db.commit()
    db.refresh(new_scenario)
    return new_scenario

@router.put("/cenarios/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(scenario_id: int, scenario: ScenarioUpdate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Atualiza um cenário."""
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Cenário não encontrado.")
    
    if scenario.nome is not None:
        db_scenario.nome = scenario.nome
    if scenario.vgv_multiplier is not None:
        db_scenario.vgv_multiplier = scenario.vgv_multiplier
    if scenario.construction_cost_multiplier is not None:
        db_scenario.construction_cost_multiplier = scenario.construction_cost_multiplier
    if scenario.sales_speed_multiplier is not None:
        db_scenario.sales_speed_multiplier = scenario.sales_speed_multiplier
        
    db.commit()
    db.refresh(db_scenario)
    return db_scenario

@router.delete("/cenarios/{scenario_id}")
def delete_scenario(scenario_id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exclui um cenário."""
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Cenário não encontrado.")
    
    db.delete(db_scenario)
    db.commit()
    return {"message": "Cenário excluído com sucesso"}

@router.post("/cenarios/seed", response_model=List[ScenarioResponse])
def seed_scenarios(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Semeia os cenários padrões se não existirem."""
    existing_count = db.query(Scenario).count()
    if existing_count > 0:
        return db.query(Scenario).order_by(Scenario.id.asc()).all()
        
    DEFAULT_SCENARIOS = [
        "Pessimista +",
        "Pessimista",
        "Neutro",
        "Otimista",
        "Otimista +"
    ]
    
    for nome in DEFAULT_SCENARIOS:
        new_scenario = Scenario(nome=nome)
        db.add(new_scenario)
        
    db.commit()
    return db.query(Scenario).order_by(Scenario.id.asc()).all()

# ── Indicadores Globais (Econômicos) ──────────────────────────────────────────

@router.get("/indicadores", response_model=List[EconomicIndicatorSchema])
def get_economic_indicators(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna todos os indicadores econômicos."""
    return db.query(EconomicIndicator).order_by(EconomicIndicator.id.asc()).all()

@router.post("/indicadores", response_model=EconomicIndicatorSchema)
def create_economic_indicator(indicator: EconomicIndicatorCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cria um novo indicador econômico."""
    new_indicator = EconomicIndicator(
        nome=indicator.nome,
        index_type=indicator.index_type,
        valor=indicator.valor,
        tipo_unidade=indicator.tipo_unidade,
        competencia=indicator.competencia
    )
    db.add(new_indicator)
    db.commit()
    db.refresh(new_indicator)
    return new_indicator

@router.put("/indicadores/{indicator_id}", response_model=EconomicIndicatorSchema)
def update_economic_indicator(indicator_id: int, indicator: EconomicIndicatorUpdate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Atualiza um indicador econômico."""
    db_indicator = db.query(EconomicIndicator).filter(EconomicIndicator.id == indicator_id).first()
    if not db_indicator:
        raise HTTPException(status_code=404, detail="Indicador não encontrado.")
    
    if indicator.nome is not None:
        db_indicator.nome = indicator.nome
    if indicator.index_type is not None:
        db_indicator.index_type = indicator.index_type
    if indicator.valor is not None:
        db_indicator.valor = indicator.valor
    if indicator.tipo_unidade is not None:
        db_indicator.tipo_unidade = indicator.tipo_unidade
    if indicator.competencia is not None:
        db_indicator.competencia = indicator.competencia
        
    db.commit()
    db.refresh(db_indicator)
    return db_indicator

@router.delete("/indicadores/{indicator_id}")
def delete_economic_indicator(indicator_id: int, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """Exclui um indicador econômico."""
    db_indicator = db.query(EconomicIndicator).filter(EconomicIndicator.id == indicator_id).first()
    if not db_indicator:
        raise HTTPException(status_code=404, detail="Indicador não encontrado.")
    
    db.delete(db_indicator)
    db.commit()
    return {"message": "Indicador excluído com sucesso"}

from app.models.system_settings import SystemSettings
from app.schemas.system_settings import SystemSettingsResponse, SystemSettingsUpdate, SystemSettingsCreate

@router.get("/system-settings/{key}", response_model=SystemSettingsResponse)
def get_system_setting(key: str, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.post("/system-settings", response_model=SystemSettingsResponse)
def create_or_update_system_setting(setting_in: SystemSettingsCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    setting = db.query(SystemSettings).filter(SystemSettings.key == setting_in.key).first()
    if setting:
        setting.value = setting_in.value
    else:
        setting = SystemSettings(key=setting_in.key, value=setting_in.value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return setting


@router.get("/consumo-sienge")
def get_consumo_sienge(
    ano: Optional[int] = None,
    mes: Optional[int] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Agregado mensal das chamadas deste ERP às APIs Sienge (REST e BULK)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.services.sienge_usage import build_month_report

    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    year = ano if ano is not None else now.year
    month = mes if mes is not None else now.month
    if month < 1 or month > 12 or year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Mês inválido.")
    return build_month_report(db, year, month)
