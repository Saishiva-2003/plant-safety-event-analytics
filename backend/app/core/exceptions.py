"""
Central exception handling: every error returns the same JSON shape

    {"error": {"code": "...", "message": "...", "path": "...", "details": ...}}

  * 400 BAD_REQUEST        - invalid combination of parameters (e.g. date_from > date_to)
  * 404 NOT_FOUND          - unknown incident / missing report file
  * 422 VALIDATION_ERROR   - wrong type / value not allowed (FastAPI + Pydantic)
  * 503 DATABASE_UNAVAILABLE - MySQL down / wrong credentials (instead of a raw 500)
  * 500 INTERNAL_ERROR     - anything unexpected (logged with traceback, no stack trace to client)
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("safety_api")

STATUS_CODES = {400: "BAD_REQUEST", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 409: "CONFLICT",
                422: "VALIDATION_ERROR", 503: "DATABASE_UNAVAILABLE"}


class BadRequestError(Exception):
    """Raise for invalid parameter combinations -> HTTP 400."""

    def __init__(self, message: str, details=None):
        self.message, self.details = message, details


def _body(code: str, message: str, request: Request, details=None) -> dict:
    return {"error": {"code": code, "message": message, "path": request.url.path, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content=_body(STATUS_CODES.get(exc.status_code, "HTTP_ERROR"), str(exc.detail), request))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(x) for x in e["loc"] if x != "query"), "message": e["msg"],
                    "input": e.get("input")} for e in exc.errors()]
        return JSONResponse(status_code=422, content=_body("VALIDATION_ERROR", "Invalid request parameters",
                                                           request, details))

    @app.exception_handler(BadRequestError)
    async def bad_request(request: Request, exc: BadRequestError):
        return JSONResponse(status_code=400, content=_body("BAD_REQUEST", exc.message, request, exc.details))

    @app.exception_handler(OperationalError)
    async def db_unavailable(request: Request, exc: OperationalError):
        log.error("Database unavailable: %s", exc.orig)
        return JSONResponse(status_code=503, content=_body(
            "DATABASE_UNAVAILABLE", "MySQL is not reachable - check that the MySQL80 service is running and "
                                    "backend/.env credentials are correct", request))

    @app.exception_handler(SQLAlchemyError)
    async def db_error(request: Request, exc: SQLAlchemyError):
        log.exception("Database error")
        return JSONResponse(status_code=500, content=_body("DATABASE_ERROR", "A database error occurred", request))

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "Unexpected server error", request))