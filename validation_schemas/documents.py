from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    s3_key: str
    size: int
    upload_date: datetime

    class Config:
        from_attributes = True
