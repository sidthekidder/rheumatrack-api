import base64
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models.prescription import Prescription
from ..models.user import User
from ..schemas.prescription import ScanResponse
from ..services.anthropic_client import get_anthropic
from ..services.scan_prompt import SCAN_PROMPT
from ..services.storage import upload_prescription

router = APIRouter(prefix="/scan", tags=["scan"])

ALLOWED_MIMES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
ANTHROPIC_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 3000


@router.post("", response_model=ScanResponse)
async def scan_prescription(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported content type: {file.content_type}",
        )

    content = await file.read()
    b64 = base64.standard_b64encode(content).decode("ascii")

    if file.content_type == "application/pdf":
        media_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        }
    else:
        media_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": file.content_type,
                "data": b64,
            },
        }

    client = get_anthropic()
    message = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    media_block,
                    {"type": "text", "text": SCAN_PROMPT},
                ],
            }
        ],
    )

    text = next(
        (block.text for block in message.content if getattr(block, "type", None) == "text"),
        "{}",
    )
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="anthropic returned non-JSON response",
        )

    storage_path = await upload_prescription(
        current_user.user_id,
        file.filename or "rx",
        content,
        file.content_type,
    )

    prescription = Prescription(
        patient_id=current_user.user_id,
        storage_path=storage_path,
        mime_type=file.content_type,
        raw_response=parsed,
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)

    return ScanResponse(prescription_id=prescription.id, parsed=parsed)
