import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from faker import Faker

from app.main import app
from routes.auth import validate_token
from database import Base
from utils.utils import get_db
from models.user import *
from models.projects import *
from models.documents import *

fake = Faker()

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

@pytest.mark.asyncio
async def test_get_projects_returns_200(test_db):
    # Override db to use the test database
    def override_get_db():
        yield test_db
    app.dependency_overrides[get_db] = override_get_db

    # Create user fake
    user = User(name="test-user", password=fake.password())
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Create project fake
    project = Project(
        name=fake.company(),
        description=fake.text(),
        owner_id=user.id
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)

    project_access = ProjectAccess(
        project_id=project.id,
        user_id=user.id,
        role="admin"
    )
    test_db.add(project_access)
    test_db.commit()

    # Override validate_token to return the test user
    def fake_validate_token():
        return "test-user"
    app.dependency_overrides[validate_token] = fake_validate_token

    # Endpoint to test
    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
        response = await ac.get("/projects")  # usa la ruta exacta definida en tu router

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(p["name"] == project.name for p in data)

    # Clean up overrides
    app.dependency_overrides.clear()
