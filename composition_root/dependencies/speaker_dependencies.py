from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared_logging import TracingMiddleware, get_logger

from application.ports.inbound.speaker_playback_port import SpeakerPlaybackPort
from application.ports.outbound.audio_playback_port import AudioPlaybackPort
from application.services.speaker_service import SpeakerService
from infrastructure.config.speaker_config import SpeakerConfig
from infrastructure.inbound.http.http_handler import SpeakerHandler
from infrastructure.outbound.sounddevice_playback.sounddevice_audio_playback import (
    SoundDeviceAudioPlayback,
)
from infrastructure.outbound.sounddevice_playback.sounddevice_device_selector import (
    DeviceSelector,
)
from infrastructure.outbound.sounddevice_playback.sounddevice_driver import SoundDeviceDriver

logger = get_logger(__name__)


def new_audio_playback(cfg: SpeakerConfig) -> AudioPlaybackPort:
    driver = SoundDeviceDriver()
    return SoundDeviceAudioPlayback(
        driver=driver,
        selector=DeviceSelector(driver, cfg.target_keywords, cfg.device_index),
    )


def new_speaker_service(playback: AudioPlaybackPort, name: str) -> SpeakerPlaybackPort:
    return SpeakerService(playback=playback, name=name)


def new_http_app(
    port: SpeakerPlaybackPort,
    name: str,
    allowed_origins: tuple[str, ...],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        logger.info("Shutting down: releasing the speaker")
        await port.stop_playback()

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
    app.include_router(SpeakerHandler(port).router)
    app.add_middleware(TracingMiddleware)  # added last so it is outermost
    return app
