import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from routes.auth import validate_token
from database import Base
from utils.utils import get_db

# Use pytest fixtures to set up a test database and override dependencies for testing.
@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    engine.dispose()

# Override the token validation to return a fixed user for testing
def fake_validate_token():
    return {"test-user"}

app.dependency_overrides[validate_token] = fake_validate_token

@pytest.mark.asyncio
async def test_get_projects_returns_200(test_db):
    # Override the get_db dependency to use the test database
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/projects")

    assert response.status_code == status.HTTP_200_OK

    # Clean up dependency overrides after the test
    app.dependency_overrides.clear()
