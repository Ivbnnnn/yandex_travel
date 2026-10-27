from datetime import datetime

from shared.db.base import Base
from sqlalchemy import DateTime, String, UniqueConstraint, func, Text, Float, ARRAY, Boolean, DDL, event
from sqlalchemy.orm import Mapped, mapped_column


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text(1024), nullable=False)

    city: Mapped[str] = mapped_column(String(255),  nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longtitude: Mapped[float] = mapped_column(Float, nullable=False)

    rating: Mapped[float] = mapped_column(Float, server_default="0", nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true",  nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )



