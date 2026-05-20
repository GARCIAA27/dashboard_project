from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    password: str
    repeat_password: str
