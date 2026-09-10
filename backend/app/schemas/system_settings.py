from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

class SystemSettingsBase(BaseModel):
    key: str
    value: Any

class SystemSettingsCreate(SystemSettingsBase):
    pass

class SystemSettingsUpdate(BaseModel):
    value: Any

class SystemSettingsResponse(SystemSettingsBase):
    id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
