from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class RefreshSessionCreateRepo(BaseModel):
    id: UUID
    user_id: int
    token: str = Field(repr=False)
    expires_at: AwareDatetime


class RefreshSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: int
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None


class RefreshSessionRevoke(BaseModel):
    revoked_at: AwareDatetime
