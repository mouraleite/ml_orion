from sqlalchemy import Column, Integer, String
from app.db.database import Base

class CustomField(Base):
    __tablename__ = "custom_fields"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, index=True, default="centro_custo") # Para onde pertence essa coluna (ex: centro_custo, empresa)
    field_name = Column(String) # Nome da coluna que o usuário criou (ex: "Observações")
    field_type = Column(String, default="text") # "text", "number", "boolean", "select"
