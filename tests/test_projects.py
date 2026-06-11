import pytest
from httpx import AsyncClient
from fastapi import status
from main import app  # Assuming your FastAPI app is defined in main.py

@pytest.mark.asyncio
async def test_get_projects_returns_200():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/projects")
    assert response.status_code == status.HTTP_200_OK