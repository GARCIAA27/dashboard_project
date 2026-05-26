
from typing import Optional
from pydantic import BaseModel


class ProjectAccessCreate(BaseModel):
    user_id: int
    role: str

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None