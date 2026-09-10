import zipfile
import os

zip_path = r"c:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML\Backups\ERP_ML_v1.0.20.zip"
base_dir = r"c:\Users\Usuario\Desktop\Em Desenvolvimento\Meus Projetos\ERP ML"

files_to_restore = [
    r"frontend\src\app\dashboard\apoio\cenarios\page.tsx",
    r"frontend\src\app\dashboard\apoio\centro-de-custo\page.tsx",
    r"frontend\src\app\dashboard\apoio\empresas\page.tsx",
    r"frontend\src\app\dashboard\apoio\parcerias\page.tsx",
    r"frontend\src\app\dashboard\apoio\planos-de-pagamento\page.tsx",
    r"frontend\src\app\dashboard\apoio\planos-financeiros\page.tsx",
    r"frontend\src\app\dashboard\apoio\taxas-funding\page.tsx",
    r"frontend\src\app\dashboard\apoio\visao\page.tsx",
    r"frontend\src\app\dashboard\apoio\visao\[id]\page.tsx",
    r"frontend\src\app\dashboard\governance\relatorios\page.tsx",
    r"frontend\src\app\dashboard\governance\workflow\page.tsx",
    r"frontend\src\app\dashboard\holding\apresentacoes\page.tsx",
    r"frontend\src\app\dashboard\holding\base-historica\page.tsx",
    r"frontend\src\app\dashboard\holding\painel\page.tsx",
    r"frontend\src\app\dashboard\holding\relatorios\page.tsx",
    r"frontend\src\app\dashboard\orcamento\forecast\page.tsx",
    r"frontend\src\app\dashboard\orcamento\geral\page.tsx",
    r"frontend\src\app\dashboard\orcamento\realizado\page.tsx",
    r"frontend\src\app\dashboard\orcamento\relatorios\page.tsx",
    r"frontend\src\app\dashboard\seguranca\logs\page.tsx",
    r"frontend\src\app\dashboard\seguranca\perfis\page.tsx",
    r"frontend\src\app\dashboard\seguranca\relatorios\page.tsx",
    r"frontend\src\app\dashboard\seguranca\usuarios\page.tsx",
    r"frontend\src\app\login\page.tsx",
    r"frontend\src\components\governance\IndexModal.tsx",
    r"frontend\src\components\ui\Card.tsx",
    r"frontend\src\components\ui\FormattedNumber.tsx",
    r"frontend\src\components\ui\Table.tsx",
    r"frontend\src\components\viabilities\ConstructionTab.tsx",
    r"frontend\src\components\viabilities\CurvesConfig.tsx",
    r"frontend\src\components\viabilities\DatesTab.tsx",
    r"frontend\src\components\viabilities\ExchangesTab.tsx",
    r"frontend\src\components\viabilities\ExpensesTab.tsx",
    r"frontend\src\components\viabilities\PhysicalDataTab.tsx",
    r"frontend\src\components\viabilities\RevenueTab.tsx"
]

restored = 0
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    # We need to map the internal zip path to our files
    # The zip might have a root folder, like ERP ML/frontend/... or just frontend/...
    # Let's check the zip contents for the first file to find the prefix
    internal_paths = zip_ref.namelist()
    
    for relative_path in files_to_restore:
        # Procurar qual o caminho no zip que termina com o relative_path (normalizando as barras)
        search_path = relative_path.replace('\\', '/')
        matching_internal = [p for p in internal_paths if p.endswith(search_path)]
        
        if matching_internal:
            internal_p = matching_internal[0]
            # Ler o conteudo do zip
            content = zip_ref.read(internal_p)
            
            # Salvar no destino
            dest_path = os.path.join(base_dir, relative_path)
            with open(dest_path, 'wb') as f:
                f.write(content)
            restored += 1
            print(f"Restaurado: {dest_path}")
        else:
            print(f"Não encontrado no zip: {search_path}")

print(f"Total restaurado: {restored}")
