import asyncio

from fastapi import Request, status
from fastapi.responses import Response
from shared_logging import get_logger

from application.dtos.inbound.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from application.ports.inbound.speaker_inbound_port import SpeakerInboundPort
from infrastructure.inbound.http.helpers.request_audio_reader import RequestAudioReader
from infrastructure.inbound.http.response.http_envelope import failure, failure_message
from infrastructure.inbound.http.response.playback_stream_response import (
    cancel_playback,
    playback_events,
)
from infrastructure.inbound.http.response.request_body_safe_streaming_response import (
    RequestBodySafeStreamingResponse,
)
from infrastructure.inbound.http.response.stream_headers import NDJSON_MEDIA_TYPE, stream_headers

logger = get_logger(__name__)

PLAY_ACTION = "set_stream_http"
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_CHANNELS = 1
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 15.0


async def handle_set_stream(
    request: Request,
    inbound: SpeakerInboundPort,
    sample_rate: int,
    channels: int,
    keep_open_after_completed: bool,
    heartbeat_interval_seconds: float,
    max_heartbeats_after_completed: int | None,
) -> Response:
    """POST /process/stream/set: accept raw audio (or NDJSON events), ack once the device is set up,
    then stream events.

    Waits only for speaker setup, emits ``stream_started`` on a live NDJSON response and keeps
    consuming the request audio while it plays.
    """
    logger.info(
        "HTTP playback stream request received",
        client=request.client,
        sample_rate=sample_rate,
        channels=channels,
    )
    if sample_rate <= 0 or channels <= 0:
        return failure_message(
            PLAY_ACTION,
            "sample_rate and channels must be positive",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    reader = RequestAudioReader(request, sample_rate, channels)
    setup_future: asyncio.Future[PlaybackOutboundDTO] = asyncio.get_running_loop().create_future()
    play_task = asyncio.create_task(
        inbound.play(
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
            return failure(PLAY_ACTION, "Failed to set playback stream", error)

    if not setup_response.success:
        logger.warning("HTTP playback setup failed", message=setup_response.message)
        await cancel_playback(play_task, "HTTP playback task cancelled after setup failure")
        return failure_message(
            PLAY_ACTION,
            setup_response.message,
            status.HTTP_503_SERVICE_UNAVAILABLE,  # the output device could not be opened
        )

    return RequestBodySafeStreamingResponse(
        playback_events(
            play_task,
            reader,
            setup_response,
            sample_rate,
            channels,
            keep_open_after_completed,
            heartbeat_interval_seconds,
            max_heartbeats_after_completed,
        ),
        media_type=NDJSON_MEDIA_TYPE,
        headers=stream_headers(),
    )
