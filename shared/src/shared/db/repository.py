from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .base import Base

ModelType = TypeVar("ModelType", bound=Base)
BaseCreate = TypeVar("BaseCreate", bound=BaseModel)
BaseUpdate = TypeVar("BaseUpdate", bound=BaseModel)


class BaseRepository(Generic[ModelType, BaseCreate, BaseUpdate]):
    """Execute SQL without committing; transactions belong to services."""

    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert(self, data: BaseCreate | dict[str, Any]) -> ModelType:
        stmt = insert(self.model).values(**self._to_dict(data)).returning(self.model)
        return (await self.session.execute(stmt)).scalar_one()

    async def read(self, id: int | UUID) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update(self, id: int | UUID, data: BaseUpdate | dict[str, Any]) -> ModelType | None:
        values = self._to_dict(data, partial=True)
        if not values:
            return await self.read(id)
        stmt = update(self.model).where(self.model.id == id).values(**values).returning(self.model)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def delete(self, id: int | UUID) -> ModelType | None:
        stmt = delete(self.model).where(self.model.id == id).returning(self.model)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def _to_dict(data: BaseModel | dict[str, Any], partial: bool = False) -> dict[str, Any]:
        if isinstance(data, BaseModel):
            return data.model_dump(exclude_unset=partial, exclude_none=partial)
        return {key: value for key, value in data.items() if not partial or value is not None}
