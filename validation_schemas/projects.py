from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: str

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    #This will allow app to return the project data in a structured way, including the owner information if needed.
    class Config:
        orm_mode = True
