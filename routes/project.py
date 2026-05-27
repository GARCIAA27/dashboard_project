from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.projects import Project, ProjectAccess
from validation_schemas.project import ProjectAccessCreate, ProjectUpdate
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

#Endpoint to get specific project details, only accessible to project members (admin or user).
@router.get("/project/{project_id}/info")
def get_project(project_id: int, username: str = Depends(validate_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

#Endpoint to delete a project, only accessible to the project owner (admin).
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

#Endpoint to invite a user to a project, only accessible to project admins. The invited user will have the user role.
@router.post("/project/{project_id}/invite")
def invite_user(project_id: int, access: ProjectAccessCreate, username: str = Depends(validate_token), db: Session = Depends(get_db)):
    # Validate authentication and get current user
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Confirm current user is admin of the project
    current_user_id = get_user_id(username, db)
    admin_access = db.query(ProjectAccess).filter(
        ProjectAccess.project_id == project_id,
        ProjectAccess.user_id == current_user_id,
        ProjectAccess.role == "admin"
    ).first()
    if not admin_access:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Grant access to the invited user
    invited_user_id = get_user_id(access.username, db)
    new_access = ProjectAccess(project_id=project_id, user_id=invited_user_id, role="user")
    db.add(new_access)
    db.commit()
    return {"detail": "User invited"}

#Endpoint to update project details, only accessible to project admins.
@router.put("/project/{project_id}/info")
def update_project_info(
    project_id: int,
    project_data: ProjectUpdate,
    username: str = Depends(validate_token),
    db: Session = Depends(get_db)
):
    # Get user ID from username
    user_id = get_user_id(username, db)

    # Validate that the user has admin access to the project
    admin_access = db.query(ProjectAccess).filter(
        ProjectAccess.project_id == project_id,
        ProjectAccess.user_id == user_id,
        ProjectAccess.role == "admin"
    ).first()

    if not admin_access:
        raise HTTPException(status_code=403, detail="Access forbidden.\n Only admins can update projects")

    # Search for the project to update
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields if provided
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description

    db.commit()
    db.refresh(project)

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description
    }
