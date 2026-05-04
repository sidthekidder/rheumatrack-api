import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_db
from .middleware.auth import verify_token
from .models.user import User

async def get_current_user(
    payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    raw_id = payload.get("sub")
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    user_id = uuid.UUID(raw_id)
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )
    return user
