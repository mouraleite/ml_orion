from fastapi import APIRouter, Depends, HTTPException
import os
import re
import zipfile
from datetime import datetime

from app.api.deps import require_admin
from app.models.user import User

router = APIRouter()

def get_project_root():
    # backend/app/api/routes/system.py -> 4 levels up
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, "../../../../"))

@router.post("/version")
def save_new_version(_admin: User = Depends(require_admin)):
    root_dir = get_project_root()
    version_file_path = os.path.join(root_dir, "frontend", "src", "version.ts")
    backups_dir = os.path.join(root_dir, "Backups")
    
    if not os.path.exists(version_file_path):
        raise HTTPException(status_code=500, detail="version.ts não encontrado.")
    
    # Ler a versão atual
    with open(version_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    match = re.search(r'APP_VERSION = "(\d+\.\d+\.\d+)";', content)
    if not match:
        raise HTTPException(status_code=500, detail="Formato da versão não encontrado.")
    
    current_version = match.group(1)
    parts = current_version.split(".")
    
    # Auto-increment patch
    new_patch = int(parts[2]) + 1
    new_version = f"{parts[0]}.{parts[1]}.{new_patch}"
    
    new_content = content.replace(f'APP_VERSION = "{current_version}"', f'APP_VERSION = "{new_version}"')
    with open(version_file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    # Zip files
    if not os.path.exists(backups_dir):
        os.makedirs(backups_dir)
        
    zip_filename = os.path.join(backups_dir, "ERP_ML_ultimo.zip")
    zip_tmp = os.path.join(backups_dir, "ERP_ML_ultimo.zip.tmp")

    ignore_dirs = {
        ".next",
        "node_modules",
        ".venv",
        "__pycache__",
        "Backups",
        ".git",
        ".gemini",
        "scratch_backup",
        "app",
    }

    try:
        if os.path.exists(zip_tmp):
            os.remove(zip_tmp)
        with zipfile.ZipFile(zip_tmp, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.comment = f"v{new_version} {datetime.now().isoformat()}".encode("utf-8")
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for file in files:
                    if file.endswith(".zip.tmp"):
                        continue
                    # Lixo de dev na raiz não entra no zip de versão
                    if root == root_dir and (
                        file.startswith(("resp_", "tool_call_", "patch_", "fix_"))
                        or file.endswith((".db", ".bak"))
                    ):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, root_dir)
                    zipf.write(file_path, arcname)
        os.replace(zip_tmp, zip_filename)
    except Exception as e:
        if os.path.exists(zip_tmp):
            try:
                os.remove(zip_tmp)
            except OSError:
                pass
        with open(version_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        raise HTTPException(status_code=500, detail=f"Erro ao criar backup: {str(e)}")

    return {
        "status": "success",
        "version": new_version,
        "file": zip_filename,
        "arquivo": "ERP_ML_ultimo.zip",
    }
