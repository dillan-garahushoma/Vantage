from pydantic import BaseModel
from typing import Optional, List

class KimiStartRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: str
    source: Optional[str] = "coverage_check"

class KimiRunLog(BaseModel):
    message: str
    ts: float

class KimiStatusResponse(BaseModel):
    run_id: str
    status: str
    progress: int
    logs: List[KimiRunLog] = []

    class Config:
        orm_mode = True

class KimiConfig(BaseModel):
    mock_mode: bool = True
    mapbox_key: Optional[str] = None
    whatsapp_key: Optional[str] = None
