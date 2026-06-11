import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.main import app
from project_dashboard.routes.auth import validate_token
from project_dashboard.database import Base
# Import all models to ensure they're registered with Base
from project_dashboard.models.user import User  # Adjust import path as needed
from project_dashboard.models.project import Project  # Adjust import path as needed
from project_dashboard.utils.utils import get_db

# Use an in-memory SQLite database for testing
@pytest.fixture(scope="function")
def test_db():
    # Use StaticPool to avoid thread issues with SQLite
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    yield db
    
    db.close()
    engine.dispose()

# Override the validate_token dependency
def fake_validate_token():
    return {"sub": "test-user"}

app.dependency_overrides[validate_token] = fake_validate_token

@pytest.mark.asyncio
async def test_get_projects_returns_200(test_db):
    # Override the database dependency to use test_db
    def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/projects")
        
        assert response.status_code == status.HTTP_200_OK
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()