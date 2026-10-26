from shared.errors import ApplicationError, application_error_handler


class UserAlreadyExistsError(ApplicationError):
    status_code = 409
    code = "user_already_exists"
    detail = "User already exists with this email"


class UserNotFoundError(ApplicationError):
    status_code = 404
    code = "user_not_found"
    detail = "User not found"


class InvalidCredentialsError(ApplicationError):
    status_code = 401
    code = "invalid_credentials"
    detail = "Invalid email or password"


class InvalidRefreshTokenError(ApplicationError):
    status_code = 401
    code = "invalid_refresh_token"
    detail = "Invalid or expired refresh session"


# All domain errors use the common handler; these names remain usable explicitly.
user_exists_handler = application_error_handler
user_not_found_handler = application_error_handler
