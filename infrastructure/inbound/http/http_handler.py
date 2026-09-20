"""HTTP inbound adapter: decode -> call the inbound port -> encode. No business rules."""

import asyncio
import time
from collections.abc import AsyncGenerator

from contracts.api.microservices.common.availability import AvailabilityResponse
from contracts.api.microservices.common.health_check import HealthCheckResponse
from contracts.api.microservices.common.readiness import ReadinessResponse
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, Response
from shared_logging import get_logger

from application.dtos.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.playback_outbound import PlaybackOutboundDTO
from application.ports.inbound.speaker_playback_port import SpeakerPlaybackPort
from infrastructure.inbound.http.http_envelope import failure, failure_message, success
from infrastructure.inbound.http.ndjson_events import NdjsonEventStream
from infrastructure.inbound.http.request_audio_reader import RequestAudioReader
from infrastructure.inbound.http.request_body_safe_streaming_response import (
    RequestBodySafeStreamingResponse,
)

logger = get_logger(__name__)

_PLAY_ACTION = "set_stream_http"


class SpeakerHandler:
    def __init__(self, port: SpeakerPlaybackPort) -> None:
        self._port = port
        self.router = APIRouter()
        self.router.add_api_route("/health", self.handle_health, methods=["GET"], tags=["Health"])
        self.router.add_api_route(
            "/ready", self.handle_ready, methods=["GET"], tags=["Health"]
        )
        self.router.add_api_route(
            "/available",
            self.handle_available,
            methods=["GET"],
            tags=["Playback"],
        )
        self.router.add_api_route(
            "/process/stream/set",
            self.handle_set_stream,
            methods=["POST"],
            tags=["Playback"],
            response_model=None,
        )

    async def handle_health(self) -> JSONResponse:
        return success(
            "health_check",
            "Speaker microservice is healthy",
            HealthCheckResponse(healthy=True),
        )

    async def handle_ready(self) -> JSONResponse:
        readiness = await self._port.check_readiness()
        return success(
            "check_readiness",
            "Speaker device readiness checked",
            ReadinessResponse(is_ready=readiness.is_ready, pending_reason=readiness.message or None),
        )

    async def handle_available(self) -> JSONResponse:
        """Whether the output device can be used (probed without opening a stream)."""
        readiness = await self._port.check_readiness()
        return success(
            "check_availability",
            "Speaker availability checked",
            AvailabilityResponse(is_available=readiness.is_ready, reason=readiness.message or None),
        )

    async def handle_set_stream(
        self,
        request: Request,
        sample_rate: int = 24000,
        channels: int = 1,
        keep_open_after_completed: bool = False,
        heartbeat_interval_seconds: float = 15.0,
        max_heartbeats_after_completed: int | None = None,
    ) -> Response:
        """Accept raw audio via chunked transfer, ack once the device is set up, then stream events.

        Waits only for speaker setup, emits ``stream_started`` on a live NDJSON response and
        keeps consuming the request audio while it plays.
        """
        logger.info(
            "HTTP playback stream request received",
            client=request.client,
            sample_rate=sample_rate,
            channels=channels,
        )
        if sample_rate <= 0 or channels <= 0:
            return failure_message(
                _PLAY_ACTION,
                "sample_rate and channels must be positive",
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        reader = RequestAudioReader(request, sample_rate, channels)
        setup_future: asyncio.Future[PlaybackOutboundDTO] = (
            asyncio.get_running_loop().create_future()
        )
        play_task = asyncio.create_task(
            self._port.play(
                PlayStreamInboundDTO(
                    audio_stream=reader.audio(),
                    sample_rate=sample_rate,
                    channels=channels,
                    setup_future=setup_future,
                )
            )
        )

        done, _ = await asyncio.wait({setup_future, play_task}, return_when=asyncio.FIRST_COMPLETED)
        if setup_future in done:
            setup_response = setup_future.result()
        else:
            try:
                setup_response = await play_task
            except Exception as error:
                logger.exception("HTTP playback setup failed before acknowledgement")
                return failure(_PLAY_ACTION, "Failed to set playback stream", error)

        if not setup_response.success:
            logger.warning("HTTP playback setup failed", message=setup_response.message)
            await _cancel(play_task, "HTTP playback task cancelled after setup failure")
            return failure_message(
                _PLAY_ACTION,
                setup_response.message,
                status.HTTP_503_SERVICE_UNAVAILABLE,  # the output device could not be opened
            )

        return RequestBodySafeStreamingResponse(
            self._response_events(
                play_task,
                reader,
                setup_response,
                sample_rate,
                channels,
                keep_open_after_completed,
                heartbeat_interval_seconds,
                max_heartbeats_after_completed,
            ),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff",
            },
        )

    async def _response_events(
        self,
        play_task: "asyncio.Task[PlaybackOutboundDTO]",
        reader: RequestAudioReader,
        setup_response: PlaybackOutboundDTO,
        sample_rate: int,
        channels: int,
        keep_open_after_completed: bool,
        heartbeat_interval_seconds: float,
        max_heartbeats_after_completed: int | None,
    ) -> AsyncGenerator[str, None]:
        events = NdjsonEventStream()
        yield events.stream_started(setup_response.message, sample_rate, channels)

        try:
            while not play_task.done():
                await asyncio.sleep(0.1)

            response = await play_task

            if reader.read_error is not None:
                yield events.error(
                    "request_stream_failed",
                    f"Failed to read request stream: {reader.read_error}",
                )
            elif not response.success:
                logger.warning(
                    "HTTP playback failed",
                    chunks=reader.chunk_count,
                    bytes=reader.total_bytes,
                    message=response.message,
                )
                yield events.error("playback_failed", response.message)
            else:
                logger.info(
                    "HTTP playback completed successfully",
                    chunks=reader.chunk_count,
                    bytes=reader.total_bytes,
                    message=response.message,
                )
                yield events.completed(
                    reason="end_of_input",
                    chunk_count=reader.chunk_count,
                    byte_count=reader.total_bytes,
                    message=response.message,
                )

                heartbeat_count = 0
                while keep_open_after_completed:
                    if (
                        max_heartbeats_after_completed is not None
                        and heartbeat_count >= max_heartbeats_after_completed
                    ):
                        break
                    await asyncio.sleep(max(0.1, heartbeat_interval_seconds))
                    heartbeat_count += 1
                    yield events.heartbeat()
        except Exception as error:
            logger.exception(
                "HTTP playback request failed",
                chunks=reader.chunk_count,
                bytes=reader.total_bytes,
            )
            yield events.error("stream_failed", f"Failed to play stream: {error}")
        finally:
            await _cancel(play_task, "HTTP playback task cancelled while closing response stream")


async def _cancel(task: "asyncio.Task[PlaybackOutboundDTO]", log_message: str) -> None:
    if task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info(log_message)
