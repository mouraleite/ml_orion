import os
from typing import List, Dict

class SharePointService:
    """
    Camada de Integração com Microsoft SharePoint (Graph API).
    Atualmente em modo Mock para simular o comportamento de um GED 
    (Gestão Eletrônica de Documentos) por Viabilidade.
    """

    def __init__(self):
        self.tenant_id = os.getenv("SP_TENANT_ID")
        self.client_id = os.getenv("SP_CLIENT_ID")
        self.client_secret = os.getenv("SP_CLIENT_SECRET")
        self.site_id = os.getenv("SP_SITE_ID")
        
        # Em memória (Mock DB de Arquivos)
        self.mock_db = {}

    def get_project_folder(self, project_name: str) -> str:
        """
        Retorna o ID ou Caminho da pasta no SharePoint. Cria se não existir.
        """
        return f"/Projetos/{project_name.replace(' ', '_')}"

    def list_documents(self, phase_id: int, project_name: str) -> List[Dict]:
        """
        Lista os arquivos existentes na pasta do projeto.
        """
        folder = self.get_project_folder(project_name)
        if folder not in self.mock_db:
            self.mock_db[folder] = [
                {"id": "doc1", "name": f"Alvará_{project_name}.pdf", "size": "1.2 MB", "date": "2023-10-01"},
                {"id": "doc2", "name": f"Quadro_Resumo_{project_name}.xlsx", "size": "450 KB", "date": "2023-10-15"},
            ]
        return self.mock_db[folder]

    def upload_document(self, phase_id: int, project_name: str, file_name: str, file_size: str) -> Dict:
        """
        Simula o upload de um documento para a pasta do projeto no SharePoint.
        """
        folder = self.get_project_folder(project_name)
        if folder not in self.mock_db:
            self.mock_db[folder] = []
            
        new_doc = {
            "id": f"doc_{len(self.mock_db[folder]) + 1}",
            "name": file_name,
            "size": file_size,
            "date": "2023-11-01" # Mock date
        }
        self.mock_db[folder].append(new_doc)
        return new_doc

    def delete_document(self, phase_id: int, project_name: str, doc_id: str) -> bool:
        folder = self.get_project_folder(project_name)
        if folder in self.mock_db:
            self.mock_db[folder] = [d for d in self.mock_db[folder] if d["id"] != doc_id]
            return True
        return False

    def rename_document(self, phase_id: int, project_name: str, doc_id: str, new_name: str) -> bool:
        folder = self.get_project_folder(project_name)
        if folder in self.mock_db:
            for d in self.mock_db[folder]:
                if d["id"] == doc_id:
                    d["name"] = new_name
                    return True
        return False

sp_service = SharePointService()
