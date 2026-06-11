from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from routes.auth import validate_token
from utils.aws_config import AWS_BUCKET_NAME, s3_client
from utils.utils import exception_access, get_db, get_document, get_user_id
from validation_schemas.documents import DocumentResponse

router = APIRouter()

# Endpoint to download a document, only accessible to project members (admin or user).
# Returns a presigned URL for S3 download.
@router.get("/document/{document_id}")
def download_document(
    document_id: int,
    username: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_id = get_user_id(username, db)
    doc = get_document(document_id, db)
    exception_access(project_id=doc.project_id, user_id=user_id, db=db)

    signed_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": AWS_BUCKET_NAME, "Key": doc.s3_key},
        ExpiresIn=3600
    )
    return {"download_url": signed_url}

#Endpoint to update a document, reupload (admin or user)  .
@router.put("/document/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(validate_token)
):
    user_id = get_user_id(current_user, db)
    doc = get_document(document_id, db)
    exception_access(doc.project_id, user_id, db)

    if file.filename != doc.filename:
        raise HTTPException(
            status_code=400,
            detail=f"Filename mismatch: expected '{doc.filename}', got '{file.filename}'"
        )
    s3_client.upload_fileobj(file.file, AWS_BUCKET_NAME, doc.s3_key)

    doc.size = file.size if hasattr(file, "size") else None

    db.commit()
    db.refresh(doc)
    return doc

# Endpoint to delete a document also deletes the file from S3.
@router.delete("/document/{document_id}")
def delete_document(
    document_id: int,
    current_user: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_id = get_user_id(current_user, db)
    doc = get_document(document_id, db)
    exception_access(project_id=doc.project_id, user_id=user_id, db=db)

    s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=doc.s3_key)

    db.delete(doc)
    db.commit()
    return {"detail": "Document deleted"}
