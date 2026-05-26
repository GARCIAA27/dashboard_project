from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.projects import Project, ProjectAccess
from validation_schemas.project import ProjectAccessCreate
from models.user import User
from routes.auth import validate_token

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_id(username: str, db: Session):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.id

@router.get("/project/{project_id}/info")
def get_project(project_id: int, username: str = Depends(validate_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/project/{project_id}")
def delete_project(project_id: int, username: str = Depends(validate_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"detail": "Project deleted"}

@router.post("/project/{project_id}/invite")
def invite_user(project_id: int, access: ProjectAccessCreate, username: str = Depends(validate_token), db: Session = Depends(get_db)):
    # Validate authentication and get current user
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Confirm current user is admin of the project
    current_user = db.query(User).filter(User.name == username).first()
    admin_access = db.query(ProjectAccess).filter(
        ProjectAccess.project_id == project_id,
        ProjectAccess.user_id == current_user.id,
        ProjectAccess.role == "admin"
    ).first()
    if not admin_access:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Grant access to the invited user
    new_access = ProjectAccess(project_id=project_id, user_id=access.user_id, role=access.role)
    db.add(new_access)
    db.commit()
    return {"detail": "User invited"}

