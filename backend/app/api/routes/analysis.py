from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.viability import Viability
from app.services.math_engine import calculate_viability_results

router = APIRouter()

def _calculate_score(margem: float, tir: float, exposicao: float, vgv: float) -> int:
    margem = margem or 0.0
    tir = tir or 0.0
    exposicao = exposicao or 0.0
    vgv = vgv or 0.0

    # Margem (Max 40)
    score_margem = min(40, max(0, (margem / 25.0) * 40))
    
    # TIR (Max 30)
    score_tir = min(30, max(0, (tir / 25.0) * 30))
    
    # Exposição (Max 30)
    if vgv > 0:
        exp_perc = abs(exposicao) / vgv
    else:
        exp_perc = 0
    
    score_exp = max(0, 30 - ((exp_perc / 0.20) * 30))
    
    return int(score_margem + score_tir + score_exp)

def _generate_explanation(scenario_name: str, indicators: dict, original_indicators: dict) -> str:
    if not original_indicators:
        return f"Este é o projeto base. Ele servirá como referência para as demais comparações de cenários."
        
    explanations = []
    
    if (indicators.get("margem_perc") or 0.0) > (original_indicators.get("margem_perc") or 0.0) + 0.5:
        explanations.append(f"apresenta uma margem melhor ({(indicators.get('margem_perc') or 0.0):.1f}%)")
    elif (indicators.get("margem_perc") or 0.0) < (original_indicators.get("margem_perc") or 0.0) - 0.5:
        explanations.append(f"sofreu uma queda na margem ({(indicators.get('margem_perc') or 0.0):.1f}%)")
        
    if (indicators.get("custo_obras") or 0.0) < (original_indicators.get("custo_obras") or 0.0) * 0.95:
        explanations.append("graças à redução no custo de obras")
    elif (indicators.get("custo_obras") or 0.0) > (original_indicators.get("custo_obras") or 0.0) * 1.05:
        explanations.append("devido ao aumento no custo de obras")
        
    if (indicators.get("vgv_total") or 0.0) > (original_indicators.get("vgv_total") or 0.0) * 1.05:
        explanations.append("impulsionado por um VGV maior")
        
    if not explanations:
        return f"O {scenario_name} possui indicadores muito similares ao original."
        
    return f"O {scenario_name} " + " e ".join(explanations) + "."

def _generate_suggestions(indicators: dict) -> List[str]:
    suggestions = []
    margem_perc = indicators.get("margem_perc") or 0.0
    tir_aa = indicators.get("tir_aa") or 0.0
    vgv_total = indicators.get("vgv_total") or 0.0
    exposicao_maxima = indicators.get("exposicao_maxima") or 0.0

    if margem_perc < 15:
        suggestions.append("A Margem Líquida está baixa (<15%). Tente reduzir os custos de obra ou avaliar um leve aumento no VGV.")
    if tir_aa < 15:
        suggestions.append("A TIR está abaixo do esperado. Considere postergar despesas, antecipar o lançamento ou trocar a compra de terreno por permuta financeira.")
    
    exp_perc = abs(exposicao_maxima) / (vgv_total or 1)
    if exp_perc > 0.10:
        suggestions.append("A exposição de caixa está alta (mais de 10% do VGV). Pode ser interessante configurar um Funding (ex: CRI ou Plano Empresarial) para aliviar o caixa.")
        
    if not suggestions:
        suggestions.append("Este cenário apresenta indicadores muito saudáveis! O equilíbrio entre margem, TIR e exposição está excelente.")
        
    return suggestions

@router.get("/{id}/compare-analysis")
def compare_analysis(
    id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
    
    root_id = viability.version_of_id if viability.version_of_id else viability.id
    
    family = db.query(Viability).filter(
        (Viability.id == root_id) | (Viability.version_of_id == root_id)
    ).order_by(Viability.created_at).all()
    
    results = []
    original_indicators = None
    
    for v in family:
        is_root = (v.id == root_id)
        
        # Build zero-value default indicators for cases where calc fails or no phases
        zero_inds = {
            "tir_aa": 0.0, "margem_perc": 0.0, "exposicao_maxima": 0.0,
            "vgv_total": 0.0, "custo_obras": 0.0, "valor_terreno": 0.0,
            "lucro_liquido": 0.0, "vpl": 0.0
        }

        if not v.phases:
            inds = zero_inds
        else:
            phase_id = v.phases[0].id
            math_results = calculate_viability_results(db, phase_id)
            if "error" in math_results:
                inds = zero_inds
            else:
                inds = math_results["indicators"]
            
        tir_aa = inds.get("tir_aa") or 0.0
        margem_perc = inds.get("margem_perc") or 0.0
        exposicao_maxima = inds.get("exposicao_maxima") or 0.0
        vgv_total = inds.get("vgv_total") or 0.0
        score = _calculate_score(margem_perc, tir_aa, exposicao_maxima, vgv_total)
        
        if is_root:
            original_indicators = inds
            
        results.append({
            "id": v.id,
            "project_name": v.project_name,
            "is_root": is_root,
            "indicators": {
                "vgv_total": vgv_total,
                "custo_obras": inds.get("custo_obras") or 0.0,
                "valor_terreno": inds.get("valor_terreno") or 0.0,
                "lucro_liquido": inds.get("lucro_liquido") or 0.0,
                "margem_perc": margem_perc,
                "tir_aa": tir_aa,
                "vpl": inds.get("vpl") or 0.0,
                "exposicao_maxima": exposicao_maxima
            },
            "score": score,
            "explanation": "",
            "suggestions": _generate_suggestions(inds)
        })
        
    for r in results:
        r["explanation"] = _generate_explanation(r["project_name"], r["indicators"], original_indicators if not r["is_root"] else None)
        
    if results:
        winner = max(results, key=lambda x: x["score"])
        for r in results:
            r["is_winner"] = (r["id"] == winner["id"])
            
    return results
