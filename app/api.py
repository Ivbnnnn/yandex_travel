from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from . import dependencies as d
from . import schemas as s
from .errors import ValidationError
from .services.bookings import BookingService, PaymentService
from .services.catalog import CatalogService, FavoriteService, ReviewService
from .services.notifications import AnalyticsService, NotificationService
from .services.users import AuthService, UserService

router = APIRouter(prefix="/api/v1")
Auth = Annotated[AuthService, Depends(d.get_auth)]
Users = Annotated[UserService, Depends(d.get_users)]
Catalog = Annotated[CatalogService, Depends(d.get_catalog)]
Bookings = Annotated[BookingService, Depends(d.get_bookings)]
Payments = Annotated[PaymentService, Depends(d.get_payments)]
Favorites = Annotated[FavoriteService, Depends(d.get_favorites)]
Reviews = Annotated[ReviewService, Depends(d.get_reviews)]
Notifications = Annotated[NotificationService, Depends(d.get_notifications)]
Analytics = Annotated[AnalyticsService, Depends(d.get_analytics)]
Search = Annotated[s.SearchQuery, Query()]
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]
ADMIN = [Depends(d.require_admin)]


@router.post("/auth/register", status_code=201, tags=["Authentication"])
async def register(data: s.Register, service: Auth):
    return await service.register(data)


@router.post("/auth/login", tags=["Authentication"])
async def login(data: s.Login, service: Auth, request: Request, response: Response):
    user, tokens = await service.login(data)
    request.app.state.tokens.set_cookies(response, tokens)
    return user


@router.post("/auth/refresh", tags=["Authentication"])
async def refresh(service: Auth, request: Request, response: Response):
    tokens = await service.refresh(
        request.state.user_id, request.state.session_id, request.state.refresh_token
    )
    request.app.state.tokens.set_cookies(response, tokens)
    return {"detail": "Tokens refreshed"}


@router.post("/auth/logout", status_code=204, tags=["Authentication"])
async def logout(service: Auth, request: Request, response: Response):
    await service.logout(
        request.state.user_id, request.state.session_id, request.state.refresh_token
    )
    request.app.state.tokens.clear_cookies(response)


@router.get("/users/me", tags=["Profile"])
async def profile(user: d.CurrentUser, service: Users):
    return await service.profile(user)


@router.patch("/users/me", tags=["Profile"])
async def update_profile(data: s.UserPatch, user: d.CurrentUser, service: Users):
    return await service.update(user, data)


@router.delete("/users/me", status_code=204, tags=["Profile"])
async def deactivate(user: d.CurrentUser, service: Users, request: Request, response: Response):
    await service.deactivate(user)
    request.app.state.tokens.clear_cookies(response)


@router.get("/filters", tags=["Catalog"])
async def filters(service: Catalog):
    return await service.filters()


@router.get("/hotels/search", tags=["Catalog"])
async def search(query: Search, service: Catalog):
    if not query.city or not query.check_in:
        raise ValidationError("city, check_in and check_out are required")
    return await service.search(query)


@router.get("/hotels", tags=["Catalog"])
async def hotels(query: Search, service: Catalog):
    return await service.search(query)


@router.get("/hotels/compare", tags=["Catalog"])
async def compare_hotels(
    service: Catalog,
    hotel_ids: Annotated[list[UUID], Query(min_length=2, max_length=3)],
):
    return await service.compare(hotel_ids)


@router.get("/hotels/{hotel_id}", tags=["Catalog"])
async def hotel(hotel_id: UUID, query: Search, service: Catalog):
    return await service.hotel(hotel_id, query)


@router.get("/hotels/{hotel_id}/rooms", tags=["Catalog"])
async def hotel_rooms(hotel_id: UUID, query: Search, service: Catalog):
    return {"items": (await service.hotel(hotel_id, query))["rooms"]}


@router.get("/rooms/{room_id}", tags=["Catalog"])
async def room(room_id: UUID, query: Search, service: Catalog):
    return await service.room(room_id, query)


@router.get("/rooms/{room_id}/rates", tags=["Catalog"])
async def room_rates(room_id: UUID, query: Search, service: Catalog):
    return {"items": (await service.room(room_id, query))["rates"]}


@router.post("/hotels", status_code=201, dependencies=ADMIN, tags=["Admin catalog"])
async def create_hotel(data: s.HotelCreate, service: Catalog):
    return await service.create_hotel(data)


@router.patch("/hotels/{hotel_id}", dependencies=ADMIN, tags=["Admin catalog"])
async def update_hotel(hotel_id: UUID, data: s.HotelPatch, service: Catalog):
    return await service.update_hotel(hotel_id, data)


@router.delete("/hotels/{hotel_id}", status_code=204, dependencies=ADMIN, tags=["Admin catalog"])
async def delete_hotel(hotel_id: UUID, service: Catalog):
    await service.update_hotel(hotel_id, s.HotelPatch(is_active=False))


