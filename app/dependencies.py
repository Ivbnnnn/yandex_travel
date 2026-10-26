from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from .errors import AuthenticationError, ForbiddenError
from .services.bookings import BookingService, PaymentService
from .services.catalog import CatalogService, FavoriteService, ReviewService
from .services.notifications import AnalyticsService, NotificationService
from .services.users import AuthService, UserService


def current_user(request: Request) -> UUID:
    if request.state.user_id is None:
        raise AuthenticationError()
    return request.state.user_id


CurrentUser = Annotated[UUID, Depends(current_user)]


def require_admin(request: Request):
    if request.state.user_role != "admin":
        raise ForbiddenError("Administrator permission required")


def get_auth(request: Request):
    state = request.app.state
    return AuthService(state.uow_factory, state.settings, state.tokens, state.passwords)


def get_users(request: Request):
    return UserService(request.app.state.uow_factory, request.app.state.settings)


def get_catalog(request: Request):
    return CatalogService(request.app.state.uow_factory, request.app.state.settings)


def get_bookings(request: Request):
    return BookingService(request.app.state.uow_factory, request.app.state.settings)


def get_payments(request: Request):
    return PaymentService(request.app.state.uow_factory, request.app.state.settings)


def get_favorites(request: Request):
    return FavoriteService(request.app.state.uow_factory, request.app.state.settings)


def get_reviews(request: Request):
    return ReviewService(request.app.state.uow_factory, request.app.state.settings)


def get_notifications(request: Request):
    return NotificationService(request.app.state.uow_factory, request.app.state.settings)


def get_analytics(request: Request):
    return AnalyticsService(request.app.state.uow_factory, request.app.state.settings)
