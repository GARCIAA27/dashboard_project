import os

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models.user import User
from utils.utils import get_db
from validation_schemas.create_user import UserCreate

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(str(password))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Endpoint for new user registration
@router.post("/auth")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if user.password != user.repeat_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Check if user already exists by name or email
    existing_name = db.query(User).filter(User.name == user.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="User already exists")

    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already in use")

    hashed_pw = hash_password(user.password)
    new_user = User(name=user.name, email=user.email, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "name": new_user.name}

# Function to verify JWT token (for protected routes)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def validate_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return username
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidSignatureError as exc:
        raise HTTPException(status_code=401, detail="Invalid signature") from exc
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token error: {str(e)}") from e
