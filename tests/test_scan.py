import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User


SAMPLE_PARSED = {
    "diagnosis": "RA",
    "medications": [
        {
            "drugName": "MTX",
            "dose": "15mg",
            "scheduleType": "weekly",
            "doseSchedule": {
                "morning": 1,
                "afternoon": 0,
                "evening": 0,
                "night": 0,
            },
            "weekDay": 2,
            "foodTiming": "after_food",
            "durationDays": 30,
        }
    ],
}


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        display_name="Test Scan User",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fake_user():
    return _make_user()


@pytest.fixture
async def seed_patient(fake_user):
    async with AsyncSessionLocal() as session:
        session.add(
            Patient(
                id=fake_user.user_id,
                name="Scan Patient",
                city="Bengaluru",
            )
        )
        await session.commit()


@pytest.fixture
async def cleanup(fake_user):
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Prescription).where(Prescription.patient_id == fake_user.user_id)
        )
        await session.execute(
            delete(Patient).where(Patient.id == fake_user.user_id)
        )
        await session.commit()


def _build_mock_anthropic(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text

    msg = MagicMock()
    msg.content = [block]

    client = MagicMock()
    client.messages.create = AsyncMock(return_value=msg)
    return client


@pytest.fixture
def mock_anthropic_ok(monkeypatch):
    import json as _json

    client = _build_mock_anthropic(_json.dumps(SAMPLE_PARSED))
    monkeypatch.setattr("app.routers.scan.get_anthropic", lambda: client)
    return client


@pytest.fixture
def mock_storage(monkeypatch, fake_user):
    storage_mock = AsyncMock(
        return_value=f"{fake_user.user_id}/20260504T000000Z-rx.pdf"
    )
    monkeypatch.setattr("app.routers.scan.upload_prescription", storage_mock)
    return storage_mock


@pytest.fixture
async def client(fake_user):
    from app.dependencies import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: fake_user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def test_post_pdf_returns_parsed_and_inserts_row(
    client: AsyncClient,
    fake_user,
    seed_patient,
    mock_anthropic_ok,
    mock_storage,
    cleanup,
):
    response = await client.post(
        "/scan",
        files={"file": ("rx.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["parsed"] == SAMPLE_PARSED
    assert body["prescription_id"]

    # Anthropic call args: media block is document
    call_args = mock_anthropic_ok.messages.create.call_args
    assert call_args.kwargs["model"] == "claude-sonnet-4-6"
    assert call_args.kwargs["max_tokens"] == 3000
    media = call_args.kwargs["messages"][0]["content"][0]
    assert media["type"] == "document"
    assert media["source"]["media_type"] == "application/pdf"

    # Row exists
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Prescription).where(
                Prescription.patient_id == fake_user.user_id
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) == 1
        assert rows[0].raw_response == SAMPLE_PARSED
        assert rows[0].storage_path is not None
        assert rows[0].mime_type == "application/pdf"


async def test_post_image_uses_image_block(
    client: AsyncClient,
    fake_user,
    seed_patient,
    mock_anthropic_ok,
    mock_storage,
    cleanup,
):
    response = await client.post(
        "/scan",
        files={"file": ("rx.jpg", b"\xff\xd8\xff fake jpeg", "image/jpeg")},
    )
    assert response.status_code == 200, response.text

    call_args = mock_anthropic_ok.messages.create.call_args
    media = call_args.kwargs["messages"][0]["content"][0]
    assert media["type"] == "image"
    assert media["source"]["media_type"] == "image/jpeg"


async def test_post_rejects_unsupported_content_type(
    client: AsyncClient,
    seed_patient,
    cleanup,
):
    response = await client.post(
        "/scan",
        files={"file": ("rx.txt", b"not a prescription", "text/plain")},
    )
    assert response.status_code == 415


async def test_post_returns_502_on_malformed_json(
    client: AsyncClient,
    fake_user,
    seed_patient,
    mock_storage,
    monkeypatch,
    cleanup,
):
    bad_client = _build_mock_anthropic("this is not json at all {")
    monkeypatch.setattr("app.routers.scan.get_anthropic", lambda: bad_client)

    response = await client.post(
        "/scan",
        files={"file": ("rx.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 502

    # No row was inserted on failure
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Prescription).where(
                Prescription.patient_id == fake_user.user_id
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) == 0


async def test_raw_response_matches_parsed_dict(
    client: AsyncClient,
    fake_user,
    seed_patient,
    mock_anthropic_ok,
    mock_storage,
    cleanup,
):
    response = await client.post(
        "/scan",
        files={"file": ("rx.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 200
    parsed = response.json()["parsed"]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Prescription).where(
                Prescription.patient_id == fake_user.user_id
            )
        )
        row = result.scalar_one()
        assert row.raw_response == parsed


async def test_storage_path_persisted(
    client: AsyncClient,
    fake_user,
    seed_patient,
    mock_anthropic_ok,
    mock_storage,
    cleanup,
):
    response = await client.post(
        "/scan",
        files={"file": ("rx.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 200

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Prescription).where(
                Prescription.patient_id == fake_user.user_id
            )
        )
        row = result.scalar_one()
        assert row.storage_path is not None
        assert str(fake_user.user_id) in row.storage_path


async def test_strips_json_code_fences(
    client: AsyncClient,
    fake_user,
    seed_patient,
    mock_storage,
    monkeypatch,
    cleanup,
):
    import json as _json

    fenced = "```json\n" + _json.dumps(SAMPLE_PARSED) + "\n```"
    fenced_client = _build_mock_anthropic(fenced)
    monkeypatch.setattr("app.routers.scan.get_anthropic", lambda: fenced_client)

    response = await client.post(
        "/scan",
        files={"file": ("rx.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["parsed"] == SAMPLE_PARSED
