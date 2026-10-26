from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __abstract__ = True
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Entity):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("role IN ('user', 'admin')"),)


class RefreshSession(Entity):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Hotel(Entity):
    __tablename__ = "hotels"
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(150), index=True)
    address: Mapped[str] = mapped_column(String(500))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("0.0"))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("rating >= 0 AND rating <= 5"),
        Index("ix_hotels_tags", "tags", postgresql_using="gin"),
    )


class Room(Entity):
    __tablename__ = "rooms"
    hotel_id: Mapped[UUID] = mapped_column(ForeignKey("hotels.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    capacity: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    interior_styles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    booking_purposes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("capacity >= 1 AND stock >= 1 AND price >= 0"),
        Index("ix_rooms_tags", "tags", postgresql_using="gin"),
    )


class Rate(Entity):
    __tablename__ = "rates"
    room_id: Mapped[UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    breakfast_included: Mapped[bool] = mapped_column(Boolean, default=False)
    cancellation_policy: Mapped[str] = mapped_column(Text, default="Free before check-in")
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("price >= 0"),)


class Photo(Entity):
    __tablename__ = "photos"
    hotel_id: Mapped[UUID | None] = mapped_column(ForeignKey("hotels.id"), index=True)
    room_id: Mapped[UUID | None] = mapped_column(ForeignKey("rooms.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        CheckConstraint(
            "(hotel_id IS NOT NULL AND room_id IS NULL) OR "
            "(hotel_id IS NULL AND room_id IS NOT NULL)"
        ),
    )


class FilterOption(Entity):
    __tablename__ = "filter_options"
    kind: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("kind", "code"),)


class Booking(Entity):
    __tablename__ = "bookings"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    hotel_id: Mapped[UUID] = mapped_column(ForeignKey("hotels.id"), index=True)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("rooms.id"), index=True)
    rate_id: Mapped[UUID] = mapped_column(ForeignKey("rates.id"))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    guests_count: Mapped[int] = mapped_column(Integer)
    rooms_count: Mapped[int] = mapped_column(Integer)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        CheckConstraint("check_out > check_in"),
        CheckConstraint("guests_count >= 1 AND rooms_count >= 1 AND total_price >= 0"),
        CheckConstraint("status IN ('pending','paid','confirmed','cancelled','failed')"),
    )


class Payment(Entity):
    __tablename__ = "payments"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_method: Mapped[str] = mapped_column(String(30), default="demo")
    provider_payment_id: Mapped[str] = mapped_column(String(100), default=lambda: str(uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    demo_ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        CheckConstraint("amount >= 0"),
        CheckConstraint("status IN ('pending','success','failed','refunded')"),
    )


class Favorite(Entity):
    __tablename__ = "favorites"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    hotel_id: Mapped[UUID] = mapped_column(ForeignKey("hotels.id"))
    __table_args__ = (UniqueConstraint("user_id", "hotel_id"),)


class Review(Entity):
    __tablename__ = "reviews"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    hotel_id: Mapped[UUID] = mapped_column(ForeignKey("hotels.id"), index=True)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5"),)


class Notification(Entity):
    __tablename__ = "notifications"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"))
    type: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("booking_id", "type"),)


class AnalyticsEvent(Entity):
    __tablename__ = "analytics_events"
    name: Mapped[str] = mapped_column(String(40))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
