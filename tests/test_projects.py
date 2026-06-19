import pytest
from faker import Faker
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from database import Base
from models.documents import Document
from models.projects import Project, ProjectAccess
from models.user import User
from routes.auth import validate_token, hash_password
import routes.auth as auth_routes
import routes.document as document_routes
import routes.login as login_routes
import routes.project as project_routes
from utils.utils import get_db

# pylint: disable=redefined-outer-name
fake = Faker()

auth_routes.SECRET_KEY = "testsecret"
auth_routes.ALGORITHM = "HS256"
login_routes.SECRET_KEY = "testsecret"
login_routes.ALGORITHM = "HS256"

# Dummy S3 client for testing
# There are deviations from pylint with unused arguments because the methods need to
# match the boto3 interface, even if we don't use all parameters in the dummy implementation.
class DummyS3Client:
    def upload_fileobj(self, file_obj, bucket, key):  # pylint: disable=unused-argument
        pass

    def generate_presigned_url(self, method, **kwargs):  # pylint: disable=unused-argument
        return f"https://example.com/{kwargs['Params']['Key']}"

    def delete_object(self, **kwargs):  # pylint: disable=unused-argument
        pass


dummy_s3 = DummyS3Client()


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session_local()
    yield db
    db.close()
    engine.dispose()


@pytest.fixture(autouse=True)
def override_db(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield db_session
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def patch_s3(monkeypatch):
    monkeypatch.setattr(project_routes, "s3_client", dummy_s3)
    monkeypatch.setattr(document_routes, "s3_client", dummy_s3)


def create_user(db_session, name=None, email=None, password=None):
    raw_password = password or fake.password()
    user = User(
        name=name or fake.user_name(),
        email=email or fake.email(),
        password=hash_password(raw_password),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, raw_password


def create_project_with_admin(db_session, owner):
    project = Project(name=fake.company(), description=fake.text(), owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    access = ProjectAccess(project_id=project.id, user_id=owner.id, role="admin")
    db_session.add(access)
    db_session.commit()
    return project


def create_document(db_session, project, filename="test-file.pdf", size=42):
    document = Document(
        project_id=project.id,
        filename=filename,
        s3_key=f"projects/{project.id}/{filename}",
        size=size,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.mark.asyncio
async def test_auth_register():
    password = fake.password()
    payload = {
        "name": fake.user_name(),
        "email": fake.email(),
        "password": password,
        "repeat_password": password,
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/auth", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == payload["name"]


@pytest.mark.asyncio
async def test_login_returns_token(db_session):
    user, password = create_user(db_session)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/login", json={"name": user.name, "password": password})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_create_project(db_session):
    user, _ = create_user(db_session)

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
async def test_list_projects(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)
    create_document(db_session, project, filename="project-file.pdf")

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/projects")

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert any(item["name"] == project.name for item in result)
    assert any(item["documents"] for item in result if item["name"] == project.name)


@pytest.mark.asyncio
async def test_get_project_info(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/project/{project.id}/info")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == project.id


@pytest.mark.asyncio
async def test_invite_user(db_session):
    owner, _ = create_user(db_session)
    invitee, _ = create_user(db_session)
    project = create_project_with_admin(db_session, owner)

    def fake_validate_token():
        return owner.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(f"/project/{project.id}/invite", json={"username": invitee.name})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "User invited"
    access = db_session.query(ProjectAccess).filter_by(
        project_id=project.id, user_id=invitee.id
    ).first()
    assert access is not None
    assert access.role == "user"


@pytest.mark.asyncio
async def test_update_project_info(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)

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
async def test_upload_document(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/project/{project.id}/documents",
            files={"file": ("test.pdf", b"hello world")},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["project_id"] == project.id
    assert data["size"] == len(b"hello world")
    assert "upload_date" in data


@pytest.mark.asyncio
async def test_list_documents(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)
    document = create_document(db_session, project)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/project/{project.id}/documents")

    assert response.status_code == status.HTTP_200_OK
    items = response.json()
    assert any(item["id"] == document.id for item in items)


@pytest.mark.asyncio
async def test_download_document(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)
    document = create_document(db_session, project)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/document/{document.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["download_url"] == f"https://example.com/{document.s3_key}"


@pytest.mark.asyncio
async def test_update_document(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)
    document = create_document(db_session, project)

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
async def test_delete_document(db_session):
    user, _ = create_user(db_session)
    project = create_project_with_admin(db_session, user)
    document = create_document(db_session, project)

    def fake_validate_token():
        return user.name

    app.dependency_overrides[validate_token] = fake_validate_token

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(f"/document/{document.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Document deleted"
