import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class BusinessError(Exception):
    status_code = 400
    code = "business_error"
    default_detail = "Request could not be completed"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(BusinessError):
    status_code = 404
    code = "not_found"
    default_detail = "Object not found"


class ConflictError(BusinessError):
    status_code = 409
    code = "conflict"


class ValidationError(BusinessError):
    status_code = 422
    code = "invalid_data"


class AuthenticationError(BusinessError):
    status_code = 401
    code = "not_authenticated"
    default_detail = "Authentication required"


class ForbiddenError(BusinessError):
    status_code = 403
    code = "forbidden"
    default_detail = "Access denied"


class SoldOutError(ConflictError):
    code = "sold_out"
    default_detail = "Not enough rooms available on these dates"


class IdempotencyError(ConflictError):
    code = "idempotency_conflict"
    default_detail = "Idempotency-Key was already used with another request"


def error_response(error: BusinessError) -> JSONResponse:
    return JSONResponse({"code": error.code, "detail": error.detail}, status_code=error.status_code)


async def business_error_handler(request: Request, exc: BusinessError):
    return error_response(exc)


async def integrity_error_handler(request: Request, exc: IntegrityError):
    return error_response(ConflictError("Data conflicts with an existing record"))


async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = [{"loc": item["loc"], "msg": item["msg"]} for item in exc.errors()]
    return JSONResponse(
        {"code": "invalid_data", "detail": "Check request fields", "errors": errors},
        status_code=422,
    )


async def unexpected_error_handler(request: Request, exc: Exception):
    logging.getLogger(__name__).error(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        {"code": "internal_error", "detail": "Internal server error"}, status_code=500
    )
