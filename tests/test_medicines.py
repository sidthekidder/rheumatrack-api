import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.models.medicine import Medicine
from app.models.patient import Patient
from app.models.user import User


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        display_name="Test Med User",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fake_user():
    return _make_user()


@pytest.fixture
def other_user():
    return _make_user()


@pytest.fixture
async def seed_patient(fake_user):
    async with AsyncSessionLocal() as session:
        session.add(
            Patient(
                id=fake_user.user_id,
                name="Med Patient",
                city="Bengaluru",
            )
        )
        await session.commit()


@pytest.fixture
async def seed_other_patient(other_user):
    async with AsyncSessionLocal() as session:
        session.add(
            Patient(
                id=other_user.user_id,
                name="Other Patient",
                city="Mumbai",
            )
        )
        await session.commit()


@pytest.fixture
async def cleanup(fake_user, other_user):
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Medicine).where(Medicine.patient_id == fake_user.user_id)
        )
        await session.execute(
            delete(Medicine).where(Medicine.patient_id == other_user.user_id)
        )
        await session.execute(
            delete(Patient).where(Patient.id == fake_user.user_id)
        )
        await session.execute(
            delete(Patient).where(Patient.id == other_user.user_id)
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


def _med_payload(**overrides) -> dict:
    base = {
        "drug_name": "Methotrexate",
        "brand_name": "Folitrax",
        "dose": "10mg",
        "schedule_type": "weekly",
        "dose_schedule": {
            "morning": 1,
            "afternoon": 0,
            "evening": 0,
            "night": 0,
        },
        "week_day": 2,
        "start_date": "2026-01-01",
    }
    base.update(overrides)
    return base


async def test_get_medicines_empty(
    client: AsyncClient, seed_patient, cleanup
):
    response = await client.get("/medicines")
    assert response.status_code == 200
    assert response.json() == []


async def test_post_creates_medicine_with_patient_id(
    client: AsyncClient, fake_user, seed_patient, cleanup
):
    response = await client.post("/medicines", json=_med_payload())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"]
    assert data["patient_id"] == str(fake_user.user_id)
    assert data["drug_name"] == "Methotrexate"


async def test_get_after_post_shows_row(
    client: AsyncClient, seed_patient, cleanup
):
    await client.post("/medicines", json=_med_payload())
    response = await client.get("/medicines")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["drug_name"] == "Methotrexate"


async def test_bulk_creates_n_rows(
    client: AsyncClient, seed_patient, cleanup
):
    bulk = [
        _med_payload(drug_name="Drug A", brand_name="A"),
        _med_payload(drug_name="Drug B", brand_name="B"),
        _med_payload(drug_name="Drug C", brand_name="C"),
    ]
    response = await client.post("/medicines/bulk", json=bulk)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 3
    names = {r["drug_name"] for r in rows}
    assert names == {"Drug A", "Drug B", "Drug C"}


async def test_get_returns_created_at_desc(
    client: AsyncClient, seed_patient, cleanup
):
    r1 = await client.post("/medicines", json=_med_payload(drug_name="First"))
    assert r1.status_code == 200
    # ensure created_at differs
    await asyncio.sleep(0.05)
    r2 = await client.post("/medicines", json=_med_payload(drug_name="Second"))
    assert r2.status_code == 200
    await asyncio.sleep(0.05)
    r3 = await client.post("/medicines", json=_med_payload(drug_name="Third"))
    assert r3.status_code == 200

    response = await client.get("/medicines")
    rows = response.json()
    assert [r["drug_name"] for r in rows] == ["Third", "Second", "First"]


async def test_patch_updates_partial_fields(
    client: AsyncClient, seed_patient, cleanup
):
    created = (await client.post("/medicines", json=_med_payload())).json()
    med_id = created["id"]

    response = await client.patch(
        f"/medicines/{med_id}",
        json={"dose": "15mg", "notes": "After breakfast"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["dose"] == "15mg"
    assert data["notes"] == "After breakfast"
    # untouched
    assert data["drug_name"] == "Methotrexate"
    assert data["brand_name"] == "Folitrax"
    assert data["schedule_type"] == "weekly"


async def test_patch_foreign_user_returns_404(
    client: AsyncClient,
    fake_user,
    other_user,
    seed_patient,
    seed_other_patient,
    cleanup,
):
    # create a medicine as fake_user
    created = (await client.post("/medicines", json=_med_payload())).json()
    med_id = created["id"]

    # swap to other_user and PATCH
    from app.main import app
    from app.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: other_user
    try:
        response = await client.patch(
            f"/medicines/{med_id}", json={"dose": "999mg"}
        )
    finally:
        app.dependency_overrides[get_current_user] = lambda: fake_user

    assert response.status_code == 404


async def test_delete_returns_204_and_removes_row(
    client: AsyncClient, seed_patient, cleanup
):
    created = (await client.post("/medicines", json=_med_payload())).json()
    med_id = created["id"]

    response = await client.delete(f"/medicines/{med_id}")
    assert response.status_code == 204

    list_response = await client.get("/medicines")
    assert list_response.status_code == 200
    assert list_response.json() == []


async def test_delete_foreign_user_returns_404(
    client: AsyncClient,
    fake_user,
    other_user,
    seed_patient,
    seed_other_patient,
    cleanup,
):
    created = (await client.post("/medicines", json=_med_payload())).json()
    med_id = created["id"]

    from app.main import app
    from app.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: other_user
    try:
        response = await client.delete(f"/medicines/{med_id}")
    finally:
        app.dependency_overrides[get_current_user] = lambda: fake_user

    assert response.status_code == 404

    # row should still exist for fake_user
    list_response = await client.get("/medicines")
    assert len(list_response.json()) == 1


async def test_bulk_empty_list_returns_empty(
    client: AsyncClient, seed_patient, cleanup
):
    response = await client.post("/medicines/bulk", json=[])
    assert response.status_code == 200
    assert response.json() == []
