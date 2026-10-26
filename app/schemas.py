from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

Money = Decimal


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Register(Input):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, repr=False)
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Login(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128, repr=False)

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class UserPatch(Input):
    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    notifications_enabled: bool | None = None

    @field_validator("email", "name", "notifications_enabled")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class HotelCreate(Input):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    city: str = Field(min_length=1, max_length=150)
    address: str = Field(min_length=1, max_length=500)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    tags: list[str] = Field(default_factory=list, max_length=50)


class HotelPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    city: str | None = Field(default=None, min_length=1, max_length=150)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    tags: list[str] | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class RoomCreate(Input):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    capacity: int = Field(ge=1, le=100)
    stock: int = Field(default=1, ge=1, le=1000)
    price: Money = Field(ge=0, max_digits=12, decimal_places=2)
    tags: list[str] = Field(default_factory=list, max_length=50)
    interior_styles: list[str] = Field(default_factory=list, max_length=10)
    booking_purposes: list[str] = Field(default_factory=list, max_length=10)


class RoomPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    capacity: int | None = Field(default=None, ge=1, le=100)
    stock: int | None = Field(default=None, ge=1, le=1000)
    price: Money | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    tags: list[str] | None = Field(default=None, max_length=50)
    interior_styles: list[str] | None = Field(default=None, max_length=10)
    booking_purposes: list[str] | None = Field(default=None, max_length=10)
    is_active: bool | None = None


class RateCreate(Input):
    name: str = Field(min_length=1, max_length=255)
    price: Money = Field(ge=0, max_digits=12, decimal_places=2)
    breakfast_included: bool = False
    cancellation_policy: str = Field(default="Free before check-in", max_length=3000)
    conditions: dict = Field(default_factory=dict)


class RatePatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Money | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    breakfast_included: bool | None = None
    cancellation_policy: str | None = Field(default=None, max_length=3000)
    conditions: dict | None = None
    is_active: bool | None = None


class PhotoCreate(Input):
    url: HttpUrl
    sort_order: int = Field(default=0, ge=0)


class SearchQuery(Input):
    city: str | None = Field(default=None, min_length=1, max_length=150)
    check_in: date | None = None
    check_out: date | None = None
    guests_count: int = Field(default=1, ge=1, le=100)
    rooms_count: int = Field(default=1, ge=1, le=20)
    interior_style: list[str] = Field(default_factory=list)
    booking_purpose: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    sort: Literal["price_asc", "price_desc", "rating_desc", "name"] = "price_asc"
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("city")
    @classmethod
    def nonblank_city(cls, value):
        if value is not None and not value.strip():
            raise ValueError("City cannot be blank")
        return value.strip() if value else value

    @model_validator(mode="after")
    def dates(self):
        if bool(self.check_in) != bool(self.check_out):
            raise ValueError("Provide both check_in and check_out")
        if self.check_in and self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if self.check_in and (self.check_out - self.check_in).days > 365:
            raise ValueError("Maximum stay is 365 nights")
        return self


class BookingCreate(Input):
    hotel_id: UUID
    room_id: UUID
    rate_id: UUID
    check_in: date
    check_out: date
    guests_count: int = Field(ge=1, le=100)
    rooms_count: int = Field(ge=1, le=20)

    @model_validator(mode="after")
    def dates(self):
        if self.check_out <= self.check_in or (self.check_out - self.check_in).days > 365:
            raise ValueError("Invalid stay dates")
        return self


class PaymentCreate(Input):
    booking_id: UUID
    payment_method: Literal["demo"] = "demo"
    payment_token: Literal["success", "fail", "timeout"] = Field(default="success", repr=False)


class FavoriteCreate(Input):
    hotel_id: UUID


class ReviewCreate(Input):
    booking_id: UUID
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=1, max_length=3000)


class AnalyticsCreate(Input):
    name: Literal["reset_filters"]
    city: str | None = Field(default=None, max_length=150)
    check_in: date | None = None
    check_out: date | None = None
