import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models.appointment import Appointment
from ..models.user import User
from ..schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
)


router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Appointment]:
    result = await db.execute(
        select(Appointment)
        .where(Appointment.patient_id == current_user.user_id)
        .order_by(Appointment.appointment_date.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=AppointmentResponse)
async def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Appointment:
    appt = Appointment(
        patient_id=current_user.user_id,
        **payload.model_dump(),
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return appt


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Appointment:
    appt = await db.scalar(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    if appt is None or appt.patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(appt, field, value)

    await db.commit()
    await db.refresh(appt)
    return appt


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    appt = await db.scalar(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    if appt is None or appt.patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    await db.delete(appt)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
