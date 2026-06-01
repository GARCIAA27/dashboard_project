from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    url: str
    size: int | None

    class Config:
        orm_mode = True