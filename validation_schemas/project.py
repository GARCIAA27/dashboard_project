from typing import Optional
from pydantic import BaseModel

class ProjectAccessCreate(BaseModel):
    username: str

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None