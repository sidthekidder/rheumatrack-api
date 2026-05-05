import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models.flare_entry import FlareEntry
from ..models.user import User
from ..schemas.flare_entry import FlareEntryUpsert, FlareEntryResponse


router = APIRouter(prefix="/flare-entries", tags=["flare-entries"])


@router.get("", response_model=list[FlareEntryResponse])
async def list_flare_entries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FlareEntry]:
    result = await db.execute(
        select(FlareEntry)
        .where(FlareEntry.patient_id == current_user.user_id)
        .order_by(FlareEntry.entry_date.desc())
    )
    return list(result.scalars().all())


@router.put("", response_model=FlareEntryResponse)
async def upsert_flare_entry(
    payload: FlareEntryUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FlareEntry:
    stmt = (
        pg_insert(FlareEntry)
        .values(
            patient_id=current_user.user_id,
            entry_date=payload.entry_date,
            pain=payload.pain,
            stiffness_min=payload.stiffness_min,
            fatigue=payload.fatigue,
            joints=payload.joints,
            notes=payload.notes,
        )
        .on_conflict_do_update(
            index_elements=["patient_id", "entry_date"],
            set_={
                "pain": payload.pain,
                "stiffness_min": payload.stiffness_min,
                "fatigue": payload.fatigue,
                "joints": payload.joints,
                "notes": payload.notes,
            },
        )
        .returning(FlareEntry)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flare_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    entry = await db.scalar(
        select(FlareEntry).where(FlareEntry.id == entry_id)
    )
    if entry is None or entry.patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flare entry not found",
        )
    await db.delete(entry)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
