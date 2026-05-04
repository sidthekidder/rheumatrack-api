from datetime import datetime, timezone
from uuid import UUID

import httpx

from app.config import settings

PRESCRIPTIONS_BUCKET = "prescriptions"


async def upload_prescription(
    user_id: UUID, filename: str, content: bytes, mime: str
) -> str:
    """PUT prescription to Supabase Storage. Returns the storage path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_filename = filename.replace("/", "_")
    path = f"{user_id}/{timestamp}-{safe_filename}"
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{PRESCRIPTIONS_BUCKET}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            content=content,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "Content-Type": mime,
                "x-upsert": "false",
            },
        )
    resp.raise_for_status()
    return path
