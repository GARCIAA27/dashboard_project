from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: str

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    total_size: int

    class Config:
        from_attributes = True
