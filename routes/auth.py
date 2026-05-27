from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from validation_schemas.create_user import UserCreate
from models.user import User
from database import SessionLocal
import hashlib
import jwt
from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint for new user registration
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

# Function to verify JWT token (for protected routes)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def validate_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token error: {str(e)}")
