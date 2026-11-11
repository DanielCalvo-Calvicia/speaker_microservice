"""HTTP inbound adapter: declares the endpoints and wires each to its route. No request logic."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from application.dtos.inbound.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from application.dtos.outbound.readiness_outbound import ReadinessOutboundDTO
from application.ports.inbound.speaker_inbound_port import SpeakerInboundPort
from application.ports.service.speaker_service_port import SpeakerServicePort
from infrastructure.inbound.http.routes.available import handle_available
from infrastructure.inbound.http.routes.health import handle_health
from infrastructure.inbound.http.routes.ready import handle_ready
from infrastructure.inbound.http.routes.set_stream import (
    DEFAULT_CHANNELS,
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_SAMPLE_RATE,
    handle_set_stream,
)


class SpeakerHandler(SpeakerInboundPort):
    """The HTTP inbound adapter. It declares which endpoints exist and wires each to its function in
    ``routes/``; the request decoding, the answers and the error mapping live in ``helpers/``,
    ``response/`` and ``errors/``. Its operations are those of ``SpeakerInboundPort`` (DTOs, no HTTP
    types) and the routes call them.
    """

    def __init__(self, service: SpeakerServicePort) -> None:
        self._service = service
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self) -> None:
        inbound: SpeakerInboundPort = self
        add = self.router.add_api_route

        async def health() -> JSONResponse:
            return await handle_health(inbound)

        async def ready() -> JSONResponse:
            return await handle_ready(inbound)

        async def available() -> JSONResponse:
            return await handle_available(inbound)

        async def set_stream(
            request: Request,
            sample_rate: int = DEFAULT_SAMPLE_RATE,
            channels: int = DEFAULT_CHANNELS,
            keep_open_after_completed: bool = False,
            heartbeat_interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
            max_heartbeats_after_completed: int | None = None,
        ) -> Response:
            return await handle_set_stream(
                request,
                inbound,
                sample_rate,
                channels,
                keep_open_after_completed,
                heartbeat_interval_seconds,
                max_heartbeats_after_completed,
            )

        add("/health", health, methods=["GET"], tags=["Health"])
        add("/ready", ready, methods=["GET"], tags=["Health"])
        add("/available", available, methods=["GET"], tags=["Playback"])
        add(
            "/process/stream/set",
            set_stream,
            methods=["POST"],
            tags=["Playback"],
            response_model=None,
        )

    # --- SpeakerInboundPort: the operations every inbound adapter offers ---------------------

    def health(self) -> bool:
        return True

    async def check_readiness(self) -> ReadinessOutboundDTO:
        return await self._service.check_readiness()

    async def play(self, request: PlayStreamInboundDTO) -> PlaybackOutboundDTO:
        return await self._service.play(request)
