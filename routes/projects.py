from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.projects import Project, ProjectAccess
from routes.auth import validate_token
from utils.utils import get_db, get_user_id
from validation_schemas.projects import ProjectCreate, ProjectResponse

router = APIRouter()

@router.post("/projects", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db),
                   username: str = Depends(validate_token)):
    # Find the user based on the username extracted from the token
    user_id = get_user_id(username, db)
    new_project = Project(name=project.name, description=project.description, owner_id=user_id)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    access = ProjectAccess(project_id=new_project.id, user_id=user_id, role="admin")
    db.add(access)
    db.commit()

    return new_project

@router.get("/projects")
def list_projects(username: str = Depends(validate_token), db: Session = Depends(get_db)):
    user_id = get_user_id(username, db)
    projects = db.query(Project).outerjoin(ProjectAccess).filter(
        (Project.owner_id == user_id) | (ProjectAccess.user_id == user_id)
    ).all()
    return projects
