from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.projects import Project, ProjectAccess
from validation_schemas.projects import ProjectCreate, ProjectResponse
from models.user import User
from routes.auth import validate_token
from utils.utils import get_db

router = APIRouter()

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

    access = ProjectAccess(project_id=new_project.id, user_id=user.id, role="admin")
    db.add(access)
    db.commit()

    return new_project

def get_user_id(username: str, db: Session):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.id

@router.get("/projects")
def list_projects(username: str = Depends(validate_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    projects = db.query(Project).join(ProjectAccess).filter(
        (Project.owner_id == user.id) | (ProjectAccess.user_id == user.id)
    ).all()
    return projects

