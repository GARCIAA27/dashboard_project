import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from routes.auth import validate_token
from database import Base  # Import your Base model class

# Use an in-memory SQLite database for testing
@pytest.fixture(scope="function")
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    yield db
    db.close()

# Override the validate_token dependency
def fake_validate_token():
    return {"sub": "test-user"}

app.dependency_overrides[validate_token] = fake_validate_token

@pytest.mark.asyncio
async def test_get_projects_returns_200(test_db):
    # Override the database dependency to use test_db
    from utils.utils import get_db
    
    def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/projects")
    
    assert response.status_code == status.HTTP_200_OK