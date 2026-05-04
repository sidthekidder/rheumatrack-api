import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.medication_log import MedicationLog
from app.models.medicine import Medicine
from app.models.patient import Patient
from app.models.user import User


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        display_name="Test Log User",
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
                name="Log Patient",
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
                name="Other Log Patient",
                city="Mumbai",
            )
        )
        await session.commit()


@pytest.fixture
async def seed_medicine(fake_user, seed_patient):
    med_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Medicine(
                id=med_id,
                patient_id=fake_user.user_id,
                drug_name="Methotrexate",
                brand_name="Folitrax",
                dose="10mg",
                schedule_type="weekly",
                dose_schedule={
                    "morning": 1,
                    "afternoon": 0,
                    "evening": 0,
                    "night": 0,
                },
                week_day=2,
                start_date=date(2026, 1, 1),
            )
        )
        await session.commit()
    return med_id


@pytest.fixture
async def seed_other_medicine(other_user, seed_other_patient):
    med_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Medicine(
                id=med_id,
                patient_id=other_user.user_id,
                drug_name="Sulfasalazine",
                brand_name="Saaz",
                dose="500mg",
                schedule_type="daily",
                dose_schedule={
                    "morning": 1,
                    "afternoon": 0,
                    "evening": 1,
                    "night": 0,
                },
                start_date=date(2026, 1, 1),
            )
        )
        await session.commit()
    return med_id


@pytest.fixture
async def cleanup(fake_user, other_user):
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(MedicationLog).where(
                MedicationLog.patient_id == fake_user.user_id
            )
        )
        await session.execute(
            delete(MedicationLog).where(
                MedicationLog.patient_id == other_user.user_id
            )
        )
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
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def _count_logs(patient_id: uuid.UUID) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MedicationLog).where(MedicationLog.patient_id == patient_id)
        )
        return len(list(result.scalars().all()))


async def test_get_empty_range(client: AsyncClient, seed_patient, cleanup):
    today = date.today()
    response = await client.get(
        "/medication-log",
        params={
            "from": (today - timedelta(days=7)).isoformat(),
            "to": today.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == []


async def test_put_creates_row(
    client: AsyncClient, fake_user, seed_medicine, cleanup
):
    today = date.today()
    response = await client.put(
        "/medication-log",
        json={
            "medicine_id": str(seed_medicine),
            "log_date": today.isoformat(),
            "slot": "morning",
            "taken": True,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"]
    assert data["patient_id"] == str(fake_user.user_id)
    assert data["medicine_id"] == str(seed_medicine)
    assert data["taken"] is True
    assert data["slot"] == "morning"

    # GET reflects it
    list_resp = await client.get("/medication-log")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert len(rows) == 1
    assert rows[0]["taken"] is True


async def test_put_same_key_updates_no_duplicate(
    client: AsyncClient, fake_user, seed_medicine, cleanup
):
    today = date.today()
    body = {
        "medicine_id": str(seed_medicine),
        "log_date": today.isoformat(),
        "slot": "morning",
        "taken": True,
    }
    r1 = await client.put("/medication-log", json=body)
    assert r1.status_code == 200
    first_id = r1.json()["id"]

    body["taken"] = False
    r2 = await client.put("/medication-log", json=body)
    assert r2.status_code == 200
    second_id = r2.json()["id"]

    # same row id (true upsert)
    assert first_id == second_id
    assert r2.json()["taken"] is False

    # only 1 row in DB
    assert await _count_logs(fake_user.user_id) == 1


async def test_put_second_slot_creates_second_row(
    client: AsyncClient, fake_user, seed_medicine, cleanup
):
    today = date.today()
    base = {
        "medicine_id": str(seed_medicine),
        "log_date": today.isoformat(),
        "taken": True,
    }
    r1 = await client.put("/medication-log", json={**base, "slot": "morning"})
    assert r1.status_code == 200
    r2 = await client.put("/medication-log", json={**base, "slot": "evening"})
    assert r2.status_code == 200

    assert await _count_logs(fake_user.user_id) == 2

    list_resp = await client.get("/medication-log")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert len(rows) == 2
    slots = {r["slot"] for r in rows}
    assert slots == {"morning", "evening"}


async def test_get_filters_by_date_range(
    client: AsyncClient, fake_user, seed_medicine, cleanup
):
    today = date.today()
    for offset in (5, 10, 40):
        log_date = today - timedelta(days=offset)
        resp = await client.put(
            "/medication-log",
            json={
                "medicine_id": str(seed_medicine),
                "log_date": log_date.isoformat(),
                "slot": "morning",
                "taken": True,
            },
        )
        assert resp.status_code == 200, resp.text

    response = await client.get(
        "/medication-log",
        params={
            "from": (today - timedelta(days=7)).isoformat(),
            "to": today.isoformat(),
        },
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["log_date"] == (today - timedelta(days=5)).isoformat()


async def test_put_foreign_medicine_returns_404(
    client: AsyncClient,
    fake_user,
    seed_medicine,
    seed_other_medicine,
    cleanup,
):
    today = date.today()
    response = await client.put(
        "/medication-log",
        json={
            "medicine_id": str(seed_other_medicine),
            "log_date": today.isoformat(),
            "slot": "morning",
            "taken": True,
        },
    )
    assert response.status_code == 404
    # nothing was logged for fake_user
    assert await _count_logs(fake_user.user_id) == 0


async def test_get_default_range_returns_last_30_days(
    client: AsyncClient, fake_user, seed_medicine, cleanup
):
    today = date.today()
    # within range
    in_range_date = today - timedelta(days=10)
    # outside range
    out_of_range_date = today - timedelta(days=45)

    r1 = await client.put(
        "/medication-log",
        json={
            "medicine_id": str(seed_medicine),
            "log_date": in_range_date.isoformat(),
            "slot": "morning",
            "taken": True,
        },
    )
    assert r1.status_code == 200
    r2 = await client.put(
        "/medication-log",
        json={
            "medicine_id": str(seed_medicine),
            "log_date": out_of_range_date.isoformat(),
            "slot": "morning",
            "taken": True,
        },
    )
    assert r2.status_code == 200

    response = await client.get("/medication-log")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["log_date"] == in_range_date.isoformat()
