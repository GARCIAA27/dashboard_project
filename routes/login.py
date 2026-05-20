from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User
from validation_schemas.login import LoginRequest
import hashlib
import jwt
import datetime

SECRET_KEY = "key_for_jwt_token_generation"
ALGORITHM = "HS256"

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == request.name).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    hashed_pw = hashlib.sha256(request.password.encode()).hexdigest()
    if user.password != hashed_pw:
        raise HTTPException(status_code=400, detail="Invalid password")

    expire = datetime.datetime.now() + datetime.timedelta(hours=1)
    token = jwt.encode({"sub": user.name, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}
