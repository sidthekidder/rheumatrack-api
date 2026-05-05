import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import settings

PRESCRIPTIONS_BUCKET = "prescriptions"

log = logging.getLogger(__name__)


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
                "apikey": settings.supabase_service_role_key,
                "Content-Type": mime,
                "x-upsert": "true",
            },
        )
    if resp.is_error:
        log.error(
            "Supabase storage upload failed: %s %s — %s",
            resp.status_code,
            url,
            resp.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed ({resp.status_code}): {resp.text}",
        )
    return path
