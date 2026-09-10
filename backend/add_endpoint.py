import re

with open('c:/Users/Usuario/Desktop/Em Desenvolvimento/Meus Projetos/ERP ML/backend/app/api/routes/viabilities.py', 'r', encoding='utf-8') as f:
    content = f.read()

endpoint_code = """

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
    if genai is None:
        raise HTTPException(status_code=500, detail="A biblioteca do Google Gemini não está instalada no servidor.")

    viability = db.query(Viability).filter(Viability.id == id).first()
    if not viability:
        raise HTTPException(status_code=404, detail="Viabilidade não encontrada.")
        
    api_key = request.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave de API do Gemini não configurada. Por favor, forneça a chave.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")
    
    # Coletar dados dos cenários (phases) e snapshots se houver
    cenarios_text = ""
    for idx, phase in enumerate(viability.phases):
        cenarios_text += f"\\n--- Cenário {idx+1}: {phase.name} ---\\n"
        
        # Tentar buscar o snapshot mais recente para pegar TIR e Payback
        from app.models.snapshot import PhaseSnapshot
        snapshot = db.query(PhaseSnapshot).filter(PhaseSnapshot.phase_id == phase.id).order_date_desc().first() if hasattr(PhaseSnapshot, 'phase_id') else None
        
        if not snapshot:
            # Busca de indicadores no banco de dados, assumindo que há uma rota ou schema de onde podemos ler.
            # Como fallback, colocamos os dados estáticos da phase
            cenarios_text += f"Status: {phase.status}\\n"
            
        else:
            # Aqui poderíamos colocar indicadores do snapshot
            pass
            
    # Prompt mais elaborado
    prompt = f\"\"\"Você é um diretor financeiro especialista em loteamentos urbanos (como a Moura Leite Loteamentos).
O usuário precisa de um Parecer Técnico / Resumo Executivo para abrir o Relatório de Viabilidade do projeto {viability.project_name}.

O estudo possui múltiplos cenários (fases). Analise os dados (ou as características se não houver dados completos ainda) e crie um texto contendo:
1. Resumo executivo com recomendação (indicando qual cenário parece melhor em termos de rentabilidade, risco de caixa e payback).
2. Tabela de Leitura sugerida.
3. Racional de cada cenário e Riscos qualitativos.

Seja extremamente profissional, use formatação Markdown (com headers h3 e tabelas se necessário).
Não escreva saudações nem encerramentos, apenas o texto do relatório.
\"\"\"
    
    try:
        response = model.generate_content(prompt)
        return {"summary": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na API da IA: {str(e)}")
"""

# Append at the bottom
with open('c:/Users/Usuario/Desktop/Em Desenvolvimento\Meus Projetos\ERP ML/backend/app/api/routes/viabilities.py', 'a', encoding='utf-8') as f:
    f.write(endpoint_code)

print("Endpoint adicionado!")
