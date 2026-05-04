import uuid
from datetime import datetime
from pydantic import BaseModel

class UserResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
