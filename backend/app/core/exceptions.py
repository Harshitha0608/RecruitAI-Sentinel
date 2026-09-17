import logging
from typing import Any
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.core.exceptions")

async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
    logger.error(f"Validation error occurred: {exc}", exc_info=True, extra={"path": request.url.path})
    errors = getattr(exc, "errors", lambda: [{"message": str(exc)}])()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "detail": errors
        }
    )

async def value_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Value error: {exc}", exc_info=True, extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "ValueError",
            "message": str(exc)
        }
    )

async def runtime_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Runtime error: {exc}", exc_info=True, extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "RuntimeError",
            "message": str(exc)
        }
    )

async def file_not_found_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"File not found: {exc}", exc_info=True, extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "NotFoundError",
            "message": str(exc)
        }
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unexpected error: {exc}", exc_info=True, extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred."
        }
    )

