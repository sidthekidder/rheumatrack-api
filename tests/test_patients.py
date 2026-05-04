import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture
def fake_user():
    return User(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        display_name="Test Patient User",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
async def cleanup_patient(fake_user):
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Patient).where(Patient.id == fake_user.user_id)
        )
        await session.commit()


@pytest.fixture
async def client(fake_user):
    from app.main import app
    from app.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: fake_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_get_me_returns_404_when_not_onboarded(
    client: AsyncClient, cleanup_patient
):
    response = await client.get("/patients/me")
    assert response.status_code == 404


async def test_post_creates_patient_with_id_from_jwt(
    client: AsyncClient, fake_user, cleanup_patient
):
    response = await client.post(
        "/patients",
        json={"name": "Alice", "city": "Bengaluru", "age": 30},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == str(fake_user.user_id)
    assert data["name"] == "Alice"
    assert data["city"] == "Bengaluru"
    assert data["age"] == 30


async def test_get_me_after_post_returns_row(
    client: AsyncClient, fake_user, cleanup_patient
):
    await client.post(
        "/patients", json={"name": "Bob", "city": "Mumbai"}
    )
    response = await client.get("/patients/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(fake_user.user_id)
    assert data["name"] == "Bob"


async def test_second_post_upserts_single_row(
    client: AsyncClient, fake_user, cleanup_patient
):
    await client.post(
        "/patients", json={"name": "First", "city": "Delhi"}
    )
    response = await client.post(
        "/patients", json={"name": "Second", "city": "Pune"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Second"
    assert data["city"] == "Pune"

    # Verify only one row exists for this id
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        count = await session.scalar(
            select(func.count()).select_from(Patient).where(
                Patient.id == fake_user.user_id
            )
        )
        assert count == 1


async def test_patch_updates_fields_and_preserves_others(
    client: AsyncClient, cleanup_patient
):
    await client.post(
        "/patients",
        json={
            "name": "Carol",
            "city": "Chennai",
            "age": 40,
            "doctor_name": "Dr. Smith",
        },
    )
    response = await client.patch(
        "/patients/me", json={"age": 41}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["age"] == 41
    assert data["name"] == "Carol"
    assert data["city"] == "Chennai"
    assert data["doctor_name"] == "Dr. Smith"


async def test_patch_returns_404_when_no_patient(
    client: AsyncClient, cleanup_patient
):
    response = await client.patch("/patients/me", json={"name": "Nope"})
    assert response.status_code == 404


async def test_post_rejects_missing_name(
    client: AsyncClient, cleanup_patient
):
    response = await client.post("/patients", json={"city": "Hyderabad"})
    # Pydantic validation -> 422
    assert response.status_code == 422


async def test_post_rejects_empty_name(
    client: AsyncClient, cleanup_patient
):
    response = await client.post(
        "/patients", json={"name": "   ", "city": "Hyderabad"}
    )
    assert response.status_code == 400


async def test_post_rejects_missing_city(
    client: AsyncClient, cleanup_patient
):
    response = await client.post("/patients", json={"name": "Dave"})
    assert response.status_code == 400


async def test_post_rejects_empty_city(
    client: AsyncClient, cleanup_patient
):
    response = await client.post(
        "/patients", json={"name": "Dave", "city": ""}
    )
    assert response.status_code == 400
