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

# Override de la validación de token
def fake_validate_token():
    return "test-user"

app.dependency_overrides[validate_token] = fake_validate_token

@pytest.mark.asyncio
async def test_get_projects_returns_200(test_db):
    def override_get_db():
        yield test_db
    app.dependency_overrides[get_db] = override_get_db

    # Crear usuario fake
    user = User(name="test-user", password=fake.password())
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Crear proyecto fake
    project = Project(
        name=fake.company(),
        owner_id=user.id
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/projects/")  # ojo con el slash

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(p["name"] == project.name for p in data)

    app.dependency_overrides.clear()
