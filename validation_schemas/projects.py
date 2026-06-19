from pydantic import BaseModel

from validation_schemas.documents import DocumentResponse


class ProjectCreate(BaseModel):
    name: str
    description: str

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    total_size: int
    documents: list[DocumentResponse] = []

    class Config:
        from_attributes = True
