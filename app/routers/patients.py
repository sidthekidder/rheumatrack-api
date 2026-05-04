from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..dependencies import get_current_user
from ..models.patient import Patient
from ..models.user import User
from ..schemas.patient import PatientCreate, PatientUpdate, PatientResponse

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me", response_model=PatientResponse)
async def get_my_patient(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    result = await db.execute(
        select(Patient).where(Patient.id == current_user.user_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not onboarded",
        )
    return patient


@router.post("", response_model=PatientResponse)
async def upsert_patient(
    payload: PatientCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    if not payload.name or not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name must be non-empty",
        )
    if not payload.city or not payload.city.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="city must be non-empty",
        )

    result = await db.execute(
        select(Patient).where(Patient.id == current_user.user_id)
    )
    patient = result.scalar_one_or_none()

    data = payload.model_dump(exclude_unset=True)

    if patient is None:
        patient = Patient(id=current_user.user_id, **data)
        db.add(patient)
    else:
        for field, value in data.items():
            setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)
    return patient


@router.patch("/me", response_model=PatientResponse)
async def patch_my_patient(
    payload: PatientUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    result = await db.execute(
        select(Patient).where(Patient.id == current_user.user_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not onboarded",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)
    return patient