@router.post(
    "/hotels/{hotel_id}/rooms", status_code=201, dependencies=ADMIN, tags=["Admin catalog"]
)
async def create_room(hotel_id: UUID, data: s.RoomCreate, service: Catalog):
    return await service.create_room(hotel_id, data)


@router.patch("/rooms/{room_id}", dependencies=ADMIN, tags=["Admin catalog"])
async def update_room(room_id: UUID, data: s.RoomPatch, service: Catalog):
    return await service.update_room(room_id, data)


@router.delete("/rooms/{room_id}", status_code=204, dependencies=ADMIN, tags=["Admin catalog"])
async def delete_room(room_id: UUID, service: Catalog):
    await service.update_room(room_id, s.RoomPatch(is_active=False))


@router.post("/rooms/{room_id}/rates", status_code=201, dependencies=ADMIN, tags=["Admin catalog"])
async def create_rate(room_id: UUID, data: s.RateCreate, service: Catalog):
    return await service.create_rate(room_id, data)


@router.patch("/rates/{rate_id}", dependencies=ADMIN, tags=["Admin catalog"])
async def update_rate(rate_id: UUID, data: s.RatePatch, service: Catalog):
    return await service.update_rate(rate_id, data)


@router.delete("/rates/{rate_id}", status_code=204, dependencies=ADMIN, tags=["Admin catalog"])
async def delete_rate(rate_id: UUID, service: Catalog):
    await service.update_rate(rate_id, s.RatePatch(is_active=False))


@router.post(
    "/hotels/{hotel_id}/photos", status_code=201, dependencies=ADMIN, tags=["Admin catalog"]
)
async def hotel_photo(hotel_id: UUID, data: s.PhotoCreate, service: Catalog):
    return await service.add_photo(hotel_id, data, "hotel")


@router.post("/rooms/{room_id}/photos", status_code=201, dependencies=ADMIN, tags=["Admin catalog"])
async def room_photo(room_id: UUID, data: s.PhotoCreate, service: Catalog):
    return await service.add_photo(room_id, data, "room")


@router.post("/favorites", status_code=201, tags=["Favorites"])
async def add_favorite(data: s.FavoriteCreate, user: d.CurrentUser, service: Favorites):
    return await service.add(user, data.hotel_id)


@router.get("/users/me/favorites", tags=["Favorites"])
async def favorites(user: d.CurrentUser, service: Favorites):
    return await service.list(user)


@router.get("/favorites/{favorite_id}", tags=["Favorites"])
async def favorite(favorite_id: UUID, user: d.CurrentUser, service: Favorites):
    return await service.get(user, favorite_id)


@router.delete("/favorites/{favorite_id}", status_code=204, tags=["Favorites"])
async def remove_favorite(favorite_id: UUID, user: d.CurrentUser, service: Favorites):
    await service.remove(user, favorite_id)


@router.post("/bookings", status_code=201, tags=["Bookings"])
async def create_booking(data: s.BookingCreate, key: Key, user: d.CurrentUser, service: Bookings):
    return await service.create(user, data, key)


@router.get("/bookings/{booking_id}", tags=["Bookings"])
async def booking(booking_id: UUID, user: d.CurrentUser, service: Bookings):
    return await service.get(user, booking_id)


@router.get("/users/me/bookings", tags=["Bookings"])
async def bookings(user: d.CurrentUser, service: Bookings):
    return await service.list(user)


@router.post("/bookings/{booking_id}/cancel", tags=["Bookings"])
async def cancel_booking(booking_id: UUID, user: d.CurrentUser, service: Bookings):
    return await service.cancel(user, booking_id)


@router.post("/payments", tags=["Demo payments"])
async def create_payment(
    data: s.PaymentCreate, key: Key, user: d.CurrentUser, service: Payments, response: Response
):
    result = await service.create(user, data, key)
    response.status_code = 202 if result["status"] == "pending" else 200
    return result


@router.get("/payments/{payment_id}", tags=["Demo payments"])
async def payment(payment_id: UUID, user: d.CurrentUser, service: Payments):
    return await service.get(user, payment_id)


@router.post("/hotels/{hotel_id}/reviews", status_code=201, tags=["Reviews"])
async def review(hotel_id: UUID, data: s.ReviewCreate, user: d.CurrentUser, service: Reviews):
    return await service.add(user, hotel_id, data)


@router.get("/users/me/notifications", tags=["Notifications"])
async def notifications(user: d.CurrentUser, service: Notifications):
    return await service.list(user)


@router.patch("/notifications/{notification_id}/read", tags=["Notifications"])
async def read_notification(notification_id: UUID, user: d.CurrentUser, service: Notifications):
    return await service.read(user, notification_id)


@router.post("/analytics/events", status_code=202, tags=["Analytics"])
async def analytics(data: s.AnalyticsCreate, request: Request, service: Analytics):
    await service.record(request.state.user_id, data)
    return {"detail": "Event recorded"}
