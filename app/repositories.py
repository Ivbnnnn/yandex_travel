from datetime import UTC, date, datetime
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from . import models as m

T = TypeVar("T", bound=m.Entity)


def active_booking(now: datetime):
    return or_(
        m.Booking.status.in_(["paid", "confirmed"]),
        and_(m.Booking.status == "pending", m.Booking.expires_at > now),
    )


class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: UUID, *, lock: bool = False) -> T | None:
        query = select(self.model).where(self.model.id == id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def add(self, **values) -> T:
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def all(self, **filters) -> list[T]:
        query = (
            select(self.model).filter_by(**filters).order_by(self.model.created_at, self.model.id)
        )
        return list((await self.session.execute(query)).scalars())

    async def remove(self, instance: T) -> None:
        await self.session.delete(instance)
        await self.session.flush()


class UserRepository(BaseRepository[m.User]):
    model = m.User

    async def by_email(self, email: str, *, lock=False):
        query = select(m.User).where(m.User.email == email.lower())
        if lock:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()


class SessionRepository(BaseRepository[m.RefreshSession]):
    model = m.RefreshSession

    async def revoke_all(self, user_id: UUID):
        await self.session.execute(
            update(m.RefreshSession)
            .where(m.RefreshSession.user_id == user_id)
            .values(revoked_at=datetime.now(UTC))
        )


class HotelRepository(BaseRepository[m.Hotel]):
    model = m.Hotel


class RoomRepository(BaseRepository[m.Room]):
    model = m.Room

    async def candidates(self, params):
        query = (
            select(m.Room, m.Hotel, func.min(m.Rate.price))
            .join(m.Hotel, m.Room.hotel_id == m.Hotel.id)
            .join(m.Rate, m.Rate.room_id == m.Room.id)
            .where(
                m.Room.is_active.is_(True),
                m.Hotel.is_active.is_(True),
                m.Rate.is_active.is_(True),
                m.Room.capacity * params.rooms_count >= params.guests_count,
                m.Room.stock >= params.rooms_count,
            )
            .group_by(m.Room.id, m.Hotel.id)
        )
        if params.city:
            query = query.where(func.lower(m.Hotel.city) == params.city.strip().lower())
        if params.interior_style:
            query = query.where(m.Room.interior_styles.overlap(params.interior_style))
        if params.booking_purpose:
            query = query.where(m.Room.booking_purposes.overlap(params.booking_purpose))
        if params.tags:
            query = query.where(
                or_(m.Room.tags.overlap(params.tags), m.Hotel.tags.overlap(params.tags))
            )
        return list((await self.session.execute(query)).all())


class RateRepository(BaseRepository[m.Rate]):
    model = m.Rate


class BookingRepository(BaseRepository[m.Booking]):
    model = m.Booking

    async def by_key(self, user_id, key):
        query = select(m.Booking).where(
            m.Booking.user_id == user_id, m.Booking.idempotency_key == key
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def intervals(self, room_ids, start: date, end: date):
        if not room_ids:
            return []
        query = select(
            m.Booking.room_id, m.Booking.check_in, m.Booking.check_out, m.Booking.rooms_count
        ).where(
            m.Booking.room_id.in_(room_ids),
            m.Booking.check_in < end,
            m.Booking.check_out > start,
            active_booking(datetime.now(UTC)),
        )
        return list((await self.session.execute(query)).all())

    async def expire_holds(self):
        await self.session.execute(
            update(m.Booking)
            .where(m.Booking.status == "pending", m.Booking.expires_at <= datetime.now(UTC))
            .values(status="failed")
            .execution_options(synchronize_session=False)
        )

    async def reminders(self, day: date):
        query = (
            select(m.Booking, m.User)
            .join(m.User)
            .where(
                m.Booking.status == "confirmed",
                m.Booking.check_in == day,
                m.User.is_active.is_(True),
                m.User.notifications_enabled.is_(True),
            )
        )
        return list((await self.session.execute(query)).all())


class PaymentRepository(BaseRepository[m.Payment]):
    model = m.Payment

    async def by_key(self, user_id, key):
        query = select(m.Payment).where(
            m.Payment.user_id == user_id, m.Payment.idempotency_key == key
        )
        return (await self.session.execute(query)).scalar_one_or_none()


class FavoriteRepository(BaseRepository[m.Favorite]):
    model = m.Favorite

    async def find(self, user_id, hotel_id):
        query = select(m.Favorite).where(
            m.Favorite.user_id == user_id, m.Favorite.hotel_id == hotel_id
        )
        return (await self.session.execute(query)).scalar_one_or_none()


class PhotoRepository(BaseRepository[m.Photo]):
    model = m.Photo


class FilterRepository(BaseRepository[m.FilterOption]):
    model = m.FilterOption


class ReviewRepository(BaseRepository[m.Review]):
    model = m.Review

    async def hotel_rating(self, hotel_id):
        return await self.session.scalar(
            select(func.avg(m.Review.rating)).where(m.Review.hotel_id == hotel_id)
        )


class NotificationRepository(BaseRepository[m.Notification]):
    model = m.Notification

    async def exists(self, booking_id, type):
        query = select(m.Notification.id).where(
            m.Notification.booking_id == booking_id, m.Notification.type == type
        )
        return await self.session.scalar(query)


class AnalyticsRepository(BaseRepository[m.AnalyticsEvent]):
    model = m.AnalyticsEvent
