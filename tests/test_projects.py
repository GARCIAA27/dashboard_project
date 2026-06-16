import sys
from pathlib import Path
import io

import pytest
from faker import Faker
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import routes.auth as auth_routes
import routes.login as login_routes
import routes.project as project_routes
import routes.document as document_routes
from app.main import app
from routes.auth import validate_token, hash_password
from database import Base
from utils.utils import get_db
from models.user import User
from models.projects import Project, ProjectAccess
from models.documents import Document

fake = Faker()

auth_routes.SECRET_KEY = "testsecret"
auth_routes.ALGORITHM = "HS256"
login_routes.SECRET_KEY = "testsecret"
login_routes.ALGORITHM = "HS256"


class DummyS3Client:
    def upload_fileobj(self, file_obj, bucket, key):
        pass

    def generate_presigned_url(self, client_method, Params=None, ExpiresIn=None):
        return f"https://example.com/{Params['Key']}"

    def delete_object(self, Bucket=None, Key=None):
        pass


dummy_s3 = DummyS3Client()


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


@pytest.fixture
def override_db(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield test_db
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def patch_s3(monkeypatch):
    monkeypatch.setattr(project_routes, "s3_client", dummy_s3)
    monkeypatch.setattr(document_routes, "s3_client", dummy_s3)


def create_user(test_db, name=None, password=None):
    raw_password = password or fake.password()
    user = User(name=name or fake.user_name(), password=hash_password(raw_password))
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user, raw_password


def create_project_with_admin(test_db, owner):
    project = Project(name=fake.company(), description=fake.text(), owner_id=owner.id)
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    access = ProjectAccess(project_id=project.id, user_id=owner.id, role="admin")
    test_db.add(access)
    test_db.commit()
    return project


def create_document(test_db, project, filename="test-file.txt", size=42):
    document = Document(
        project_id=project.id,
        filename=filename,
        s3_key=f"projects/{project.id}/{filename}",
        size=size,
    )
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


@pytest.mark.asyncio
async def test_auth_register(override_db):
    password = fake.password()
    payload = {
        "name": fake.user_name(),
        "password": password,
        "repeat_password": password,
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/auth", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == payload["name"]


@pytest.mark.asyncio
async def test_login_returns_token(override_db, test_db):
    user, password = create_user(test_db)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/login", json={"name": user.name, "password": password})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_create_project(override_db, test_db):
    user, _ = create_user(test_db)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    project_payload = {"name": fake.company(), "description": fake.text()}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/projects", json=project_payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == project_payload["name"]


@pytest.mark.asyncio
async def test_list_projects(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/projects")

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert any(item["name"] == project.name for item in result)


@pytest.mark.asyncio
async def test_get_project_info(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/project/{project.id}/info")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == project.id


@pytest.mark.asyncio
async def test_invite_user(override_db, test_db):
    owner, _ = create_user(test_db)
    invitee, _ = create_user(test_db)
    project = create_project_with_admin(test_db, owner)

    def fake_validate_token():
        return owner.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(f"/project/{project.id}/invite", json={"username": invitee.name})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "User invited"
    access = test_db.query(ProjectAccess).filter_by(project_id=project.id, user_id=invitee.id).first()
    assert access is not None
    assert access.role == "user"


@pytest.mark.asyncio
async def test_update_project_info(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    patch = {"name": "Updated Project", "description": "Updated description."}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(f"/project/{project.id}/info", json=patch)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == patch["name"]
    assert data["description"] == patch["description"]


@pytest.mark.asyncio
async def test_upload_document(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/project/{project.id}/documents",
            files={"file": ("test.txt", b"hello world")},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["project_id"] == project.id


@pytest.mark.asyncio
async def test_list_documents(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)
    document = create_document(test_db, project)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/project/{project.id}/documents")

    assert response.status_code == status.HTTP_200_OK
    items = response.json()
    assert any(item["id"] == document.id for item in items)


@pytest.mark.asyncio
async def test_download_document(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)
    document = create_document(test_db, project)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/document/{document.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["download_url"] == f"https://example.com/{document.s3_key}"


@pytest.mark.asyncio
async def test_update_document(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)
    document = create_document(test_db, project)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            f"/document/{document.id}",
            files={"file": (document.filename, b"updated content")},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["filename"] == document.filename


@pytest.mark.asyncio
async def test_delete_document(override_db, test_db):
    user, _ = create_user(test_db)
    project = create_project_with_admin(test_db, user)
    document = create_document(test_db, project)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(f"/document/{document.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Document deleted"

