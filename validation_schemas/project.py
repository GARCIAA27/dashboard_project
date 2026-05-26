
from pydantic import BaseModel


class ProjectAccessCreate(BaseModel):
    user_id: int
    role: str
