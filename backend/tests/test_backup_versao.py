"""O zip de /system/version precisa levar o código do sistema (backend/app e frontend/src/app)."""
import os
import zipfile

import pytest

from app.api.routes import system


def _arquivo(caminho, conteudo="x"):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)


@pytest.fixture
def projeto_falso(tmp_path, monkeypatch):
    raiz = tmp_path / "proj"
    r = str(raiz)
    _arquivo(os.path.join(r, "frontend", "src", "version.ts"), 'export const APP_VERSION = "1.0.5";\n')
    _arquivo(os.path.join(r, "backend", "app", "main.py"))
    _arquivo(os.path.join(r, "backend", "app", "api", "routes", "system.py"))
    _arquivo(os.path.join(r, "frontend", "src", "app", "page.tsx"))
    _arquivo(os.path.join(r, "frontend", "node_modules", "lib", "index.js"))
    _arquivo(os.path.join(r, "frontend", ".next", "server", "app", "x.js"))
    _arquivo(os.path.join(r, "backend", "app", "__pycache__", "main.pyc"))
    _arquivo(os.path.join(r, "Backups", "antigo.zip"))
    _arquivo(os.path.join(r, "scratch_backup", "app", "velho.py"))
    _arquivo(os.path.join(r, "backend", "Backups", "nota.txt"))
    _arquivo(os.path.join(r, "backend", ".fuse_hidden0001"))
    _arquivo(os.path.join(r, "lixo.db"))
    monkeypatch.setattr(system, "get_project_root", lambda: r)
    return raiz


def test_backup_inclui_codigo_e_ignora_gerados(projeto_falso):
    resp = system.save_new_version(_admin=None)
    assert resp["version"] == "1.0.6"
    nomes = set(zipfile.ZipFile(resp["file"]).namelist())
    nomes = {n.replace("\\", "/") for n in nomes}

    assert "backend/app/main.py" in nomes
    assert "backend/app/api/routes/system.py" in nomes
    assert "frontend/src/app/page.tsx" in nomes
    assert "frontend/src/version.ts" in nomes
    # "Backups" só é ignorada na raiz; dentro de outra pasta entra.
    assert "backend/Backups/nota.txt" in nomes

    proibidos = ("node_modules/", ".next/", "__pycache__/", "scratch_backup/", "Backups/antigo.zip")
    assert not [n for n in nomes if any(p in n for p in proibidos) and not n.startswith("backend/Backups/")]
    assert "backend/.fuse_hidden0001" not in nomes
    assert "lixo.db" not in nomes


def test_pasta_ignorada_regras(tmp_path):
    raiz = str(tmp_path)
    assert system.pasta_ignorada(raiz, raiz, "Backups")
    assert not system.pasta_ignorada(raiz, os.path.join(raiz, "backend"), "Backups")
    assert not system.pasta_ignorada(raiz, os.path.join(raiz, "backend"), "app")
    assert system.pasta_ignorada(raiz, os.path.join(raiz, "frontend"), "node_modules")
