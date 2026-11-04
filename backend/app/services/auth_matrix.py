from sqlalchemy.orm import Session
from app.models.departamento import DepartamentoPlano, ProdutoPlanoFinanceiro

def validate_budget_allocation(db: Session, departamento_id: int, produto_id: int, plano_financeiro_id: int) -> bool:
    """
    Verifica a matriz de autorização (Departamento x Produto x Plano Financeiro).
    Retorna True se o lançamento for permitido, False caso contrário.
    Utiliza lógica de 'White List' (permissão padrão fechada).

    Se produto_plano_financeiro estiver vazio (produção atual), só o vínculo
    departamento × plano é exigido — a carga Excel já segue essa regra.
    """
    # 1. Verifica se o Departamento tem acesso ao Plano Financeiro
    dept_plano_link = db.query(DepartamentoPlano).filter(
        DepartamentoPlano.departamento_id == departamento_id,
        DepartamentoPlano.plano_financeiro_id == plano_financeiro_id,
        DepartamentoPlano.permitido == True
    ).first()

    if not dept_plano_link:
        return False

    matriz_produto_em_uso = (
        db.query(ProdutoPlanoFinanceiro.id).first() is not None
    )
    if not matriz_produto_em_uso:
        return True

    # 2. Verifica se o Produto (CostCenter) permite este Plano Financeiro
    prod_plano_link = db.query(ProdutoPlanoFinanceiro).filter(
        ProdutoPlanoFinanceiro.produto_id == produto_id,
        ProdutoPlanoFinanceiro.plano_financeiro_id == plano_financeiro_id,
        ProdutoPlanoFinanceiro.permitido == True
    ).first()

    if not prod_plano_link:
        return False

    return True
