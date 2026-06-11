import datetime
import os

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.user import User
from routes.auth import verify_password
from utils.utils import get_db
from validation_schemas.login import LoginRequest

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

router = APIRouter()

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == request.name).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid password")

    expire = datetime.datetime.now() + datetime.timedelta(hours=1)
    to_encode = {"sub": user.name, "exp": expire.timestamp()}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}
