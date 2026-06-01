from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.documents import Document
from models.projects import ProjectAccess
from models.user import User
from routes.auth import validate_token
from utils.utils import get_user_id, get_db
from utils.aws_config import s3_client, AWS_BUCKET_NAME
from fastapi import UploadFile, File
from validation_schemas.documents import DocumentResponse
router = APIRouter()

#Endpoint to download a document, only accessible to project members (admin or user). Returns a presigned URL for S3 download.
@router.get("/document/{document_id}")
def download_document(document_id: int, current_user: str = Depends(validate_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == current_user).first()
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    access = db.query(ProjectAccess).filter_by(project_id=doc.project_id, user_id=user.id).first()
    if not access:
        raise HTTPException(status_code=403, detail="Access forbidden")

    signed_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": "mybucket", "Key": doc.url.replace("s3://mybucket/", "")},
        ExpiresIn=3600
    )
    return {"download_url": signed_url}

#Endpoint to update a document's metadata (e.g., filename), only accessible to project members (admin or user)  .
@router.put("/document/{document_id}", response_model=DocumentResponse)
def update_document(document_id: int, file: UploadFile = File(None), current_user: str = Depends(validate_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == current_user).first()
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    access = db.query(ProjectAccess).filter_by(project_id=doc.project_id, user_id=user.id).first()
    if not access:
        raise HTTPException(status_code=403, detail="Access forbidden")

    if file:
        s3_key = f"projects/{doc.project_id}/{file.filename}"
        s3_client.upload_fileobj(file.file, "mybucket", s3_key)
        doc.filename = file.filename
        doc.url = f"s3://mybucket/{s3_key}"
        doc.size = file.size

    db.commit()
    db.refresh(doc)
    return doc

#Endpoint to delete a document also deletes the file from S3.
@router.delete("/document/{document_id}")
def delete_document(document_id: int, current_user: str = Depends(validate_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == current_user).first()
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    access = db.query(ProjectAccess).filter_by(project_id=doc.project_id, user_id=user.id).first()
    if not access:
        raise HTTPException(status_code=403, detail="Access forbidden")

    s3_client.delete_object(Bucket="mybucket", Key=doc.url.replace("s3://mybucket/", ""))

    db.delete(doc)
    db.commit()
    return {"detail": "Document deleted"}