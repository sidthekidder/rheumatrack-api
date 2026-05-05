import base64
import json

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from ..dependencies import get_current_user
from ..models.user import User
from ..services.anthropic_client import get_anthropic
from ..services.lab_scan_prompt import build_lab_scan_prompt

router = APIRouter(prefix="/scan-lab", tags=["scan"])

ALLOWED_MIMES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
ANTHROPIC_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000


@router.post("")
async def scan_lab_report(
    file: UploadFile = File(...),
    tests: str = Form(
        ...,
        description='JSON array of [id, name, unit] triples for available tests',
    ),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Returns {"reportDate": str|null, "results": [{"testId": str, "value": str}]}.

    Lab definitions live client-side, so the client passes its current LAB_TESTS
    catalog with each scan — keeps the parser aligned without DB drift.
    """
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported content type: {file.content_type}",
        )

    try:
        test_list = json.loads(tests)
        triples = [(t[0], t[1], t[2] if len(t) > 2 else "") for t in test_list]
    except (json.JSONDecodeError, TypeError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid tests payload: {exc}")

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

    prompt = build_lab_scan_prompt(triples)

    client = get_anthropic()
    message = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    media_block,
                    {"type": "text", "text": prompt},
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

    return parsed
