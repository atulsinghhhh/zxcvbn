"""FastAPI application factory for WindSight."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import accuracy, forecast, health, intervals, overview
from app.clients.base import ElexonBaseClient
from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient
from app.config import settings
from app.exceptions import ElexonClientError, ElexonHTTPError, ElexonNetworkError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    http = ElexonBaseClient()
    app.state.windfor_client = WindForClient(http)
    app.state.fuelhh_client = FuelHHClient(http)
    try:
        yield
    finally:
        http.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="WindSight API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(ElexonHTTPError)
    async def _elexon_http(req: Request, exc: ElexonHTTPError) -> JSONResponse:
        logger.warning("Upstream HTTP %d: %s", exc.status_code, exc.url)
        return JSONResponse(
            status_code=502,
            content={"error": "upstream_error", "detail": "Elexon API returned an error."},
        )

    @app.exception_handler(ElexonNetworkError)
    async def _elexon_net(req: Request, exc: ElexonNetworkError) -> JSONResponse:
        logger.warning("Upstream network failure: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"error": "upstream_unavailable", "detail": "Elexon API is unreachable."},
        )

    @app.exception_handler(ElexonClientError)
    async def _elexon_client(req: Request, exc: ElexonClientError) -> JSONResponse:
        logger.warning("Elexon client error: %s", exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_data_error",
                "detail": "Unexpected data from Elexon API.",
            },
        )

    @app.exception_handler(ValueError)
    async def _value_error(req: Request, exc: ValueError) -> JSONResponse:
        logger.info("Not found: %s", exc)
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def _unhandled(req: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": "An unexpected error occurred."},
        )

    app.include_router(health.router, prefix="/api")
    app.include_router(overview.router, prefix="/api")
    app.include_router(forecast.router, prefix="/api")
    app.include_router(accuracy.router, prefix="/api")
    app.include_router(intervals.router, prefix="/api")

    return app


app = create_app()
