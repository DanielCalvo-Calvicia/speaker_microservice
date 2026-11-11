from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared_logging import TracingMiddleware, get_logger

from application.ports.service.speaker_service_port import SpeakerServicePort
from infrastructure.inbound.http.http_handler import SpeakerHandler

logger = get_logger(__name__)


def new_http_app(
    service: SpeakerServicePort,
    name: str,
    allowed_origins: tuple[str, ...],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        logger.info("Shutting down: releasing the speaker")
        await service.stop_playback()

    app = FastAPI(
        title=name,
        description=f"HTTP adapter exposing {name}",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception in HTTP handler", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "An internal error occurred"},
        )

    allow_all = allowed_origins == ("*",)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=not allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(SpeakerHandler(service).router)
    app.add_middleware(TracingMiddleware)  # added last so it is outermost
    return app
