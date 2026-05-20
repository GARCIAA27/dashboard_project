from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from validation_schemas.create_user import UserCreate
from models.user import User
from database import SessionLocal
import hashlib

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/auth")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if user.password != user.repeat_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Check if user already exists
    existing = db.query(User).filter(User.name == user.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw = hashlib.sha256(user.password.encode()).hexdigest()
    new_user = User(name=user.name, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "name": new_user.name}

