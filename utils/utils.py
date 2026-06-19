import os

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from database import SESSION_LOCAL
from models.documents import Document
from models.projects import ProjectAccess
from models.user import User

def get_db():
    db = SESSION_LOCAL()
    try:
        yield db
    finally:
        db.close()

def get_user_id(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.id

def exception_access(project_id: int, user_id: int, db: Session = Depends(get_db)):
    access = db.query(ProjectAccess).filter_by(project_id=project_id, user_id=user_id).first()
    if not access:
        raise HTTPException(status_code=403, detail="Access forbidden")


def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def validate_file_extension(filename: str):
    extension = os.path.splitext(filename)[1].lower()
    if extension not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .pdf and .docx are allowed."
        )
