from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.projects import Project
from models.user import User
from validation_schemas.project import ProjectCreate, ProjectResponse
from routes.auth import validate_token

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/projects", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db), username: str = Depends(validate_token)):
    #Find the user based on the username extracted from the token
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_project = Project(name=project.name, description=project.description, owner_id=user.id)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project
