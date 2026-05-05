import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models.medicine import Medicine
from ..models.user import User
from ..schemas.medicine import MedicineCreate, MedicineUpdate, MedicineResponse


router = APIRouter(prefix="/medicines", tags=["medicines"])


@router.get("", response_model=list[MedicineResponse])
async def list_medicines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Medicine]:
    result = await db.execute(
        select(Medicine)
        .where(Medicine.patient_id == current_user.user_id)
        .order_by(Medicine.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=MedicineResponse)
async def create_medicine(
    payload: MedicineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Medicine:
    medicine = Medicine(
        patient_id=current_user.user_id,
        **payload.model_dump(),
    )
    db.add(medicine)
    await db.commit()
    await db.refresh(medicine)
    return medicine


@router.post("/bulk", response_model=list[MedicineResponse])
async def bulk_create_medicines(
    payload: list[MedicineCreate] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Medicine]:
    if not payload:
        return []
    medicines = [
        Medicine(patient_id=current_user.user_id, **m.model_dump())
        for m in payload
    ]
    db.add_all(medicines)
    await db.commit()
    for m in medicines:
        await db.refresh(m)
    return medicines


@router.patch("/{medicine_id}", response_model=MedicineResponse)
async def update_medicine(
    medicine_id: uuid.UUID,
    payload: MedicineUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Medicine:
    result = await db.execute(
        select(Medicine).where(Medicine.id == medicine_id)
    )
    medicine = result.scalar_one_or_none()
    if medicine is None or medicine.patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(medicine, field, value)

    await db.commit()
    await db.refresh(medicine)
    return medicine


@router.delete("/{medicine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medicine(
    medicine_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(Medicine).where(Medicine.id == medicine_id)
    )
    medicine = result.scalar_one_or_none()
    if medicine is None or medicine.patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )

    await db.delete(medicine)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
