from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

# Stable application error codes shared with the frontend.
ERROR_STATUS: dict[str, int] = {
    "UNAUTHENTICATED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "INVALID_STATE_TRANSITION": 409,
    "REFUND_LIMIT_EXCEEDED": 422,
    "REFUND_AMOUNT_EXCEEDED": 422,
    "IDEMPOTENCY_CONFLICT": 409,
    "VERSION_CONFLICT": 409,
    "PROVIDER_ERROR": 502,
}


class AppError(Exception):
    """Domain error mapped to a consistent JSON response shape."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = ERROR_STATUS.get(code, 400)
        super().__init__(message)

    def to_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content={
                "error": {
                    "code": self.code,
                    "message": self.message,
                    "details": self.details,
                }
            },
        )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return exc.to_response()


async def validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    from fastapi.exceptions import RequestValidationError

    from fastapi.encoders import jsonable_encoder

    details: dict[str, Any] = {}
    if isinstance(exc, RequestValidationError):
        details = {"errors": jsonable_encoder(exc.errors())}
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request payload failed validation.",
                "details": details,
            }
        },
    )
