import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import Settings
from ..errors import AuthenticationError, ForbiddenError, NotFoundError, ValidationError
from ..uow import UowFactory

ID_FIELDS = {
    "users": "user_id",
    "hotels": "hotel_id",
    "rooms": "room_id",
    "rates": "rate_id",
    "photos": "photo_id",
    "bookings": "booking_id",
    "payments": "payment_id",
    "favorites": "favorite_id",
    "reviews": "review_id",
    "notifications": "notification_id",
}
HIDDEN = {"password_hash", "token_hash", "request_hash", "idempotency_key", "demo_ready_at"}


def public(instance) -> dict:
    data = {
        column.key: getattr(instance, column.key)
        for column in instance.__table__.columns
        if column.key not in HIDDEN
    }
    if "id" in data:
        data[ID_FIELDS.get(instance.__tablename__, "id")] = data.pop("id")
    return data


def fingerprint(data) -> str:
    value = data.model_dump(mode="json") if hasattr(data, "model_dump") else data
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def own(instance, user_id):
    if instance is None:
        raise NotFoundError()
    if instance.user_id != user_id:
        raise ForbiddenError()
    return instance


class BaseService:
    def __init__(self, uow_factory: UowFactory, settings: Settings):
        self.uow_factory = uow_factory
        self.settings = settings

    def today(self):
        return datetime.now(ZoneInfo(self.settings.TIMEZONE)).date()

    @staticmethod
    async def active_user(uow, user_id, *, lock=True):
        user = await uow.users.get(user_id, lock=lock)
        if not user or not user.is_active:
            raise AuthenticationError("Account is inactive")
        return user

    def validate_dates(self, start, end):
        if start and (start < self.today() or end <= start):
            raise ValidationError("Check-in must not be in the past; check-out must be later")

    @staticmethod
    def patch(instance, data, nullable=()):
        values = data.model_dump(exclude_unset=True)
        for key, value in values.items():
            if value is None and key not in nullable:
                raise ValidationError(f"{key} cannot be null")
            setattr(instance, key, value)
