import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app.models.user import User

FAKE_USER = User(
    id=uuid.uuid4(),
    user_id=uuid.uuid4(),
    display_name="Test User",
    created_at=datetime.now(timezone.utc),
)

@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

async def test_get_me_returns_user_profile(client: AsyncClient):
    from app.dependencies import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    response = await client.get("/users/me")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Test User"
    assert "id" in data
    assert "user_id" in data

async def test_get_me_returns_401_without_token(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 403
