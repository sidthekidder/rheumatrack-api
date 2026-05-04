from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models.medication_log import MedicationLog
from ..models.medicine import Medicine
from ..models.user import User
from ..schemas.medication_log import MedicationLogResponse, MedicationLogUpsert


router = APIRouter(prefix="/medication-log", tags=["medication-log"])


@router.get("", response_model=list[MedicationLogResponse])
async def list_medication_log(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MedicationLog]:
    today = date.today()
    if to is None:
        to = today
    if from_ is None:
        from_ = to - timedelta(days=30)

    result = await db.execute(
        select(MedicationLog)
        .where(
            MedicationLog.patient_id == current_user.user_id,
            MedicationLog.log_date >= from_,
            MedicationLog.log_date <= to,
        )
        .order_by(MedicationLog.log_date.asc(), MedicationLog.slot.asc())
    )
    return list(result.scalars().all())


@router.put("", response_model=MedicationLogResponse)
async def upsert_medication_log(
    payload: MedicationLogUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MedicationLog:
    med = await db.scalar(
        select(Medicine).where(
            Medicine.id == payload.medicine_id,
            Medicine.patient_id == current_user.user_id,
        )
    )
    if med is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )

    stmt = (
        pg_insert(MedicationLog)
        .values(
            patient_id=current_user.user_id,
            medicine_id=payload.medicine_id,
            log_date=payload.log_date,
            slot=payload.slot,
            taken=payload.taken,
        )
        .on_conflict_do_update(
            index_elements=["patient_id", "medicine_id", "log_date", "slot"],
            set_={"taken": pg_insert(MedicationLog).excluded.taken},
        )
        .returning(MedicationLog)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()
