import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models.lab_report import LabReport
from ..models.user import User
from ..schemas.lab_report import LabReportCreate, LabReportResponse


router = APIRouter(prefix="/lab-reports", tags=["lab-reports"])


@router.get("", response_model=list[LabReportResponse])
async def list_lab_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LabReport]:
    result = await db.execute(
        select(LabReport)
        .where(LabReport.patient_id == current_user.user_id)
        .order_by(LabReport.report_date.desc(), LabReport.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=LabReportResponse)
async def create_lab_report(
    payload: LabReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabReport:
    report = LabReport(
        patient_id=current_user.user_id,
        report_date=payload.report_date,
        results=[r.model_dump() for r in payload.results],
        source=payload.source,
        notes=payload.notes,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lab_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    report = await db.scalar(
        select(LabReport).where(LabReport.id == report_id)
    )
    if report is None or report.patient_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab report not found",
        )
    await db.delete(report)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
