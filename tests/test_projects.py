import pytest
from httpx import AsyncClient
from fastapi import status
from app.main import app
from routes.auth import validate_token  

# Override the validate_token dependency to return a fixed user for testing
def fake_validate_token():
    return {"sub": "test-user"}

app.dependency_overrides[validate_token] = fake_validate_token
@pytest.mark.asyncio
async def test_get_projects_returns_200():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/projects")
    assert response.status_code == status.HTTP_200_OK