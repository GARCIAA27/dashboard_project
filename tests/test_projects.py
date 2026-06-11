import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, MagicMock
from app.main import app

@pytest.mark.asyncio
async def test_get_projects_returns_200():
    # Using patch to mock the database session and return a predefined response
    with patch("app.database.SessionLocal", MagicMock()):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/projects")
    assert response.status_code == status.HTTP_200_OK
