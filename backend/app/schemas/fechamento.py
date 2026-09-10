from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ClosedMonthBase(BaseModel):
    ano: int
    mes: int

class ClosedMonthCreate(ClosedMonthBase):
    pass

class ClosedMonthResponse(ClosedMonthBase):
    id: int
    fechado_por_id: int
    data_fechamento: datetime

    class Config:
        from_attributes = True
