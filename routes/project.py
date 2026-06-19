from io import BytesIO
from datetime import datetime
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from models.documents import Document
from models.projects import Project, ProjectAccess
from models.user import User
from routes.auth import validate_token
from utils.aws_config import AWS_BUCKET_NAME, s3_client
from utils.utils import exception_access, get_db, get_user_id, validate_file_extension
from validation_schemas.documents import DocumentResponse
from validation_schemas.project import ProjectAccessCreate, ProjectUpdate
router = APIRouter()

# Endpoint to get specific project details, only accessible to project members (admin or user).
@router.get("/project/{project_id}/info")
def get_project_info(
    project_id: int,
    username: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_id = get_user_id(username, db)
    user_access = db.query(ProjectAccess).filter_by(
        project_id=project_id,
        user_id=user_id,
    ).first()
    if not user_access:
        raise HTTPException(status_code=403, detail="Access forbidden")

    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project

# Endpoint to delete a project, only accessible to the project owner (admin).
@router.delete("/project/{project_id}")
def delete_project(
    project_id: int,
    username: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    documents = db.query(Document).filter(Document.project_id == project_id).all()
    for document in documents:
        key = document.s3_key.lstrip('/')
        s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=key)
        db.delete(document)

    db.query(ProjectAccess).filter(ProjectAccess.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return {"detail": "Project deleted"}

# Endpoint to invite a user to a project, only accessible to project admins.
# The invited user will have the user role.
@router.post("/project/{project_id}/invite")
def invite_user(
    project_id: int,
    access: ProjectAccessCreate,
    username: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
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

# Endpoint to update project details, only accessible to project admins.
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
    access = db.query(ProjectAccess).filter(
        ProjectAccess.project_id == project_id,
        ProjectAccess.user_id == user_id,
    ).first()

    if not access:
        raise HTTPException(status_code=403, detail="Access forbidden")

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

# Endpoint to upload a document to a project, only accessible to project members
# (admin or user). The document will be stored in S3 and its metadata in the database.
@router.post("/project/{project_id}/documents", response_model=DocumentResponse)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    username: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user = get_user_id(username, db)
    exception_access(project_id, user, db)

    # Safety check in the app layer
    # sanitize filename and build s3 key to avoid malformed URLs
    filename = os.path.basename(file.filename)
    validate_file_extension(filename)
    content = await file.read()
    s3_key = f"projects/{project_id}/{filename}".lstrip('/')
    s3_client.upload_fileobj(BytesIO(content), AWS_BUCKET_NAME, s3_key)

    doc = Document(
        project_id=project_id,
        filename=filename,
        s3_key=s3_key,
        size=len(content),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

# Endpoint to return all documents of a project, only accessible to project members
# (admin or user).
@router.get("/project/{project_id}/documents", response_model=list[DocumentResponse])
def list_documents(project_id: int, username: str = Depends(validate_token),
                   db: Session = Depends(get_db)):
    user_id = get_user_id(username, db)
    exception_access(project_id, user_id, db)

    docs = db.query(Document).filter_by(project_id=project_id).all()
    return docs
