import os
import sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy.orm import Session
from sqlalchemy import func, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.db.database import SessionLocal
from app.models.cost_center import CostCenter
from app.models.company import Company
from app.models.forecast import Forecast, ForecastItem
from app.services.carga_forecast_sharepoint import parse_sienge_forecast_report, FORECAST_BASE_DIR
import glob

def validate_empresa_2():
    db = SessionLocal()
    try:
        print("Validando Forecasts para Empresa ID 2")

        # Pegar todos os centros de custo e filtrar pela empresa 2 no custom_data
        todos_ccs = db.query(CostCenter).all()
        ccs = []
        for cc in todos_ccs:
            try:
                if cc.custom_data and cc.custom_data.get('__id_empresa') == 2:
                    ccs.append(cc)
            except:
                pass
        cc_map_sienge = {cc.id_sienge: cc for cc in ccs if cc.id_sienge}
        cc_map_nome = {cc.nome.lower(): cc for cc in ccs}
        cc_ids = [cc.id for cc in ccs]

        print(f"Encontrados {len(ccs)} Centros de Custo (Empreendimentos) para a Empresa 2.")

        # Buscar todos os Forecasts carregados (via RAW SQL)
        forecasts_db = db.execute(text("SELECT id, descricao FROM forecasts WHERE status = 'Importado Sienge'")).fetchall()
        if not forecasts_db:
            print("Nenhum Forecast importado encontrado no banco.")
            return
            
        print(f"Encontrados {len(forecasts_db)} Forecasts importados no banco de dados.")

        # Ler os dados dos relatórios no SharePoint
        subdirs = [f.path for f in os.scandir(FORECAST_BASE_DIR) if f.is_dir() and "Forecast -" in f.name]
        
        # Para cada pasta, comparar com o BD
        for folder in subdirs:
            folder_name = os.path.basename(folder)
            print(f"\n{'='*50}\nAnalisando {folder_name}...\n{'='*50}")
            
            search_pattern = os.path.join(folder, "**", "*.xlsx")
            files = glob.glob(search_pattern, recursive=True)
            
            if not files:
                continue
                
            raw_data = []
            for f in files:
                if "~$" in f: continue
                try:
                    raw_data.extend(parse_sienge_forecast_report(f, db))
                except Exception as e:
                    pass
            
            # Filtrar raw_data para apenas CCs da empresa 2
            raw_empresa2 = []
            for row in raw_data:
                cc_sienge = row.get("cc_id_sienge")
                cc_nome = row.get("cc_nome")
                
                is_empresa2 = False
                if cc_sienge and str(cc_sienge) in cc_map_sienge:
                    is_empresa2 = True
                    row['cc_id'] = cc_map_sienge[str(cc_sienge)].id
                elif cc_nome and cc_nome.lower() in cc_map_nome:
                    is_empresa2 = True
                    row['cc_id'] = cc_map_nome[cc_nome.lower()].id
                    
                if is_empresa2:
                    raw_empresa2.append(row)
                    
            print(f"Lidos {len(raw_empresa2)} itens no SharePoint para a Empresa 2 neste Forecast.")

            # Agrupar valores lidos do sharepoint por cc_id (total orçado)
            sharepoint_totals = {}
            for row in raw_empresa2:
                cc_id = row['cc_id']
                sharepoint_totals[cc_id] = sharepoint_totals.get(cc_id, 0) + row['orcado']
            
            # Agrupar valores lidos do BD para o mesmo forecast
            db_totals = {}
            for f_db in forecasts_db:
                f_id = f_db[0]
                f_desc = f_db[1]
                if f_desc == folder_name:
                    query = text("SELECT produto_id, total_anual FROM forecast_itens WHERE forecast_id = :fid AND produto_id IN :cc_ids")
                    # bindparams with tuples requires some care in sqlalchemy text, let's just do a string format for IN clause since cc_ids are ints
                    cc_ids_str = ",".join(map(str, cc_ids))
                    if not cc_ids_str: cc_ids_str = "-1"
                    query = text(f"SELECT produto_id, total_anual FROM forecast_itens WHERE forecast_id = :fid AND produto_id IN ({cc_ids_str})")
                    
                    items = db.execute(query, {"fid": f_id}).fetchall()
                    
                    for item in items:
                        db_totals[item[0]] = db_totals.get(item[0], 0) + float(item[1])

            # Comparar
            todas_ok = True
            for cc in ccs:
                total_sp = sharepoint_totals.get(cc.id, 0.0)
                total_db = db_totals.get(cc.id, 0.0)
                
                # Tolerância de 1 centavo para arredondamentos
                diff = abs(total_sp - total_db)
                if diff > 0.01:
                    print(f"DIVERGÊNCIA no Empreendimento: {cc.nome} (Sienge: {cc.id_sienge})")
                    print(f"  -> SharePoint: R$ {total_sp:,.2f}")
                    print(f"  -> Banco de Dados: R$ {total_db:,.2f}")
                    print(f"  -> Diferença: R$ {diff:,.2f}")
                    todas_ok = False
                else:
                    if total_sp > 0 or total_db > 0:
                        print(f"OK - Empreendimento: {cc.nome} (Sienge: {cc.id_sienge}) -> Total: R$ {total_db:,.2f}")
            
            if todas_ok:
                print(f">>> {folder_name} para a Empresa 2 bateu exatamente em todos os empreendimentos!")

    finally:
        db.close()

if __name__ == "__main__":
    validate_empresa_2()
